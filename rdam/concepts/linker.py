"""Deterministic lexical matching with reversible Unicode normalization."""

from collections import defaultdict
from collections.abc import Iterator
from dataclasses import dataclass, field
from functools import cache
from importlib.resources import files
import unicodedata

from rdam._canonical import semantic_sha256, sha256_bytes
from rdam.concepts.contracts import (
    Candidate, CandidateSpan, ConceptLinkRequest, ConceptLinkResult, MatchingOptions, Mention,
    Surface, occurrence_identity,
)
from rdam.concepts.index import ConceptIndex, LexicalEntry
from rdam.concepts.surfaces import inventory_surfaces
from rdam.ingest.contracts.preparation import ContentInventory
from rdam.ingest.contracts.source import SourceArtifact
from rdam.ingest.prepare import prepare_source


_DEFAULT_OPTIONS = MatchingOptions()


@cache
def implementation_identity() -> str:
    """Bind persisted evidence to the installed implementation, including contracts."""
    root = files("rdam.concepts")
    names = ("contracts.py", "index.py", "linker.py", "surfaces.py")
    return semantic_sha256(tuple((name, sha256_bytes(root.joinpath(name).read_bytes())) for name in names))


def _normalise(text: str, *, case_sensitive: bool) -> tuple[str, tuple[int, ...], tuple[int, ...]]:
    # NFD preserves canonical equivalence. Every output character maps to the
    # complete original starter/combining sequence; case expansions never split it.
    parts: list[str] = []
    starts: list[int] = []
    ends: list[int] = []
    index = 0
    while index < len(text):
        start = index
        index += 1
        if text[start].isspace():
            while index < len(text) and text[index].isspace():
                index += 1
            value = " "
        else:
            while index < len(text) and unicodedata.combining(text[index]):
                index += 1
            value = unicodedata.normalize("NFD", text[start:index])
            if not case_sensitive:
                value = unicodedata.normalize("NFD", value.casefold())
        parts.append(value)
        starts.extend([start] * len(value))
        ends.extend([index] * len(value))
    return "".join(parts), tuple(starts), tuple(ends)


def _word(character: str) -> bool:
    return character == "_" or character.isalnum() or unicodedata.category(character).startswith("M")


@dataclass(slots=True)
class _Trie:
    children: dict[str, _Trie] = field(default_factory=lambda: dict[str, _Trie]())
    entries: list[LexicalEntry] = field(default_factory=list[LexicalEntry])


def _trie(entries: tuple[LexicalEntry, ...], *, case_sensitive: bool) -> _Trie:
    root = _Trie()
    for entry in entries:
        literal, _, _ = _normalise(entry.literal, case_sensitive=case_sensitive)
        if not literal.strip():
            raise ValueError("ontology literal cannot be whitespace-only")
        node = root
        for character in literal:
            node = node.children.setdefault(character, _Trie())
        node.entries.append(entry)
    return root


def _matches(surface: Surface, root: _Trie, *, case_sensitive: bool) -> Iterator[tuple[tuple[int, int], LexicalEntry]]:
    text, starts, ends = _normalise(surface.text, case_sensitive=case_sensitive)
    for position, start in enumerate(starts):
        if position and start == starts[position - 1]:
            continue
        if start and _word(surface.text[start - 1]) and _word(surface.text[start]):
            continue
        node = root
        for cursor in range(position, len(text)):
            child = node.children.get(text[cursor])
            if child is None:
                break
            node = child
            finish = cursor + 1
            if finish < len(text) and ends[cursor] == ends[finish]:
                continue
            end = ends[cursor]
            if end < len(surface.text) and _word(surface.text[end - 1]) and _word(surface.text[end]):
                continue
            for entry in node.entries:
                yield (start, end), entry


def _link(
    inventory: ContentInventory, index: ConceptIndex, options: MatchingOptions,
    supplied: tuple[CandidateSpan, ...] | None,
) -> ConceptLinkResult:
    inventory = ContentInventory.model_validate(inventory.model_dump())
    index = ConceptIndex.model_validate(index.model_dump())
    options = MatchingOptions.model_validate(options.model_dump())
    surfaces, exclusions = inventory_surfaces(inventory)
    lookup = {(item.item_id, item.field_pointer): item for item in surfaces}
    requested: dict[tuple[str, str], set[tuple[int, int]]] = defaultdict(set)
    if supplied is not None:
        for span in supplied:
            span = CandidateSpan.model_validate(span.model_dump())
            surface = lookup.get((span.item_id, span.field_pointer))
            if surface is None or surface.text[span.start:span.end] != span.quote:
                raise ValueError("supplied candidate does not resolve to its exact source surface")
            requested[span.item_id, span.field_pointer].add((span.start, span.end))
    resources = {item.identifier: item for item in index.projection.resources}
    entries = tuple(entry for entry in index.projection.entries if entry.status != "retired"
                    and resources[entry.target].status != "retired" and resources[entry.target].domain in index.domains)
    sensitive_entries = tuple(entry for entry in entries if options.acronym_case_sensitive and entry.scope == "acronym")
    ordinary_entries = tuple(entry for entry in entries if not (options.acronym_case_sensitive and entry.scope == "acronym"))
    tries = ((_trie(ordinary_entries, case_sensitive=False), False), (_trie(sensitive_entries, case_sensitive=True), True))
    mentions: list[Mention] = []
    identity = inventory.semantic_digest
    if identity is None:
        raise ValueError("inventory has no identity")
    for surface in surfaces:
        reasons: dict[tuple[int, int], dict[str, list[LexicalEntry]]] = {}
        if supplied is not None:
            reasons = {span: {} for span in requested[surface.item_id, surface.field_pointer]}
        for trie, sensitive in tries:
            for span, entry in _matches(surface, trie, case_sensitive=sensitive):
                if supplied is not None and span not in reasons:
                    continue
                targets = reasons.setdefault(span, {})
                evidence = targets.setdefault(entry.target, [])
                if entry not in evidence:
                    evidence.append(entry)
        for (start, end), targets in sorted(reasons.items()):
            span = CandidateSpan(item_id=surface.item_id, field_pointer=surface.field_pointer,
                                 start=start, end=end, quote=surface.text[start:end])
            candidates = tuple(Candidate(resource=resources[target], reasons=tuple(targets[target])) for target in sorted(targets))
            mentions.append(Mention(
                **span.model_dump(), occurrence_id=occurrence_identity(identity, span), candidates=candidates,
                resolution="unmapped" if not candidates else "unique" if len(candidates) == 1 else "ambiguous",
            ))
    return ConceptLinkResult(
        source=inventory.source, inventory_identity=identity, source_adapter=inventory.source_contract,
        ontology=index.identity, implementation_identity=implementation_identity(), options=options,
        surfaces=surfaces, exclusions=exclusions, supplied_candidates=supplied, mentions=tuple(mentions),
    )


def link_inventory(inventory: ContentInventory, index: ConceptIndex, *, options: MatchingOptions = _DEFAULT_OPTIONS) -> ConceptLinkResult:
    """Scan each represented surface; uniqueness is lexical, not contextual."""
    return _link(inventory, index, options, None)


def resolve_candidates(inventory: ContentInventory, index: ConceptIndex, candidates: tuple[CandidateSpan, ...], *, options: MatchingOptions = _DEFAULT_OPTIONS) -> ConceptLinkResult:
    """Resolve exact supplied spans, retaining unmatched phrases explicitly."""
    return _link(inventory, index, options, candidates)


def link_source(source: SourceArtifact, index: ConceptIndex, *, options: MatchingOptions = _DEFAULT_OPTIONS) -> ConceptLinkResult:
    """Use shared ingestion exactly once; no analytical provider is constructed."""
    return link_inventory(ContentInventory.from_preparation(prepare_source(source)), index, options=options)


def execute_request(request: ConceptLinkRequest, index: ConceptIndex) -> ConceptLinkResult:
    request = ConceptLinkRequest.model_validate(request.model_dump())
    if request.domains is not None:
        if set(request.domains) - set(index.domains):
            raise ValueError("request domains exceed configured ontology scope")
        index = ConceptIndex(projection=index.projection, domains=tuple(sorted(request.domains)))
    inventory = request.inventory
    if inventory is None:
        if request.source is None:
            raise ValueError("request has no source")
        inventory = ContentInventory.from_preparation(prepare_source(request.source))
    return _link(inventory, index, request.options, request.supplied_candidates)


def validate_result(result: ConceptLinkResult, inventory: ContentInventory, index: ConceptIndex, *, options: MatchingOptions = _DEFAULT_OPTIONS) -> None:
    """Reconcile persisted evidence with the actual inputs and current implementation."""
    result = ConceptLinkResult.model_validate(result.model_dump())
    if (result.source != inventory.source or result.inventory_identity != inventory.semantic_digest
            or result.source_adapter != inventory.source_contract or result.ontology != index.identity
            or result.options != options or result.implementation_identity != implementation_identity()):
        raise ValueError("stale concept links: input or implementation identity differs")
    expected = _link(inventory, index, options, result.supplied_candidates)
    if result != expected:
        raise ValueError("stale or invalid concept links: source, inventory, ontology, options or implementation differs")

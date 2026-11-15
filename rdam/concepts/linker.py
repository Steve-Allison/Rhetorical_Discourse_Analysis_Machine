"""Deterministic Central_Configs v5.0.0 Stage 1 proper-noun surface linker."""

from bisect import bisect_left, bisect_right
from collections import defaultdict
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from functools import cache
from importlib.resources import files
import re
from typing import Literal

from ahocorasick_rs import AhoCorasick, MatchKind
from pydantic import BaseModel

from rdam._canonical import semantic_sha256, sha256_bytes
from rdam.concepts.contracts import (
    Candidate,
    CandidateSpan,
    ConceptLinkRequest,
    ConceptLinkResult,
    MatchingOptions,
    Mention,
    Surface,
    occurrence_identity,
)
from rdam.concepts.index import ConceptIndex, LexicalEntry, SemanticResource
from rdam.concepts.surfaces import inventory_surfaces
from rdam.ingest.contracts.preparation import ContentInventory
from rdam.ingest.contracts.source import AuthorshipRole, ContentClass, ItemAnchor, SourceArtifact, SourceOrigin
from rdam.ingest.prepare import prepare_source

_DEFAULT_OPTIONS = MatchingOptions()
_TOKEN_RE = re.compile(r"[A-Za-z0-9_.+-]+")
_NEGATIVE_WINDOW_TOKENS = 25


@cache
def implementation_identity() -> str:
    """Bind persisted evidence to the installed implementation, including contracts."""
    root = files("rdam.concepts")
    names = ("contracts.py", "index.py", "linker.py", "surfaces.py")
    return semantic_sha256(tuple((name, sha256_bytes(root.joinpath(name).read_bytes())) for name in names))


def _length_preserving_lower(text: str) -> str:
    lowered = text.lower()
    if len(lowered) == len(text):
        return lowered
    return "".join(ch.lower() if len(ch.lower()) == 1 else ch for ch in text)


def _alnum_bounded_in(haystack_lower: str, needle_lower: str) -> bool:
    if not needle_lower:
        return False
    pos = haystack_lower.find(needle_lower, 0)
    needle_len = len(needle_lower)
    hay_len = len(haystack_lower)
    while pos != -1:
        end = pos + needle_len
        left_ok = pos == 0 or not haystack_lower[pos - 1].isalnum()
        right_ok = end == hay_len or not haystack_lower[end].isalnum()
        if left_ok and right_ok:
            return True
        pos = haystack_lower.find(needle_lower, pos + 1)
    return False


@dataclass(frozen=True, slots=True)
class _CompiledRule:
    entry: LexicalEntry
    context_anchors_lower: tuple[str, ...]
    negative_phrases_lower: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class _CompiledMatcher:
    automaton: AhoCorasick | None
    pattern_rules: tuple[tuple[_CompiledRule, ...], ...]


@dataclass(frozen=True, slots=True)
class _TokenizedText:
    raw: str
    lowered: str
    starts: tuple[int, ...]
    ends: tuple[int, ...]
    tokens: tuple[str, ...]


def _tokenize_surface(raw_text: str) -> _TokenizedText:
    lowered = _length_preserving_lower(raw_text)
    starts: list[int] = []
    ends: list[int] = []
    tokens: list[str] = []
    for match in _TOKEN_RE.finditer(raw_text):
        starts.append(match.start())
        ends.append(match.end())
        tokens.append(match.group(0))
    return _TokenizedText(
        raw=raw_text,
        lowered=lowered,
        starts=tuple(starts),
        ends=tuple(ends),
        tokens=tuple(tokens),
    )


_MATCHER_CACHE: dict[
    tuple[str, tuple[str, ...]],
    tuple[Mapping[str, SemanticResource], _CompiledMatcher],
] = {}


def _compiled_index(
    index: ConceptIndex,
) -> tuple[Mapping[str, SemanticResource], _CompiledMatcher]:
    cache_key = (index.projection.content_digest, index.domains)
    cached = _MATCHER_CACHE.get(cache_key)
    if cached is not None:
        return cached
    resources = {item.curie: item for item in index.projection.resources}
    domain_set = set(index.domains)
    buckets: dict[str, list[_CompiledRule]] = {}
    for entry in index.projection.entries:
        owner = resources[entry.curie]
        if owner.status == "historical_only" or owner.collection_name not in domain_set:
            continue
        if entry.match_policy == "never_link":
            continue
        pattern = _length_preserving_lower(entry.surface)
        if not pattern.strip():
            raise ValueError("ontology surface cannot be whitespace-only")
        buckets.setdefault(pattern, []).append(
            _CompiledRule(
                entry=entry,
                context_anchors_lower=tuple(item.lower() for item in entry.context_anchors),
                negative_phrases_lower=tuple(item.lower() for item in entry.negative_phrases),
            )
        )
    if not buckets:
        matcher = _CompiledMatcher(automaton=None, pattern_rules=())
    else:
        patterns = tuple(buckets)
        pattern_rules = tuple(tuple(buckets[pattern]) for pattern in patterns)
        automaton = AhoCorasick(patterns, matchkind=MatchKind.Standard, store_patterns=False)
        matcher = _CompiledMatcher(automaton=automaton, pattern_rules=pattern_rules)
    compiled = (resources, matcher)
    if len(_MATCHER_CACHE) >= 32:
        _MATCHER_CACHE.clear()
    _MATCHER_CACHE[cache_key] = compiled
    return compiled


def _identifier_safe_boundaries(text: str, start: int, end: int) -> bool:
    text_len = len(text)
    if start > 0 and text[start - 1].isalnum():
        return False
    if end < text_len and text[end].isalnum():
        return False
    # Reject dotted package suffixes such as Express.js (GG-168).
    if end + 1 < text_len and text[end] == "." and text[end + 1].isalnum():
        return False
    # Reject hyphenated prefixes such as e-commerce (GG-176).
    return not (start >= 2 and text[start - 1] == "-" and text[start - 2].isalnum())


def _negative_veto(tokens: _TokenizedText, start: int, end: int, negative_phrases_lower: tuple[str, ...]) -> bool:
    if not negative_phrases_lower:
        return False
    if tokens.tokens:
        first_overlapping = bisect_right(tokens.ends, start)
        after_overlapping = bisect_left(tokens.starts, end)
        left_tok = max(0, first_overlapping - _NEGATIVE_WINDOW_TOKENS)
        right_tok = min(len(tokens.tokens), max(after_overlapping, first_overlapping) + _NEGATIVE_WINDOW_TOKENS)
        win_start = min(start, tokens.starts[left_tok]) if left_tok < len(tokens.starts) else start
        win_end = max(end, tokens.ends[right_tok - 1]) if right_tok > 0 else end
    else:
        win_start, win_end = start, end
    window_lower = tokens.lowered[win_start:win_end]
    return any(_alnum_bounded_in(window_lower, phrase) for phrase in negative_phrases_lower)


def _context_anchor_satisfied(
    tokens: _TokenizedText,
    start: int,
    end: int,
    window_tokens: int,
    anchors_lower: tuple[str, ...],
) -> bool:
    # Inspect +-anchor_window_tokens EXCLUDING the matched span [start, end) itself.
    left_end_idx = bisect_right(tokens.ends, start)
    right_start_idx = bisect_left(tokens.starts, end)
    left_slice = tokens.tokens[max(0, left_end_idx - window_tokens) : left_end_idx]
    right_slice = tokens.tokens[right_start_idx : right_start_idx + window_tokens]
    ctx_lower = f"{' '.join(left_slice)} {' '.join(right_slice)}".lower()
    return any(_alnum_bounded_in(ctx_lower, anchor) for anchor in anchors_lower)


def _matches(
    surface: Surface,
    matcher: _CompiledMatcher,
    *,
    acronym_case_sensitive: bool,
) -> Iterator[tuple[tuple[int, int], LexicalEntry]]:
    if matcher.automaton is None:
        return
    tokenized = _tokenize_surface(surface.text)
    raw_text = tokenized.raw
    pattern_rules = matcher.pattern_rules
    for pattern_id, start, end in matcher.automaton.find_matches_as_indexes(tokenized.lowered, overlapping=True):
        if not _identifier_safe_boundaries(raw_text, start, end):
            continue
        matched_slice = raw_text[start:end]
        for compiled_rule in pattern_rules[pattern_id]:
            entry = compiled_rule.entry
            if (
                acronym_case_sensitive
                and (entry.case_sensitive or entry.match_policy == "case_exact")
                and matched_slice != entry.surface
            ):
                continue
            if _negative_veto(tokenized, start, end, compiled_rule.negative_phrases_lower):
                continue
            if entry.match_policy == "context_anchored" and not _context_anchor_satisfied(
                tokenized,
                start,
                end,
                entry.anchor_window_tokens,
                compiled_rule.context_anchors_lower,
            ):
                continue
            yield (start, end), entry


def _select_non_overlapping(
    spans: Mapping[tuple[int, int], dict[str, list[LexicalEntry]]],
) -> list[tuple[tuple[int, int], dict[str, list[LexicalEntry]]]]:
    selected: list[tuple[tuple[int, int], dict[str, list[LexicalEntry]]]] = []
    last_end = -1
    for (start, end), targets in sorted(spans.items(), key=lambda item: (item[0][0], -(item[0][1] - item[0][0]))):
        if start >= last_end:
            selected.append(((start, end), targets))
            last_end = end
    return selected


def _build_mention(
    *,
    inventory_identity: object,
    surface: Surface,
    start: int,
    end: int,
    targets: Mapping[str, list[LexicalEntry]],
    resources: Mapping[str, SemanticResource],
) -> Mention:
    from rdam.ingest.contracts.base import Sha256Identity

    if not isinstance(inventory_identity, Sha256Identity):
        raise ValueError("inventory identity must be a Sha256Identity")
    span = CandidateSpan(
        item_id=surface.item_id,
        field_pointer=surface.field_pointer,
        start=start,
        end=end,
        quote=surface.text[start:end],
    )
    sorted_curies = tuple(sorted(targets))
    candidates = tuple(
        Candidate(resource=resources[curie], reasons=tuple(targets[curie]))
        for curie in sorted_curies
    )
    llm_required = any(
        reason.requires_llm_disambiguation
        for candidate in candidates
        for reason in candidate.reasons
    )
    if not sorted_curies:
        resolution: Literal["unique", "ambiguous", "unmapped"] = "unmapped"
        resolved_curie = None
        ambiguous = False
    else:
        first_curie, *rest = sorted_curies
        if rest or llm_required:
            resolution = "ambiguous"
            resolved_curie = None
            ambiguous = True
        else:
            resolution = "unique"
            resolved_curie = first_curie
            ambiguous = False
    return Mention(
        item_id=span.item_id,
        field_pointer=span.field_pointer,
        start=span.start,
        end=span.end,
        quote=span.quote,
        occurrence_id=occurrence_identity(inventory_identity, span),
        curie=resolved_curie,
        candidate_curies=sorted_curies,
        ambiguous=ambiguous,
        requires_llm_disambiguation=llm_required,
        candidates=candidates,
        resolution=resolution,
    )


def _coerce[T: BaseModel](value: T, model_cls: type[T]) -> T:
    raw: object = value
    if isinstance(raw, model_cls):
        return raw
    return model_cls.model_validate(raw)


def _link(
    inventory: ContentInventory,
    index: ConceptIndex,
    options: MatchingOptions,
    supplied: tuple[CandidateSpan, ...] | None,
) -> ConceptLinkResult:
    inventory = _coerce(inventory, ContentInventory)
    index = _coerce(index, ConceptIndex)
    options = _coerce(options, MatchingOptions)
    surfaces, exclusions = inventory_surfaces(inventory)
    lookup = {(item.item_id, item.field_pointer): item for item in surfaces}
    requested: dict[tuple[str, str], set[tuple[int, int]]] = defaultdict(set)
    if supplied is not None:
        for span in supplied:
            span = _coerce(span, CandidateSpan)
            surface = lookup.get((span.item_id, span.field_pointer))
            if surface is None or surface.text[span.start:span.end] != span.quote:
                raise ValueError("supplied candidate does not resolve to its exact source surface")
            requested[span.item_id, span.field_pointer].add((span.start, span.end))
    resources, matcher = _compiled_index(index)
    mentions: list[Mention] = []
    identity = inventory.semantic_digest
    if identity is None:
        raise ValueError("inventory has no identity")
    for surface in surfaces:
        reasons: dict[tuple[int, int], dict[str, list[LexicalEntry]]] = {}
        if supplied is not None:
            reasons = {span: {} for span in requested[surface.item_id, surface.field_pointer]}
        for span, entry in _matches(surface, matcher, acronym_case_sensitive=options.acronym_case_sensitive):
            if supplied is not None and span not in reasons:
                continue
            targets = reasons.setdefault(span, {})
            evidence = targets.setdefault(entry.curie, [])
            if entry not in evidence:
                evidence.append(entry)
        ordered_spans = (
            sorted(reasons.items())
            if supplied is not None
            else _select_non_overlapping(reasons)
        )
        for (start, end), targets in ordered_spans:
            mentions.append(
                _build_mention(
                    inventory_identity=identity,
                    surface=surface,
                    start=start,
                    end=end,
                    targets=targets,
                    resources=resources,
                )
            )
    return ConceptLinkResult(
        source=inventory.source,
        inventory_identity=identity,
        source_adapter=inventory.source_contract,
        ontology=index.identity,
        implementation_identity=implementation_identity(),
        options=options,
        surfaces=surfaces,
        exclusions=exclusions,
        supplied_candidates=supplied,
        mentions=tuple(mentions),
    )


def scan_text_mentions(
    text: str,
    index: ConceptIndex | None = None,
) -> tuple[tuple[int, int, str], ...]:
    """Scan prepared text for deterministic non-overlapping proper-noun mentions."""
    if not text:
        return ()
    resolved_index = index or ConceptIndex.load()
    _, matcher = _compiled_index(resolved_index)
    synthetic = Surface(
        item_id="prepared:text",
        field_pointer="/text",
        text=text,
        classification=ContentClass.PARAGRAPH,
        origin=SourceOrigin(authorship=AuthorshipRole.AUTHORED),
        anchors=(ItemAnchor(artifact_identity="prepared", item_identity="prepared:text"),),
    )
    by_span: dict[tuple[int, int], dict[str, list[LexicalEntry]]] = {}
    for (start, end), entry in _matches(
        synthetic,
        matcher,
        acronym_case_sensitive=_DEFAULT_OPTIONS.acronym_case_sensitive,
    ):
        targets = by_span.setdefault((start, end), {})
        evidence = targets.setdefault(entry.curie, [])
        if entry not in evidence:
            evidence.append(entry)
    ordered: list[tuple[int, int, str]] = []
    for (start, end), targets in _select_non_overlapping(by_span):
        if len(targets) != 1:
            continue
        curie, rules = next(iter(targets.items()))
        if any(rule.requires_llm_disambiguation for rule in rules):
            continue
        ordered.append((start, end, curie))
    return tuple(ordered)


def link_inventory(
    inventory: ContentInventory,
    index: ConceptIndex,
    *,
    options: MatchingOptions = _DEFAULT_OPTIONS,
) -> ConceptLinkResult:
    """Scan each represented surface using Central_Configs v5 Stage 1 rules."""
    return _link(inventory, index, options, None)


def resolve_candidates(
    inventory: ContentInventory,
    index: ConceptIndex,
    candidates: tuple[CandidateSpan, ...],
    *,
    options: MatchingOptions = _DEFAULT_OPTIONS,
) -> ConceptLinkResult:
    """Resolve exact supplied spans, retaining unmatched phrases explicitly."""
    return _link(inventory, index, options, candidates)


def link_source(
    source: SourceArtifact,
    index: ConceptIndex,
    *,
    options: MatchingOptions = _DEFAULT_OPTIONS,
) -> ConceptLinkResult:
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


def validate_result(
    result: ConceptLinkResult,
    inventory: ContentInventory,
    index: ConceptIndex,
    *,
    options: MatchingOptions = _DEFAULT_OPTIONS,
) -> None:
    """Reconcile persisted evidence with the actual inputs and current implementation."""
    result = ConceptLinkResult.model_validate(result.model_dump())
    if (
        result.source != inventory.source
        or result.inventory_identity != inventory.semantic_digest
        or result.source_adapter != inventory.source_contract
        or result.ontology != index.identity
        or result.options != options
        or result.implementation_identity != implementation_identity()
    ):
        raise ValueError("stale concept links: input or implementation identity differs")
    expected = _link(inventory, index, options, result.supplied_candidates)
    if result != expected:
        raise ValueError("stale or invalid concept links: source, inventory, ontology, options or implementation differs")

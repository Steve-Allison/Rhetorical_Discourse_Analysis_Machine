"""Deterministic single-turn `(quote, occurrence)` grounder and section-aligned sharding."""

from dataclasses import dataclass
from typing import Annotated

from pydantic import Field, PositiveInt, StringConstraints

from rdam._llm import PromptPayload
from rdam._strict import StrictModel
from rdam.contracts import ProviderRequest
from rdam.ingest.contracts.evidence import SourceEvidenceSpan
from rdam.ingest.substrate import (
    LinguisticSubstrate,
    SignalSpan,
    UnitSpan,
    build_linguistic_substrate,
    render_cached_source_prefix,
)

type ExactText = Annotated[str, StringConstraints(min_length=1)]


class QuoteRef(StrictModel):
    """LLM-emitted verbatim quotation reference resolved deterministically to character offsets."""

    quote: ExactText = Field(
        description=(
            "Exact character-for-character substring from the unit body text in <source_document> "
            "(never include [u_k | ...] bracketed headers)."
        )
    )
    occurrence: PositiveInt = Field(
        default=1,
        description="1-based literal occurrence index of this exact quote in the document.",
    )


def find_all_occurrences(source_text: str, substring: str) -> tuple[tuple[int, int], ...]:
    """Return all `(start, end)` literal occurrences of `substring` in `source_text`."""
    if not substring:
        return ()
    spans: list[tuple[int, int]] = []
    width = len(substring)
    cursor = source_text.find(substring)
    while cursor >= 0:
        spans.append((cursor, cursor + width))
        cursor = source_text.find(substring, cursor + 1)
    return tuple(spans)


def _collapse_ws(value: str) -> str:
    return " ".join(value.split())


def resolve_quote(
    ref: QuoteRef,
    source_text: str,
    *,
    field_name: str = "quote",
) -> SourceEvidenceSpan:
    """Resolve `QuoteRef` to an exact `SourceEvidenceSpan` or raise an actionable `ValueError`."""
    matches = find_all_occurrences(source_text, ref.quote)
    if not matches:
        hint = ""
        if ref.quote.startswith("[u_") and "]" in ref.quote:
            hint = " Do not include [u_k | ...] unit metadata headers inside `quote`."
        else:
            lowered_pos = source_text.lower().find(ref.quote.lower())
            if lowered_pos >= 0:
                exact = source_text[lowered_pos : lowered_pos + len(ref.quote)]
                hint = f" Case mismatch; source contains {exact!r} at [{lowered_pos}:{lowered_pos + len(ref.quote)}]."
            elif _collapse_ws(ref.quote) and _collapse_ws(ref.quote) in _collapse_ws(source_text):
                hint = " Whitespace/newline mismatch; copy exact characters without re-wrapping whitespace."
        preview = ref.quote if len(ref.quote) <= 96 else f"{ref.quote[:93]}..."
        raise ValueError(f"{field_name}: verbatim quote {preview!r} does not appear in source text.{hint}")
    if ref.occurrence > len(matches):
        raise ValueError(
            f"{field_name}: requested occurrence={ref.occurrence}, "
            f"but quote occurs only {len(matches)} time(s) at {list(matches)}."
        )
    start, end = matches[ref.occurrence - 1]
    return SourceEvidenceSpan(start=start, end=end, text=ref.quote)


class GroundingCollector:
    """Batch multiple quote and formalism validation errors into a single `ModelRetry` turn."""

    def __init__(self, source_text: str) -> None:
        self.source_text = source_text
        self._errors: list[str] = []

    def resolve(self, ref: QuoteRef, *, field_name: str) -> SourceEvidenceSpan | None:
        try:
            return resolve_quote(ref, self.source_text, field_name=field_name)
        except ValueError as exc:
            self._errors.append(str(exc))
            return None

    def error(self, message: str) -> None:
        self._errors.append(message)

    @property
    def has_errors(self) -> bool:
        return bool(self._errors)

    def raise_if_errors(self) -> None:
        if self._errors:
            bulleted = "\n".join(f"- {item}" for item in self._errors)
            raise ValueError(f"Fix all {len(self._errors)} validation issue(s):\n{bulleted}")


@dataclass(frozen=True, slots=True)
class SubstrateShard:
    """Contiguous section-aligned slice of a `LinguisticSubstrate` with global offset mapping."""

    shard_index: int
    char_offset: int
    substrate: LinguisticSubstrate

    def to_global_span(self, local_span: SourceEvidenceSpan) -> SourceEvidenceSpan:
        return SourceEvidenceSpan(
            start=self.char_offset + local_span.start,
            end=self.char_offset + local_span.end,
            text=local_span.text,
        )


def shard_substrate(
    substrate: LinguisticSubstrate,
    *,
    max_chars: int = 12_000,
) -> tuple[SubstrateShard, ...]:
    """Split a dense `LinguisticSubstrate` along section/unit boundaries when `len(text) > max_chars`."""
    if max_chars <= 0:
        raise ValueError("max_chars must be positive")
    if len(substrate.text) <= max_chars or len(substrate.units) <= 1:
        return (SubstrateShard(shard_index=0, char_offset=0, substrate=substrate),)

    groups: list[list[UnitSpan]] = []
    current: list[UnitSpan] = []
    for unit in substrate.units:
        if current:
            projected_span = unit.end - current[0].start
            section_changed = (
                unit.section_heading_xpath != current[-1].section_heading_xpath
                and projected_span >= max_chars // 2
            )
            if projected_span > max_chars or section_changed:
                groups.append(current)
                current = [unit]
                continue
        current.append(unit)
    if current:
        groups.append(current)

    shards: list[SubstrateShard] = []
    for idx, group in enumerate(groups):
        base_start = group[0].start
        base_end = group[-1].end
        shard_text = substrate.text[base_start:base_end]
        local_units = tuple(
            UnitSpan(
                unit_id=u.unit_id,
                segment_id=u.segment_id,
                start=u.start - base_start,
                end=u.end - base_start,
                text=u.text,
                classification=u.classification,
                dclq_xpath=u.dclq_xpath,
                xml_path=u.xml_path,
                section_heading_xpath=u.section_heading_xpath,
                speaker=u.speaker,
                page=u.page,
                table_cell=u.table_cell,
            )
            for u in group
        )
        unit_ids = {u.unit_id for u in group}
        local_sentences = tuple(
            sent
            for sent in substrate.sentences
            if sent.unit_id in unit_ids
        )
        local_signals = tuple(
            SignalSpan(
                kind=sig.kind,
                label=sig.label,
                start=sig.start - base_start,
                end=sig.end - base_start,
                text=sig.text,
                unit_id=sig.unit_id,
            )
            for sig in substrate.signals
            if base_start <= sig.start and sig.end <= base_end
        )
        shard_digest = f"{substrate.prepared_digest}:shard:{idx}" if substrate.prepared_digest else f"shard:{idx}"
        shards.append(
            SubstrateShard(
                shard_index=idx,
                char_offset=base_start,
                substrate=LinguisticSubstrate(
                    prepared_digest=shard_digest,
                    text=shard_text,
                    units=local_units,
                    sentences=local_sentences,
                    signals=local_signals,
                ),
            )
        )
    return tuple(shards)


def substrate_for_request(request: ProviderRequest) -> LinguisticSubstrate | None:
    """Build the deterministic `LinguisticSubstrate` when a `SourceProjection` is attached."""
    if request.projection is None:
        return None
    inventory = request.preparation.inventory if request.preparation is not None else None
    return build_linguistic_substrate(request.projection.prepared_document, inventory)


def prompt_payload_for_request(request: ProviderRequest, *, task_prompt: str = "") -> PromptPayload | None:
    """Build a KV-cacheable `PromptPayload` over the shared `<source_document>` prefix."""
    substrate = substrate_for_request(request)
    if substrate is None:
        return None
    return PromptPayload(
        source_text=substrate.text,
        cached_prefix=render_cached_source_prefix(substrate),
        task_prompt=task_prompt,
        cache_key=f"rdam:{request.source.source_id.hex_digest[:24]}",
    )


__all__ = [
    "GroundingCollector",
    "QuoteRef",
    "SubstrateShard",
    "find_all_occurrences",
    "prompt_payload_for_request",
    "resolve_quote",
    "shard_substrate",
    "substrate_for_request",
]

"""Shared deterministic linguistic substrate and KV-cached source renderer."""

from dataclasses import dataclass
from functools import cache, lru_cache
from typing import Literal

from ahocorasick_rs import AhoCorasick, MatchKind
from razdel import sentenize, tokenize

from rdam.concepts.linker import scan_text_mentions
from rdam.ingest.contracts.preparation import ContentInventory, PreparedDocument, SegmentKind
from rdam.ingest.contracts.source import (
    ContentInventoryItem,
    PageAnchor,
    SourcePathAnchor,
    TableCoordinateAnchor,
)
from rdam.ingest.doclang.loader import to_dclq_xpath

type SignalCategory = Literal[
    "discourse_connective",
    "epistemic_marker",
    "speech_act_cue",
    "concept_mention",
]

_DISCOURSE_CONNECTIVES: tuple[tuple[str, str], ...] = (
    ("on the other hand", "Comparison.Contrast"),
    ("in other words", "Expansion.Equivalence"),
    ("as a result", "Contingency.Cause.Result"),
    ("for example", "Expansion.Instantiation"),
    ("for instance", "Expansion.Instantiation"),
    ("in addition", "Expansion.Conjunction"),
    ("in contrast", "Comparison.Contrast"),
    ("in conclusion", "Contingency.Cause.Result"),
    ("in particular", "Expansion.Level-of-detail.Arg2-as-detail"),
    ("in order to", "Contingency.Purpose.Arg2-as-goal"),
    ("even though", "Comparison.Concession.Arg1-as-denier"),
    ("so that", "Contingency.Purpose.Arg2-as-goal"),
    ("furthermore", "Expansion.Conjunction"),
    ("nevertheless", "Comparison.Concession.Arg2-as-denier"),
    ("nonetheless", "Comparison.Concession.Arg2-as-denier"),
    ("consequently", "Contingency.Cause.Result"),
    ("subsequently", "Temporal.Asynchronous.Precedence"),
    ("specifically", "Expansion.Level-of-detail.Arg2-as-detail"),
    ("alternatively", "Expansion.Disjunction"),
    ("accordingly", "Contingency.Cause.Result"),
    ("meanwhile", "Temporal.Synchronous"),
    ("therefore", "Contingency.Cause.Result"),
    ("otherwise", "Contingency.Negative-condition.Arg2-as-negCond"),
    ("moreover", "Expansion.Conjunction"),
    ("although", "Comparison.Concession.Arg1-as-denier"),
    ("however", "Comparison.Contrast"),
    ("because", "Contingency.Cause.Reason"),
    ("whereas", "Comparison.Contrast"),
    ("instead", "Expansion.Substitution.Arg2-as-subst"),
    ("unless", "Contingency.Negative-condition.Arg2-as-negCond"),
    ("though", "Comparison.Concession.Arg1-as-denier"),
    ("while", "Comparison.Contrast"),
    ("since", "Contingency.Cause.Reason"),
    ("thus", "Contingency.Cause.Result"),
    ("hence", "Contingency.Cause.Result"),
)

_EPISTEMIC_MARKERS: tuple[tuple[str, str], ...] = (
    ("beyond doubt", "booster"),
    ("without doubt", "booster"),
    ("undoubtedly", "booster"),
    ("definitely", "booster"),
    ("certainly", "booster"),
    ("obviously", "booster"),
    ("clearly", "booster"),
    ("necessarily", "booster"),
    ("presumably", "hedge"),
    ("apparently", "hedge"),
    ("allegedly", "hedge"),
    ("reportedly", "hedge"),
    ("arguably", "hedge"),
    ("generally", "hedge"),
    ("typically", "hedge"),
    ("probably", "hedge"),
    ("possibly", "hedge"),
    ("unlikely", "hedge"),
    ("perhaps", "hedge"),
    ("likely", "hedge"),
    ("might", "modal_hedge"),
    ("could", "modal_hedge"),
    ("must", "modal_booster"),
)

_SPEECH_ACT_CUES: tuple[tuple[str, str], ...] = (
    ("we recommend", "directive"),
    ("i recommend", "directive"),
    ("we propose", "directive"),
    ("i propose", "directive"),
    ("must not", "prohibition"),
    ("shall not", "prohibition"),
    ("hereby", "declaration"),
    ("promise", "commissive"),
    ("guarantee", "commissive"),
    ("commit to", "commissive"),
    ("undertake to", "commissive"),
    ("concede", "concession"),
    ("disagree", "disagreement"),
    ("object to", "objection"),
    ("contend", "assertive"),
)


@dataclass(frozen=True, slots=True)
class TokenSpan:
    start: int
    end: int
    text: str


@dataclass(frozen=True, slots=True)
class SentenceSpan:
    sentence_id: str
    start: int
    end: int
    text: str
    unit_id: str | None
    tokens: tuple[TokenSpan, ...]


@dataclass(frozen=True, slots=True)
class UnitSpan:
    unit_id: str
    segment_id: str
    start: int
    end: int
    text: str
    classification: str
    dclq_xpath: str | None
    xml_path: str | None
    section_heading_xpath: str | None
    speaker: str | None
    page: int | None
    table_cell: tuple[int, int] | None


@dataclass(frozen=True, slots=True)
class SignalSpan:
    kind: SignalCategory
    label: str
    start: int
    end: int
    text: str
    unit_id: str | None


@dataclass(frozen=True, slots=True)
class LinguisticSubstrate:
    prepared_digest: str
    text: str
    units: tuple[UnitSpan, ...]
    sentences: tuple[SentenceSpan, ...]
    signals: tuple[SignalSpan, ...]

    def unit_at_offset(self, offset: int) -> UnitSpan | None:
        for unit in self.units:
            if unit.start <= offset < unit.end:
                return unit
        return None

    def units_overlapping(self, start: int, end: int) -> tuple[UnitSpan, ...]:
        return tuple(unit for unit in self.units if unit.start < end and start < unit.end)


@cache
def _cue_automaton() -> tuple[AhoCorasick, tuple[tuple[SignalCategory, str], ...]]:
    patterns: list[str] = []
    metadata: list[tuple[SignalCategory, str]] = []
    for surface, sense in _DISCOURSE_CONNECTIVES:
        patterns.append(surface)
        metadata.append(("discourse_connective", sense))
    for surface, role in _EPISTEMIC_MARKERS:
        patterns.append(surface)
        metadata.append(("epistemic_marker", role))
    for surface, act in _SPEECH_ACT_CUES:
        patterns.append(surface)
        metadata.append(("speech_act_cue", act))
    return AhoCorasick(patterns, matchkind=MatchKind.LeftmostLongest), tuple(metadata)


def _is_word_char(ch: str) -> bool:
    return ch.isalnum() or ch == "_"


def _word_bounded(text: str, start: int, end: int) -> bool:
    if start > 0 and _is_word_char(text[start - 1]):
        return False
    return not (end < len(text) and _is_word_char(text[end]))


def _build_units(
    prepared: PreparedDocument,
    items_by_id: dict[str, ContentInventoryItem],
) -> tuple[UnitSpan, ...]:
    units: list[UnitSpan] = []
    unit_index = 0
    for segment in prepared.segments:
        if segment.kind is SegmentKind.SEPARATOR or not segment.text:
            continue
        primary_item = (
            items_by_id.get(segment.contributing_item_ids[0]) if segment.contributing_item_ids else None
        )
        attrs = dict(primary_item.provider_attributes) if primary_item is not None else {}
        xml_path = next(
            (
                anchor.path
                for anchor in segment.source_anchors
                if isinstance(anchor, SourcePathAnchor) and anchor.path_kind == "xml_path"
            ),
            None,
        )
        dclq_xpath = attrs.get("dclq_xpath") or (to_dclq_xpath(xml_path) if xml_path is not None else None)
        page = next(
            (anchor.page for anchor in segment.source_anchors if isinstance(anchor, PageAnchor)),
            None,
        )
        cell_anchor = next(
            (anchor for anchor in segment.source_anchors if isinstance(anchor, TableCoordinateAnchor)),
            None,
        )
        speaker: str | None = None
        if primary_item is not None and primary_item.speaker is not None:
            speaker = primary_item.speaker.display_name or primary_item.speaker.participant_id
        classification = primary_item.classification.value if primary_item is not None else "paragraph"
        units.append(
            UnitSpan(
                unit_id=f"u_{unit_index}",
                segment_id=segment.segment_id,
                start=segment.prepared_range.start,
                end=segment.prepared_range.end,
                text=segment.text,
                classification=classification,
                dclq_xpath=dclq_xpath,
                xml_path=xml_path,
                section_heading_xpath=attrs.get("dclq_section_heading_xpath"),
                speaker=speaker,
                page=page,
                table_cell=(cell_anchor.row, cell_anchor.column) if cell_anchor is not None else None,
            )
        )
        unit_index += 1
    return tuple(units)


def _build_sentences(units: tuple[UnitSpan, ...]) -> tuple[SentenceSpan, ...]:
    sentences: list[SentenceSpan] = []
    sent_index = 0
    for unit in units:
        for sent in sentenize(unit.text):
            if not sent.text.strip():
                continue
            abs_start = unit.start + sent.start
            abs_end = unit.start + sent.stop
            tokens = tuple(
                TokenSpan(
                    start=abs_start + tok.start,
                    end=abs_start + tok.stop,
                    text=tok.text,
                )
                for tok in tokenize(sent.text)
                if tok.text.strip()
            )
            sentences.append(
                SentenceSpan(
                    sentence_id=f"s_{sent_index}",
                    start=abs_start,
                    end=abs_end,
                    text=sent.text,
                    unit_id=unit.unit_id,
                    tokens=tokens,
                )
            )
            sent_index += 1
    return tuple(sentences)


def _scan_signals(text: str, units: tuple[UnitSpan, ...]) -> tuple[SignalSpan, ...]:
    if not text:
        return ()
    lowered = text.lower()
    # Guard against Unicode characters whose `.lower()` changes string length (e.g. 'İ' -> 'i\u0307').
    if len(lowered) != len(text):
        lowered = "".join(ch.lower() if len(ch.lower()) == 1 else ch for ch in text)

    def _unit_id_for(offset: int) -> str | None:
        for unit in units:
            if unit.start <= offset < unit.end:
                return unit.unit_id
        return None

    signals: list[SignalSpan] = []
    cue_ac, cue_meta = _cue_automaton()
    for pattern_idx, start, end in cue_ac.find_matches_as_indexes(lowered):
        if not _word_bounded(text, start, end):
            continue
        category, label = cue_meta[pattern_idx]
        signals.append(
            SignalSpan(
                kind=category,
                label=label,
                start=start,
                end=end,
                text=text[start:end],
                unit_id=_unit_id_for(start),
            )
        )

    for start, end, target in scan_text_mentions(text):
        signals.append(
            SignalSpan(
                kind="concept_mention",
                label=target,
                start=start,
                end=end,
                text=text[start:end],
                unit_id=_unit_id_for(start),
            )
        )

    signals.sort(key=lambda item: (item.start, item.end, item.kind))
    return tuple(signals)


def build_linguistic_substrate(
    prepared: PreparedDocument,
    inventory: ContentInventory | None = None,
) -> LinguisticSubstrate:
    """Build deterministic unit, sentence, token, and lexical-signal spans over prepared text."""
    digest = prepared.semantic_digest.hex_digest if prepared.semantic_digest is not None else ""
    items_by_id = {item.item_id: item for item in inventory.items} if inventory is not None else {}
    units = _build_units(prepared, items_by_id)
    sentences = _build_sentences(units)
    signals = _scan_signals(prepared.text, units)
    return LinguisticSubstrate(
        prepared_digest=digest,
        text=prepared.text,
        units=units,
        sentences=sentences,
        signals=signals,
    )


@lru_cache(maxsize=32)
def _cached_prefix_by_key(
    prepared_digest: str,
    unit_headers_and_texts: tuple[tuple[str, str], ...],
    signal_lines: tuple[str, ...],
) -> str:
    del prepared_digest
    blocks: list[str] = ["<source_document>"]
    for header, body in unit_headers_and_texts:
        blocks.append(header)
        blocks.append(body)
        blocks.append("")
    if blocks[-1] == "":
        blocks.pop()
    blocks.append("</source_document>")
    if signal_lines:
        blocks.append("<linguistic_signals>")
        blocks.extend(signal_lines)
        blocks.append("</linguistic_signals>")
    return "\n".join(blocks)


def render_cached_source_prefix(substrate: LinguisticSubstrate) -> str:
    """Render the byte-identical shared prefix for LLM KV-cache reuse across all techniques."""
    unit_entries: list[tuple[str, str]] = []
    for unit in substrate.units:
        parts = [unit.unit_id, f"kind={unit.classification}"]
        if unit.dclq_xpath is not None:
            parts.append(f"xpath={unit.dclq_xpath}")
        if unit.section_heading_xpath is not None:
            parts.append(f"section={unit.section_heading_xpath}")
        if unit.speaker is not None:
            parts.append(f"speaker={unit.speaker}")
        if unit.page is not None:
            parts.append(f"page={unit.page}")
        if unit.table_cell is not None:
            parts.append(f"cell=({unit.table_cell[0]},{unit.table_cell[1]})")
        unit_entries.append((f"[{' | '.join(parts)}]", unit.text))

    signal_lines = tuple(
        f"- {sig.unit_id or 'doc'} [{sig.kind}:{sig.label}] {sig.text!r}"
        for sig in substrate.signals[:128]
    )
    return _cached_prefix_by_key(substrate.prepared_digest, tuple(unit_entries), signal_lines)


__all__ = [
    "LinguisticSubstrate",
    "SentenceSpan",
    "SignalSpan",
    "TokenSpan",
    "UnitSpan",
    "build_linguistic_substrate",
    "render_cached_source_prefix",
]

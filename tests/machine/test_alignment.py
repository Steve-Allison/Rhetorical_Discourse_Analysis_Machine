"""Two native formalisms share source anchors without sharing an analytical structure."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Literal

from pydantic import ValidationError
from pydantic_ai import models
from pydantic_ai.messages import ModelMessage, ModelResponse, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
import pytest

from rdam import AggregateRequest, Machine, ResultOutcome, Technique
from rdam.ingest.alignment import SourceSelection, align_payload
from rdam.ingest.contracts.evidence import SourceEvidenceSpan
from rdam.ingest.contracts.preparation import ContentInventory, SourceProjection
from rdam.ingest.contracts.source import SourceArtifact
from rdam.ingest.projection import project
from rdam.ingest.service import ProductionIngestor
from rdam.toulmin.provider import ToulminProvider
from rdam.sdrt.provider import SdrtProvider


def test_native_findings_alignment_shares_only_source_coordinates(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-not-used")
    monkeypatch.setattr(models, "ALLOW_MODEL_REQUESTS", False)
    text = "Evidence supports the decision."
    toulmin, sdrt = ToulminProvider(), SdrtProvider()
    proposals = (
        {"layouts": [{
            "claim": "Accept the decision.", "grounds": [text],
            "warrant": "Decisions supported by evidence merit acceptance.",
            "warrant_origin": "reconstructed",
            "warrant_evidence": [{"start": 0, "end": len(text), "text": text}],
            "warrant_origin_reason": None,
        }]},
        {"edus": [{"unit_id": "e1", "text": text, "start": 0, "end": len(text)}], "relations": []},
    )
    def respond(_messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        output = info.output_tools[0]
        properties = output.parameters_json_schema["properties"]
        payload = proposals[0] if "layouts" in properties else proposals[1]
        return ModelResponse(parts=[ToolCallPart(output.name, payload)])

    @asynccontextmanager
    async def model_for_test(_model: str, *, timeout_seconds: float) -> AsyncGenerator[FunctionModel]:
        assert timeout_seconds > 0
        yield FunctionModel(respond)

    monkeypatch.setattr("rdam._llm._model_without_implicit_retries", model_for_test)
    result = Machine([toulmin, sdrt]).analyse(AggregateRequest.for_text(text, (Technique.TOULMIN, Technique.SDRT)))
    first, second = result.outcomes
    assert isinstance(first, ResultOutcome) and isinstance(second, ResultOutcome)
    assert first.result.formalism_id == "toulmin_layout"
    assert second.result.formalism_id == "sdrs_graph"
    assert "layouts" in first.result.payload and "edus" not in first.result.payload
    assert "edus" in second.result.payload and "layouts" not in second.result.payload
    left = next(item for item in first.result.source_alignment if item.payload_path.endswith("/grounds/0"))
    right = next(item for item in second.result.source_alignment if item.payload_path.endswith("/text"))
    assert left.prepared_range == right.prepared_range
    assert left.source_anchors == right.source_anchors
    assert left.contributing_item_ids == right.contributing_item_ids
    assert left.relationship == "literal_occurrence"
    assert right.relationship == "exact_quote"
    assert result.lineage == ()


def _projection(text: str) -> SourceProjection:
    source = SourceArtifact.from_text(text, source_name="alignment-regression")
    prepared = ProductionIngestor().prepare(source)
    return project(ContentInventory.from_preparation(prepared), ToulminProvider().content_requirement)


def test_only_explicitly_selected_source_fields_align() -> None:
    text = "open Implicit Contrast Evidence."
    payload = {"status": "open", "type": "Implicit", "sense": "Contrast", "grounds": ["Evidence."]}
    projection = _projection(text)
    assert align_payload(payload, projection, selections=()) == ()
    alignments = align_payload(payload, projection, selections=(
        SourceSelection(payload_path="/grounds/0", relationship="literal_occurrence"),
    ))
    assert [(item.payload_path, item.quote) for item in alignments] == [("/grounds/0", "Evidence.")]


@pytest.mark.parametrize("relationship", ("exact_quote", "literal_occurrence"))
def test_every_repeated_eligible_match_is_retained(
    relationship: Literal["exact_quote", "literal_occurrence"],
) -> None:
    projection = _projection("Éva saw Éva.")
    alignments = align_payload({"name": "Éva"}, projection, selections=(
        SourceSelection(payload_path="/name", relationship=relationship),
    ))
    assert [(item.prepared_range.start, item.prepared_range.end) for item in alignments] == [(0, 3), (8, 11)]
    assert all(item.relationship == relationship for item in alignments)


def test_supporting_passage_does_not_require_interpretation_to_be_a_quotation() -> None:
    text = "The bridge has visible cracks."
    selection = SourceSelection(
        payload_path="/warrant", relationship="supporting_passage",
        span=SourceEvidenceSpan(start=0, end=len(text), text=text),
    )
    alignments = align_payload({"warrant": "Damaged bridges may require closure."}, _projection(text), selections=(selection,))
    assert len(alignments) == 1
    assert alignments[0].quote == text
    assert alignments[0].relationship == "supporting_passage"


@pytest.mark.parametrize("relationship", ("exact_quote", "literal_occurrence"))
def test_exact_and_literal_selections_cannot_attach_different_text(
    relationship: Literal["exact_quote", "literal_occurrence"],
) -> None:
    with pytest.raises(ValueError, match="must equal"):
        align_payload({"claim": "Close the bridge."}, _projection("Cracks are visible."), selections=(
            SourceSelection(payload_path="/claim", relationship=relationship,
                            span=SourceEvidenceSpan(start=0, end=6, text="Cracks")),
        ))


def test_supporting_passage_without_declared_span_is_rejected() -> None:
    with pytest.raises(ValidationError):
        SourceSelection(payload_path="/warrant", relationship="supporting_passage")


@pytest.mark.parametrize("pointer", ("grounds/0", "/absent", "/grounds/01", "/grounds/-", "/grounds/2", "/bad~2key"))
def test_invalid_or_unresolved_payload_pointers_fail(pointer: str) -> None:
    with pytest.raises(ValueError):
        align_payload({"grounds": ["Evidence."]}, _projection("Evidence."), selections=(
            SourceSelection(payload_path=pointer, relationship="exact_quote"),
        ))


@pytest.mark.parametrize("value", (None, 3, True, [], {}, "", "   "))
def test_selected_fields_must_be_nonblank_strings(value: object) -> None:
    with pytest.raises(ValueError, match="nonblank string"):
        align_payload({"field": value}, _projection("Evidence."), selections=(
            SourceSelection(payload_path="/field", relationship="literal_occurrence"),
        ))


def test_escaped_json_pointer_names_resolve_exactly() -> None:
    alignments = align_payload({"a/b~c": "Evidence."}, _projection("Evidence."), selections=(
        SourceSelection(payload_path="/a~1b~0c", relationship="exact_quote"),
    ))
    assert len(alignments) == 1
    assert alignments[0].payload_path == "/a~1b~0c"


def test_unicode_span_offsets_are_characters_and_keep_exact_declared_occurrence() -> None:
    text = "🙂 café — café"
    start = text.rindex("café")
    span = SourceEvidenceSpan(start=start, end=start + len("café"), text="café")
    alignments = align_payload({"quote": "café"}, _projection(text), selections=(
        SourceSelection(payload_path="/quote", relationship="exact_quote", span=span),
    ))
    assert len(alignments) == 1
    assert alignments[0].prepared_range.start == start
    assert alignments[0].prepared_range.end == start + len("café")


@pytest.mark.parametrize(("start", "end", "quote"), ((1, 4, "Éva"), (90, 93, "Éva"), (0, 3, "Ada")))
def test_invalid_source_coordinates_and_fabricated_quotes_fail(start: int, end: int, quote: str) -> None:
    with pytest.raises(ValueError, match="does not match"):
        align_payload({"warrant": "A proposed interpretation."}, _projection("Éva inspected the bridge."), selections=(
            SourceSelection(payload_path="/warrant", relationship="supporting_passage",
                            span=SourceEvidenceSpan(start=start, end=end, text=quote)),
        ))


def test_source_anchors_contributors_and_projection_identity_are_derived() -> None:
    projection = _projection("Evidence.")
    (alignment,) = align_payload({"quote": "Evidence."}, projection, selections=(
        SourceSelection(payload_path="/quote", relationship="exact_quote"),
    ))
    segment = projection.prepared_document.segments[0]
    assert alignment.contributing_item_ids == segment.contributing_item_ids
    assert alignment.source_anchors == segment.source_anchors
    assert projection.projection_identity is not None
    assert alignment.projection_identity.hex_digest == projection.projection_identity.hex_digest
    assert alignment.quote == projection.prepared_document.text[alignment.prepared_range.start:alignment.prepared_range.end]


@pytest.mark.parametrize("field", ("source_anchors", "contributing_item_ids", "projection_identity"))
def test_source_selection_cannot_supply_trusted_coordinates_or_identity(field: str) -> None:
    with pytest.raises(ValidationError, match="extra_forbidden"):
        SourceSelection.model_validate({"payload_path": "/quote", "relationship": "exact_quote", field: "forged"})


def test_declared_span_from_another_projection_is_rejected() -> None:
    with pytest.raises(ValueError, match="does not match"):
        align_payload({"quote": "Éva"}, _projection("Ada inspected the bridge."), selections=(
            SourceSelection(payload_path="/quote", relationship="exact_quote",
                            span=SourceEvidenceSpan(start=0, end=3, text="Éva")),
        ))


def test_no_projection_never_fabricates_original_source_alignments() -> None:
    assert align_payload({"quote": "Evidence."}, None, selections=(
        SourceSelection(payload_path="/quote", relationship="exact_quote",
                        span=SourceEvidenceSpan(start=0, end=9, text="Evidence.")),
    )) == ()


def test_invalid_pointer_still_fails_without_projection() -> None:
    with pytest.raises(ValueError):
        align_payload({"quote": "Evidence."}, None, selections=(
            SourceSelection(payload_path="/missing", relationship="exact_quote"),
        ))


def test_declared_exact_quote_missing_from_source_is_not_silently_dropped() -> None:
    with pytest.raises(ValueError):
        align_payload({"quote": "Invented quotation."}, _projection("Evidence."), selections=(
            SourceSelection(payload_path="/quote", relationship="exact_quote"),
        ))

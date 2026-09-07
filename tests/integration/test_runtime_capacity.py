"""Exercise unknown and explicitly bounded planning through actual released models."""

from pathlib import Path

import pytest

from rdam.ingest import AnalysedOutcome, ProductionIngestor, SourceArtifact
from rdam.ingest.contracts.source import TextSpanAnchor
from rdam.ingest.policy import DEFAULT_PREPARATION_POLICY
from rdam.rst.model_loading import ParserCapacity
from rdam.rst.parser import Parser

pytestmark = pytest.mark.slow


@pytest.fixture(scope="module", params=("gumrrg-eb1d5745f3a1", "unirst-9407970f1d9d"))
def released_parser(request: pytest.FixtureRequest) -> Parser:
    return Parser.from_model_release(
        Path.home() / ".cache/isanlp_rst/model-releases", request.param, device="cpu",
    )


def test_public_ingest_preserves_one_native_tree_above_the_old_edu_cutoff(released_parser: Parser) -> None:
    assert released_parser.analysis_capacity.maximum is None
    source = SourceArtifact.from_edus(tuple("Word." for _ in range(513)), source_name="native-capacity")
    outcome = ProductionIngestor(parser=released_parser).analyse(source)
    assert isinstance(outcome, AnalysedOutcome)
    result = outcome.semantic.parser_result
    assert result is not None
    assert len(result.analysed_document.edus) == 513
    assert result.semantic.recombination is None
    assert len(outcome.semantic.preparation.semantic.analysis_plan.units) == 1
    restored = AnalysedOutcome.model_validate_json(outcome.model_dump_json())
    assert restored.semantic.parser_result == result


def test_normalized_source_keeps_original_quotes_after_native_round_trip(released_parser: Parser) -> None:
    text = "Cafe\u0301 patrons left. A storm arrived."
    policy = DEFAULT_PREPARATION_POLICY.model_copy(update={"normalization": "unicode_nfc", "semantic_digest": None})
    outcome = ProductionIngestor(parser=released_parser).analyse(
        SourceArtifact.from_text(text, source_name="normalization"), policy=policy,
    )
    assert isinstance(outcome, AnalysedOutcome)
    assert outcome.semantic.preparation.semantic.prepared_document.text == "Café patrons left. A storm arrived."
    assert outcome.semantic.preparation.semantic.transformations
    document = outcome.semantic.analysed_document
    assert document is not None
    anchors = tuple(anchor for token in document.tokens for anchor in token.source_anchors if isinstance(anchor, TextSpanAnchor))
    assert anchors
    assert all(anchor.quote == text[anchor.start:anchor.end] for anchor in anchors)
    restored = AnalysedOutcome.model_validate_json(outcome.model_dump_json())
    assert restored.semantic.analysed_document == document
    assert restored.semantic.anchors == outcome.semantic.anchors


class _ExplicitlyBoundedParser(Parser):
    @property
    def analysis_capacity(self) -> ParserCapacity:
        return ParserCapacity(unit="edu_count", maximum=2, source="test/explicit-planning-budget")


def test_real_subdivided_inference_preserves_global_source_ranges() -> None:
    parser = _ExplicitlyBoundedParser.from_model_release(
        Path.home() / ".cache/isanlp_rst/model-releases", "gumrrg-eb1d5745f3a1", device="cpu",
    )
    outcome = ProductionIngestor(parser=parser).analyse(
        SourceArtifact.from_edus(("One claim.", "Two claims.", "Three claims."), source_name="explicit-subdivision"),
    )
    assert isinstance(outcome, AnalysedOutcome)
    result = outcome.semantic.parser_result
    assert result is not None and result.semantic.recombination is not None
    assert len(result.semantic.recombination.unit_identities) == 2
    assert tuple((edu.character_range.start, edu.character_range.end, edu.text) for edu in result.analysed_document.edus) == (
        (0, 10, "One claim."), (11, 22, "Two claims."), (23, 36, "Three claims."),
    )
    restored = AnalysedOutcome.model_validate_json(outcome.model_dump_json())
    assert restored.semantic.parser_result == result
    assert restored.semantic.anchors == outcome.semantic.anchors

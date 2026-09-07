"""Closed resolved analysis policy and evidence-level semantics."""

import pytest
from pydantic import ValidationError

from rdam.ingest import EvidenceDetailPolicy, ProductionIngestor, SourceArtifact
from rdam.ingest.service import DEFAULT_ANALYSIS_POLICY
from rdam.ingest.parser_result import validate_parser_analysis_result
from rdam.ingest.contracts.inference import MappingStatus
from rdam.rst.contracts import RstDocument

from .conftest import ParserBuilder


def test_invalid_formalism_is_rejected_and_resolved_policy_is_returned(
    parser_builder: ParserBuilder,
) -> None:
    with pytest.raises(ValidationError):
        DEFAULT_ANALYSIS_POLICY.__class__.model_validate(
            {
                **DEFAULT_ANALYSIS_POLICY.model_dump(exclude={"semantic_digest"}),
                "output_formalism": "invented_graph",
            }
        )
    outcome = ProductionIngestor(parser=parser_builder()).analyse(
        SourceArtifact.from_text("First. Second.", source_name="policy.txt")
    )
    assert outcome.semantic.policy == DEFAULT_ANALYSIS_POLICY


def test_requested_genuine_distributions_change_semantic_identity(
    parser_builder: ParserBuilder,
) -> None:
    policy = DEFAULT_ANALYSIS_POLICY.__class__.model_validate(
        {
            **DEFAULT_ANALYSIS_POLICY.model_dump(exclude={"semantic_digest"}),
            "evidence_detail": EvidenceDetailPolicy.NORMALIZED_DISTRIBUTIONS,
        }
    )
    source = SourceArtifact.from_text("First. Second.", source_name="distributions.txt")
    default = ProductionIngestor(parser=parser_builder()).analyse(source)
    detailed = ProductionIngestor(parser=parser_builder()).analyse(
        source,
        analysis_policy=policy,
    )
    decisions = detailed.semantic.primary_inference
    assert decisions is not None
    assert decisions.structure_decisions[0].split_distribution is None
    assert decisions.structure_decisions[0].split_basis == "forced_two_edu"
    assert decisions.structure_decisions[0].relation_distribution is not None
    assert detailed.semantic_digest != default.semantic_digest


@pytest.mark.parametrize(
    ("mode", "status", "reason"),
    (
        ("disabled", "not_mapped", "ontology_mapping_disabled"),
        ("identity_only", "identity_only", None),
        ("provider_mapping", "not_available", "authoritative_crosswalk_unavailable"),
    ),
)
def test_mapping_policy_preserves_predictions_and_reports_actual_availability(
    parser_builder: ParserBuilder, mode: str, status: str, reason: str | None,
) -> None:
    policy = type(DEFAULT_ANALYSIS_POLICY).model_validate({
        **DEFAULT_ANALYSIS_POLICY.model_dump(exclude={"semantic_digest"}),
        "relation_interpretation": {
            **DEFAULT_ANALYSIS_POLICY.relation_interpretation.model_dump(),
            "ontology_mapping": mode,
        },
    })
    source = SourceArtifact.from_text("First. Second.", source_name="mapping-policy")
    parser = parser_builder()
    baseline = ProductionIngestor(parser=parser).analyse(source)
    outcome = ProductionIngestor(parser=parser).analyse(source, analysis_policy=policy)
    result = outcome.semantic.parser_result
    original = baseline.semantic.parser_result
    assert result is not None and original is not None
    assert result.analysis.primary_edges == original.analysis.primary_edges
    assert result.analysis.provenance.ontology_version is None
    for decision, previous in zip(
        result.semantic.primary_inference.structure_decisions,
        original.semantic.primary_inference.structure_decisions,
        strict=True,
    ):
        assert decision.joint == previous.joint
        assert decision.confidence == previous.confidence
        assert decision.relation.mapping_status.value == status
        assert decision.relation.mapping_reason == reason
        assert decision.relation.selected_ontology_concept == (
            decision.relation.raw_label if mode == "identity_only" else None
        )


def test_semantically_valid_mapping_cannot_contradict_disabled_policy(parser_builder: ParserBuilder) -> None:
    outcome = ProductionIngestor(parser=parser_builder()).analyse(
        SourceArtifact.from_text("First. Second.", source_name="mapping-mutation")
    )
    result = outcome.semantic.parser_result
    assert result is not None
    (decision,) = result.semantic.primary_inference.structure_decisions
    relation = type(decision.relation).model_validate({
        **decision.relation.model_dump(),
        "mapping_status": MappingStatus.IDENTITY_ONLY,
        "mapping_reason": None,
        "selected_ontology_concept": decision.relation.raw_label,
    })
    primary = result.semantic.primary_inference.model_copy(
        update={"structure_decisions": (decision.model_copy(update={"relation": relation}),)}
    )
    semantic = result.semantic.model_copy(update={"primary_inference": primary})
    with pytest.raises(ValueError, match="requested ontology policy"):
        validate_parser_analysis_result(result.model_copy(update={"semantic": semantic}))


def test_unsupported_relation_scheme_is_not_silently_ignored(parser_builder: ParserBuilder) -> None:
    policy = type(DEFAULT_ANALYSIS_POLICY).model_validate({
        **DEFAULT_ANALYSIS_POLICY.model_dump(exclude={"semantic_digest"}),
        "relation_interpretation": {
            **DEFAULT_ANALYSIS_POLICY.relation_interpretation.model_dump(),
            "relation_scheme": "invented_scheme",
        },
    })
    with pytest.raises(ValueError, match="provider_native relation scheme"):
        parser_builder().analyse_document(RstDocument.from_text("First. Second."), analysis_policy=policy)


def test_canonical_mapping_claim_requires_authority_provenance(parser_builder: ParserBuilder) -> None:
    outcome = ProductionIngestor(parser=parser_builder()).analyse(
        SourceArtifact.from_text("First. Second.", source_name="unsupported-mapping")
    )
    primary = outcome.semantic.primary_inference
    assert primary is not None
    relation = primary.structure_decisions[0].relation
    with pytest.raises(ValueError, match="mapping/ontology provenance"):
        type(relation).model_validate({
            **relation.model_dump(),
            "mapping_status": MappingStatus.MAPPED,
            "selected_ontology_concept": "coe:unverified",
            "mapping_reason": None,
        })

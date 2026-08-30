"""Closed resolved analysis policy and evidence-level semantics."""

import pytest
from pydantic import ValidationError

from isanlp_rst.ingest import EvidenceDetailPolicy, ProductionIngestor, SourceArtifact
from isanlp_rst.ingest.service import DEFAULT_ANALYSIS_POLICY

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
    assert decisions.structure_decisions[0].split_distribution is not None
    assert decisions.structure_decisions[0].relation_distribution is not None
    assert detailed.semantic_digest != default.semantic_digest

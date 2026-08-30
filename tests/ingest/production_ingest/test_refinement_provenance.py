"""Before/after refinement provenance invariants."""

import pytest
from pydantic import ValidationError

from isanlp_rst.ingest import SemanticVersion, Sha256Identity
from isanlp_rst.ingest.contracts.inference import RefinementRecord
from isanlp_rst.ingest.contracts.source import TextSpanAnchor


def test_refinement_requires_a_real_change_and_complete_trigger_links() -> None:
    digest = Sha256Identity(hex_digest="a" * 64)
    record = RefinementRecord(
        refinement_id="refinement:e1:relation",
        decision_kind="relation_raw",
        before_value="elaboration",
        after_value="cause",
        trigger_signal_ids=("signal:1",),
        trigger_anchors=(
            TextSpanAnchor(
                artifact_identity="document",
                start=0,
                end=7,
                quote="because",
            ),
        ),
        policy_identity=digest,
        algorithm_version=SemanticVersion(root="2.0.0"),
        graph_element_ids=("e1",),
        explanation_code="marker_refinement",
    )
    assert record.semantic_digest is not None
    with pytest.raises(ValidationError, match="must differ"):
        RefinementRecord.model_validate(
            {
                **record.model_dump(exclude={"semantic_digest"}),
                "after_value": "elaboration",
            }
        )

"""Promotion assessment protects EDU quality and structural-boundary gains."""

from rdam.rst.contracts import NodeKindEnum, OutputFormalismEnum, RstAnalysis, RstNode
from tools.production_ingest.assessor import (
    _edu_boundary_f1,
    _preparation_identity_matches,
    _structural_violations,
)


def _analysis(*spans: tuple[int, int]) -> RstAnalysis:
    return RstAnalysis(
        document_id="document",
        formalism=OutputFormalismEnum.RST_TREE,
        nodes=tuple(
            RstNode(
                node_id=index,
                kind=NodeKindEnum.EDU,
                edu_span=(index, index),
                char_span=span,
                text=f"edu-{index}",
            )
            for index, span in enumerate(spans, start=1)
        ),
        primary_edges=(),
    )


def test_edu_boundary_f1_detects_regression_without_using_source_text() -> None:
    gold = _analysis((0, 5), (6, 10))
    assert _edu_boundary_f1(gold, _analysis((0, 5), (6, 10))) == 1.0
    assert _edu_boundary_f1(gold, _analysis((0, 10))) == 0.0


def test_structural_gate_counts_pre_feature_cross_boundary_relation_and_macro_fix() -> None:
    candidate = {
        "subdivision_plan": {
            "units": [
                {"output_range": {"start": 0, "end": 5}},
                {"output_range": {"start": 5, "end": 10}},
            ]
        },
        "analysis_result": {
            "analysis_anchors": [
                {
                    "analysis_kind": "relation",
                    "prepared_ranges": [{"start": 0, "end": 10}],
                    "origin": "macro",
                }
            ]
        },
    }
    assert _structural_violations(candidate) == (1, 0)


def test_structural_gate_rejects_cross_boundary_relation_mislabelled_local() -> None:
    candidate = {
        "subdivision_plan": {
            "units": [
                {"output_range": {"start": 0, "end": 5}},
                {"output_range": {"start": 5, "end": 10}},
            ]
        },
        "analysis_result": {
            "analysis_anchors": [
                {
                    "analysis_kind": "relation",
                    "prepared_ranges": [{"start": 0, "end": 10}],
                    "origin": "local",
                }
            ]
        },
    }
    assert _structural_violations(candidate) == (1, 1)


def test_preparation_identity_requires_exact_contract_preparation_and_text() -> None:
    expectation = {
        "source_contract_digest": "contract",
        "prepared_digest": "prepared",
        "prepared_text_sha256": "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824",
    }
    assert _preparation_identity_matches(
        expectation=expectation,
        contract_digest="contract",
        prepared={"semantic_digest": "prepared", "text": "hello"},
    ) == (True, True, True)
    assert _preparation_identity_matches(
        expectation=expectation,
        contract_digest="changed",
        prepared={"semantic_digest": "prepared", "text": "hello!"},
    ) == (False, True, False)

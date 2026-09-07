"""Decision-complete primary inference evidence."""

import math

import pytest

from rdam.ingest import ProductionIngestor, SourceArtifact
from rdam.ingest.contracts.analysis import AnalysisPolicy
from rdam.ingest.contracts.base import Sha256Identity
from rdam.ingest.contracts.inference import EvidenceDetailPolicy
from rdam.ingest.identity import semantic_sha256
from rdam.ingest.vocabulary import RuntimeRelationVocabulary
from rdam.ingest.parser_result import build_parser_analysis_result
from rdam.ingest.service import DEFAULT_ANALYSIS_POLICY
from rdam.rst.annotation_rst import DiscourseUnit
from rdam.rst.contracts import DocumentToken, Edu, RstDocument, TextSpan
from rdam.rst.contracts.trace import PredictorAnalysisTrace
from rdam.rst.inference_evidence import NetworkStructureDecision

from .conftest import ParserBuilder


def test_selected_structure_relation_nuclearity_and_scores_link_to_graph(
    parser_builder: ParserBuilder,
) -> None:
    outcome = ProductionIngestor(parser=parser_builder()).analyse(
        SourceArtifact.from_text("First. Second.", source_name="primary.txt")
    )
    analysis = outcome.semantic.analysis
    evidence = outcome.semantic.primary_inference
    assert analysis is not None and evidence is not None
    assert evidence.relation_vocabulary is not None
    assert evidence.relation_vocabulary.mapping_reason == "corpus_not_declared"
    forged = RuntimeRelationVocabulary(
        corpus_name=None, scope_basis="not_declared", labels=("invented",),
        inventory_identity=Sha256Identity(hex_digest=semantic_sha256(("invented",))),
        alignment=None, mapping_reason="corpus_not_declared",
    )
    with pytest.raises(ValueError, match="Decision inventory differs"):
        type(evidence).model_validate({**evidence.model_dump(), "relation_vocabulary": forged})
    decision = evidence.structure_decisions[0]
    assert decision.selected_split == 0
    assert decision.nuclearity == "NN"
    assert decision.relation.raw_label == "same-unit"
    assert decision.confidence is not None
    assert decision.confidence.confidence_kind.value == "probability"
    assert decision.split_entropy is None
    assert decision.split_basis == "forced_two_edu"
    assert decision.confidence_basis == "joint_relation_nuclearity_given_selected_split"
    assert set(decision.node_ids) <= {node.node_id for node in analysis.nodes}
    assert set(decision.primary_edge_ids) == {edge.edge_id for edge in analysis.primary_edges}
    for segmentation in evidence.segmentation_decisions:
        assert segmentation.confidence is None
        assert segmentation.scores_unavailable_reason == "deterministic_boundary_rule"
        with pytest.raises(ValueError, match="reason matching"):
            type(segmentation).model_validate({
                **segmentation.model_dump(),
                "scores_unavailable_reason": None,
            })


def test_near_certain_joint_classes_have_bounded_marginal_mass(parser_builder: ParserBuilder) -> None:
    document = RstDocument.from_edus(("First.", "Second."), document_id="rounding-regression")
    assert document.edus is not None
    parser = parser_builder()
    analysis = parser.analyse_document(document).analysis
    logits = (0.0, -7.642683660095622, -22.700429624826874)
    weights = tuple(math.exp(value) for value in logits)
    assert math.fsum(value / sum(weights) for value in weights) > 1.0
    scores = tuple(value - math.log(math.fsum(weights)) for value in logits)
    decision = NetworkStructureDecision(
        start=0, end=1, split=0, selected_class=0,
        joint_labels=("same-unit_NN", "joint_NN", "list_NN"),
        joint_log_probabilities=scores, split_log_probabilities=None,
    )
    tokens = tuple(DocumentToken(token_id=index, text=edu.text, start=edu.start, end=edu.end,
                                 sentence_id=index, paragraph_id=0)
                   for index, edu in enumerate(document.edus))
    edus = tuple(Edu(edu_id=edu.edu_id, text=edu.text, start=edu.start, end=edu.end, token_ids=(index,))
                 for index, edu in enumerate(document.edus))
    trace = PredictorAnalysisTrace(
        root_unit=DiscourseUnit(id=1, text=document.text), analysis=analysis,
        tokens=tokens, edus=edus,
        sentence_boundaries=tuple(TextSpan(start=edu.start, end=edu.end, text=edu.text) for edu in edus),
        paragraph_boundaries=(TextSpan(start=0, end=len(document.text), text=document.text),),
        structure_decisions=(decision,), segmentation_source="presegmented",
        relation_inventory=("same-unit", "joint", "list"),
    )
    result = build_parser_analysis_result(
        parser, document, trace, policy=AnalysisPolicy.model_validate({
            **DEFAULT_ANALYSIS_POLICY.model_dump(exclude={"semantic_digest"}),
            "evidence_detail": EvidenceDetailPolicy.NORMALIZED_DISTRIBUTIONS,
        }),
        model_analysis=analysis, final_analysis=analysis, duration_ms=0.0,
    )
    exported = result.semantic.primary_inference.structure_decisions[0]
    assert exported.joint is not None and exported.joint.log_probabilities == scores
    assert exported.nuclearity_distribution is not None
    assert {item.label: item.score.value for item in exported.nuclearity_distribution.entries} == {
        "NS": 0.0, "SN": 0.0, "NN": 1.0,
    }

"""CPU/MPS decoded-graph and probability parity evidence."""

import json
from pathlib import Path

from research_harness.erst.selection import CpuMpsParityEvidence
from research_harness.erst.systems.common import DocumentPredictionRecord


def _load_predictions(path: Path) -> tuple[DocumentPredictionRecord, ...]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("prediction artifact must contain a document list")
    return tuple(DocumentPredictionRecord.model_validate(item) for item in payload)


def compare_prediction_artifacts(
    *,
    cpu_path: Path,
    mps_path: Path,
    cpu_receipt_sha256: str,
    mps_receipt_sha256: str,
    tolerance: float,
) -> CpuMpsParityEvidence:
    """Require identical graph identities and measure the largest confidence delta."""

    cpu_documents = _load_predictions(cpu_path)
    mps_documents = _load_predictions(mps_path)
    if tuple(item.document_id for item in cpu_documents) != tuple(
        item.document_id for item in mps_documents
    ):
        raise ValueError("CPU/MPS prediction document identities differ")
    max_delta = 0.0
    graphs_equal = True
    for cpu_document, mps_document in zip(cpu_documents, mps_documents, strict=True):
        cpu_edges = {
            (edge.source_id, edge.target_id, edge.relation_raw): edge.confidence
            for edge in cpu_document.edges
        }
        mps_edges = {
            (edge.source_id, edge.target_id, edge.relation_raw): edge.confidence
            for edge in mps_document.edges
        }
        if set(cpu_edges) != set(mps_edges):
            graphs_equal = False
            continue
        for identity in cpu_edges:
            max_delta = max(max_delta, abs(cpu_edges[identity] - mps_edges[identity]))
    return CpuMpsParityEvidence(
        cpu_receipt_sha256=cpu_receipt_sha256,
        mps_receipt_sha256=mps_receipt_sha256,
        max_probability_delta=max_delta,
        decoded_graphs_equal=graphs_equal,
        tolerance=tolerance,
    )


__all__ = ["compare_prediction_artifacts"]

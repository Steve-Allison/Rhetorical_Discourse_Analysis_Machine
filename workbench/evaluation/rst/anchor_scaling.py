"""Synthetic graph-anchor scaling, separate from inference and analytical quality.

Run with ``pixi run python -m workbench.evaluation.rst.anchor_scaling --sizes N ...``.
Each EDU contains one token. Sizes are experimental inputs, never production caps.
The generated balanced and left-deep binary trees have no model scores, signals,
or decisions. Measurements cover expanded graph anchors, not full reports.
"""

import argparse
from dataclasses import asdict
import json
import platform
from typing import Literal

from rdam._strict import canonical_json_bytes
from rdam.ingest.contracts.analysis import (
    AnalysedDocument, AnalysedEdu, AnalysedToken, FidelityClass, PreparedRange,
)
from rdam.ingest.contracts.base import CoverageUnit, ExactCoverage
from rdam.ingest.contracts.inference import PrimaryInferenceEvidence
from rdam.ingest.contracts.graph import StoredRstGraph
from rdam.ingest.contracts.source import TextSpanAnchor
from rdam.ingest.parser_result import analysis_anchors
from rdam.ingest.validation import validate_canonical_anchors
from rdam.rst.contracts.analysis import PrimaryRelationEdge, RstAnalysis, RstNode
from rdam.rst.contracts.enums import NodeKindEnum, NuclearityPatternEnum, OutputFormalismEnum
from workbench.evaluation.rst.persistence import measure

type Shape = Literal["balanced", "left_deep"]


def synthetic_case(size: int, shape: Shape) -> tuple[AnalysedDocument, RstAnalysis]:
    if size < 2:
        raise ValueError("binary-tree benchmark requires at least two EDUs")
    if shape not in {"balanced", "left_deep"}:
        raise ValueError("unknown synthetic tree shape")
    text = " ".join("x" for _ in range(size))
    identity = f"synthetic-anchor-scaling:{shape}:{size}"

    def anchor(start: int, end: int) -> TextSpanAnchor:
        return TextSpanAnchor(artifact_identity=identity, start=start, end=end, quote=text[start:end])

    tokens = tuple(AnalysedToken(
        token_id=f"token:{index}", order=index, text="x",
        character_range=PreparedRange(start=2 * index, end=2 * index + 1),
        source_anchors=(anchor(2 * index, 2 * index + 1),),
        sentence_id="sentence:0", paragraph_id="paragraph:0",
    ) for index in range(size))
    edus = tuple(AnalysedEdu(
        edu_id=f"edu:{index}", order=index, text=token.text, token_ids=(token.token_id,),
        character_range=token.character_range,
        sentence_id=token.sentence_id, paragraph_id=token.paragraph_id,
        prepared_segment_ids=("document:segment:0000",), source_anchors=token.source_anchors,
    ) for index, token in enumerate(tokens))
    document = AnalysedDocument(
        text=text, tokens=tokens, edus=edus,
        sentence_boundaries=(PreparedRange(start=0, end=len(text)),),
        paragraph_boundaries=(PreparedRange(start=0, end=len(text)),),
        structural_boundary_ids=(), prepared_segment_ids=("document:segment:0000",),
        source_anchors=(anchor(0, len(text)),), transformations=(), fidelity=FidelityClass.LOSSLESS,
        character_coverage=ExactCoverage(covered_units=len(text), total_units=len(text), unit=CoverageUnit.CHARACTERS),
        token_coverage=ExactCoverage(covered_units=size, total_units=size, unit=CoverageUnit.ITEMS),
        edu_coverage=ExactCoverage(covered_units=size, total_units=size, unit=CoverageUnit.ITEMS),
    )
    nodes: dict[tuple[int, int], RstNode] = {}
    edges: list[PrimaryRelationEdge] = []
    pending = [(0, size, False)]
    while pending:
        start, stop, visited = pending.pop()
        split = (start + stop) // 2 if shape == "balanced" else stop - 1
        if stop - start > 1 and not visited:
            pending.extend(((start, stop, True), (split, stop, False), (start, split, False)))
            continue
        node = RstNode(
            node_id=len(nodes) + 1,
            kind=NodeKindEnum.ROOT if (start, stop) == (0, size) else
                 NodeKindEnum.EDU if stop - start == 1 else NodeKindEnum.SPAN,
            edu_span=(start + 1, stop), char_span=(2 * start, 2 * stop - 1), text=text[2 * start:2 * stop - 1],
        )
        nodes[start, stop] = node
        if stop - start > 1:
            for child in (nodes[start, split], nodes[split, stop]):
                edges.append(PrimaryRelationEdge(
                    edge_id=f"edge:{node.node_id}:{child.node_id}", parent_id=node.node_id, child_id=child.node_id,
                    relation_raw="joint", relation_concept="joint", nuclearity=NuclearityPatternEnum.NN,
                ))
    graph = RstAnalysis(
        document_id=identity, formalism=OutputFormalismEnum.RST_TREE,
        nodes=tuple(nodes.values()), primary_edges=tuple(edges),
    )
    if len(graph.nodes) != 2 * size - 1 or len(graph.primary_edges) != 2 * size - 2:
        raise ValueError("synthetic binary-tree topology is incomplete")
    return document, graph


def measure_case(size: int, shape: Shape) -> dict[str, object]:
    document, graph = synthetic_case(size, shape)
    primary = PrimaryInferenceEvidence(segmentation_decisions=(), structure_decisions=(), refinements=())
    _, canonical_validation = measure(lambda: validate_canonical_anchors(graph, document, primary))
    anchors, resolution = measure(lambda: analysis_anchors(
        graph, document, primary, document_identity=graph.document_id,
    ))
    expected = len(document.edus) + len(graph.nodes) + len(graph.primary_edges)
    if len(anchors) != expected:
        raise ValueError("anchor inventory differs from synthetic graph")
    for item in anchors:
        for source in item.source_anchors:
            if not isinstance(source, TextSpanAnchor) or source.quote != document.text[source.start:source.end]:
                raise ValueError("resolved source quotation differs from synthetic text")
    encoded, serialization = measure(lambda: canonical_json_bytes(anchors))
    stored = StoredRstGraph.capture(graph, document.text)
    if stored.resolve(document.text) != graph:
        raise ValueError("stored graph fails exact native-text reconstruction")
    canonical, canonical_serialization = measure(lambda: canonical_json_bytes({
        "analysed_document": document, "analysis": stored,
    }))
    return {
        "shape": shape, "edus": size, "tokens": len(document.tokens), "nodes": len(graph.nodes),
        "anchors": len(anchors),
        "expanded_token_references": sum(
            len(item.token_ids) + sum(len(endpoint.token_ids) for endpoint in
                                    (item.source_endpoint, item.target_endpoint) if endpoint is not None)
            for item in anchors
        ),
        "expanded_anchor_json_bytes": len(encoded),
        "canonical_graph_and_substrate_bytes": len(canonical),
        "canonical_graph_and_substrate_serialization": asdict(canonical_serialization),
        "resolution": asdict(resolution), "expanded_serialization": asdict(serialization),
        "canonical_anchor_input_validation": asdict(canonical_validation),
        "source_quotes": "verified",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sizes", type=int, nargs="+", required=True)
    args = parser.parse_args()
    if len(set(args.sizes)) != len(args.sizes) or any(size < 2 for size in args.sizes):
        parser.error("sizes must be distinct integers of at least two")
    result = {
        "measurement_version": "3.0.0", "purpose": "synthetic_graph_and_substrate_scaling_without_inference",
        "python": platform.python_version(), "platform": platform.platform(),
        "memory_measure": "tracemalloc_allocations_excluding_preexisting_objects",
        "timing_condition": "tracemalloc_enabled_other_processes_not_controlled",
        "cases": [measure_case(size, shape) for shape in ("balanced", "left_deep") for size in args.sizes],
    }
    print(json.dumps(result, allow_nan=False, indent=2))


if __name__ == "__main__":
    main()

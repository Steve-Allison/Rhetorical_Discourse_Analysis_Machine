"""RST quality diagnostics over production sources without gold labels.

Every supported source is routed through :mod:`isanlp_rst.ingest`; this tool
does not own format-specific preparation policy or result envelopes.
"""

import argparse
from collections import defaultdict, deque
from dataclasses import asdict, dataclass
import json
import math
from pathlib import Path
from statistics import mean, median
import sys

from isanlp_rst.contracts import NodeKindEnum
from isanlp_rst.ingest import (
    ProductionAnalysisResult,
    ProductionIngestor,
    SourceArtifact,
    SourceForm,
)
from isanlp_rst.parser import Parser

_THIN_PREFIXES = ("joint", "same-unit", "same_unit", "organization")


@dataclass(frozen=True, slots=True)
class DocMetrics:
    """Per-document canonical-ingest diagnostics."""

    source: str
    source_form: str
    status: str
    prepared_chars: int
    prepared_segments: int
    edus: int
    relations: int
    joint_ratio: float
    tree_skew: float
    inventory_coverage: float
    source_coverage: float
    prepared_coverage: float
    anchor_coverage: float


def _discover(paths: list[Path]) -> list[Path]:
    out: list[Path] = []
    for path in paths:
        if path.is_dir():
            for pattern in ("*.md", "*.markdown", "*.docling.json", "*.dclg", "*.dclg.xml", "*.dclx"):
                out.extend(sorted(path.rglob(pattern)))
        else:
            out.append(path)
    return list(dict.fromkeys(out))


def _artifact(path: Path) -> SourceArtifact:
    if path.name.endswith(".docling.json"):
        return SourceArtifact.from_path(path, source_form=SourceForm.DOCLING_JSON)
    return SourceArtifact.from_path(path)


def _tree_depth(result: ProductionAnalysisResult) -> int:
    analysis = result.analysis
    if analysis is None or not analysis.nodes:
        return 0
    children: dict[int, list[int]] = defaultdict(list)
    child_ids: set[int] = set()
    for edge in analysis.primary_edges:
        children[edge.parent_id].append(edge.child_id)
        child_ids.add(edge.child_id)
    roots = sorted(node.node_id for node in analysis.nodes if node.node_id not in child_ids)
    queue = deque((root, 0) for root in roots)
    maximum = 0
    while queue:
        node_id, depth = queue.popleft()
        maximum = max(maximum, depth)
        queue.extend((child_id, depth + 1) for child_id in children[node_id])
    return maximum


def _metrics(result: ProductionAnalysisResult) -> DocMetrics:
    analysis = result.analysis
    nodes = analysis.nodes if analysis is not None else ()
    edus = sum(node.kind is NodeKindEnum.EDU for node in nodes)
    relation_by_parent: dict[int, str] = {}
    if analysis is not None:
        for edge in analysis.primary_edges:
            label = edge.relation_concept or edge.relation_raw
            if label.lower() != "span":
                relation_by_parent.setdefault(edge.parent_id, label)
    relations = len(relation_by_parent)
    thin = sum(label.lower().startswith(_THIN_PREFIXES) for label in relation_by_parent.values())
    joint_ratio = thin / relations if relations else 0.0
    skew_base = math.ceil(math.log2(edus)) if edus > 1 else 1
    prepared = result.prepared_document
    receipt = result.preparation_receipt
    return DocMetrics(
        source=result.source.source_name,
        source_form=result.source.source_form.value,
        status=result.analysis_status.value,
        prepared_chars=len(prepared.text) if prepared is not None else 0,
        prepared_segments=len(prepared.segments) if prepared is not None else 0,
        edus=edus,
        relations=relations,
        joint_ratio=round(joint_ratio, 3),
        tree_skew=round(_tree_depth(result) / skew_base, 2),
        inventory_coverage=receipt.inventory_coverage,
        source_coverage=receipt.primary_source_coverage,
        prepared_coverage=receipt.prepared_text_coverage,
        anchor_coverage=receipt.analysis_anchor_coverage,
    )


def _print_table(rows: list[DocMetrics]) -> None:
    headers = ("source", "form", "status", "chars", "segs", "edus", "rels", "joint", "skew", "coverage")
    cells = [
        (
            row.source,
            row.source_form,
            row.status,
            str(row.prepared_chars),
            str(row.prepared_segments),
            str(row.edus),
            str(row.relations),
            f"{row.joint_ratio:.3f}",
            f"{row.tree_skew:.2f}",
            f"{min(row.inventory_coverage, row.source_coverage, row.prepared_coverage, row.anchor_coverage):.3f}",
        )
        for row in rows
    ]
    widths = [max(len(header), *(len(cell[index]) for cell in cells)) for index, header in enumerate(headers)]
    print("  ".join(header.ljust(width) for header, width in zip(headers, widths, strict=True)))
    for cell in cells:
        print("  ".join(value.ljust(width) for value, width in zip(cell, widths, strict=True)))
    if len(rows) > 1:
        print()
        for label, values in (
            ("joint_ratio", [row.joint_ratio for row in rows]),
            ("tree_skew", [row.tree_skew for row in rows]),
            ("anchor_coverage", [row.anchor_coverage for row in rows]),
        ):
            print(f"{label}: mean={mean(values):.3f} median={median(values):.3f} min={min(values):.3f}")


def main(argv: list[str] | None = None) -> int:
    argument_parser = argparse.ArgumentParser(description=__doc__)
    argument_parser.add_argument("paths", nargs="+", type=Path, help="source files or directories")
    argument_parser.add_argument("--model-version", default="gumrrg", dest="model_version")
    argument_parser.add_argument("--relinventory")
    argument_parser.add_argument("--device", default="auto")
    argument_parser.add_argument("--dtype")
    argument_parser.add_argument("--json", action="store_true", help="emit JSON instead of a table")
    args = argument_parser.parse_args(argv)
    sources = _discover(args.paths)
    if not sources:
        print("No supported sources found.", file=sys.stderr)
        return 1
    parser = Parser(
        hf_model_version=args.model_version,
        relinventory=args.relinventory,
        device=args.device,
        dtype=args.dtype,
    )
    ingestor = ProductionIngestor(parser=parser)
    rows = [_metrics(ingestor.analyse(_artifact(path))) for path in sources]
    if args.json:
        print(json.dumps([asdict(row) for row in rows], ensure_ascii=False, indent=2))
    else:
        _print_table(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

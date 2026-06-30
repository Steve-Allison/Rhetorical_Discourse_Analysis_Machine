"""RST quality diagnostics over a corpus — no gold annotations required.

Parses each source with the matching format-native entry point and emits
per-document proxy metrics plus a corpus summary:

  - edus / relations        — raw tree size
  - joint_ratio             — share of relations whose label starts with
                              joint / same-unit / organization (heuristic
                              for rhetorically thin output: high = the
                              parser mostly chained instead of structuring)
  - tree_skew               — max relation depth / ceil(log2(edus));
                              ~1 is balanced, >> 1 is a degenerate chain
  - cross_boundary_ratio    — share of relations spanning > 1 primary
                              boundary (section / slide / turn / heading /
                              page / group / document — tables and code
                              blocks excluded); a spike suggests invented
                              arcs across unrelated content
  - note_ratio              — share of relations carrying an overlap
                              note (lopsided EDU/span alignment)
  - table_analyses          — count of per-table mini-parses emitted

Usage:

    pixi run rst-diag <paths...>                 # files and/or directories
    pixi run rst-diag corpus/ --json             # machine-readable
    pixi run rst-diag doc.md --model-version gumrrg --device auto

Format dispatch by suffix: ``.md`` / ``.markdown`` → parse_markdown;
``*.docling.json`` → parse_docling; ``*.dclg.xml`` → parse_doclang.
One ``Parser`` is constructed and injected across all documents.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import mean, median
from typing import Any

_THIN_PREFIXES = ("joint", "same-unit", "same_unit", "organization")
_SECONDARY_BOUNDARY_KINDS = frozenset({"table", "code_block", "field_region"})


@dataclass(frozen=True, slots=True)
class DocMetrics:
    """Per-document diagnostic metrics."""

    source: str
    format: str
    edus: int
    relations: int
    joint_ratio: float
    tree_skew: float
    cross_boundary_ratio: float
    note_ratio: float
    table_analyses: int


def _discover(paths: list[Path]) -> list[Path]:
    """Expand directories into supported source files, keep files as-is."""
    out: list[Path] = []
    for p in paths:
        if p.is_dir():
            out.extend(sorted(p.rglob("*.md")))
            out.extend(sorted(p.rglob("*.markdown")))
            out.extend(sorted(p.rglob("*.docling.json")))
            out.extend(sorted(p.rglob("*.dclg.xml")))
        else:
            out.append(p)
    return out


def _format_of(path: Path) -> str:
    name = path.name
    if name.endswith(".docling.json"):
        return "docling"
    if name.endswith(".dclg.xml"):
        return "doclang"
    if path.suffix in (".md", ".markdown"):
        return "markdown"
    raise ValueError(
        f"Unsupported source {path} — expected .md/.markdown, "
        f"*.docling.json, or *.dclg.xml"
    )


def _parse(path: Path, fmt: str, parser: Any) -> Any:
    if fmt == "markdown":
        from isanlp_rst.markdown import parse_markdown
        return parse_markdown(path, parser=parser)
    if fmt == "docling":
        from isanlp_rst.docling import parse_docling
        return parse_docling(path, parser=parser)
    from isanlp_rst.doclang import parse_doclang
    return parse_doclang(path, parser=parser)


def _metrics(path: Path, fmt: str, result: Any) -> DocMetrics:
    relations = result.relations
    edus = result.edus
    n_rel = len(relations)
    n_edu = len(edus)

    thin = sum(
        1 for r in relations if r.relation.lower().startswith(_THIN_PREFIXES)
    )
    joint_ratio = thin / n_rel if n_rel else 0.0

    max_depth = max(
        (r.depth for r in relations), default=0
    )
    skew_base = math.ceil(math.log2(n_edu)) if n_edu > 1 else 1
    tree_skew = max_depth / skew_base if skew_base else 0.0

    primary_ids = {
        b.id for b in result.boundaries if b.kind not in _SECONDARY_BOUNDARY_KINDS
    }
    cross = sum(
        1
        for r in relations
        if len(primary_ids.intersection(r.boundary_memberships)) > 1
    )
    cross_ratio = cross / n_rel if n_rel else 0.0

    noted = sum(1 for r in relations if r.note is not None)
    note_ratio = noted / n_rel if n_rel else 0.0

    return DocMetrics(
        source=path.name,
        format=fmt,
        edus=n_edu,
        relations=n_rel,
        joint_ratio=round(joint_ratio, 3),
        tree_skew=round(tree_skew, 2),
        cross_boundary_ratio=round(cross_ratio, 3),
        note_ratio=round(note_ratio, 3),
        table_analyses=len(result.table_analyses),
    )


def _print_table(rows: list[DocMetrics]) -> None:
    headers = (
        "source", "fmt", "edus", "rels", "joint", "skew", "cross", "note", "tables"
    )
    cells = [
        (
            m.source, m.format, str(m.edus), str(m.relations),
            f"{m.joint_ratio:.3f}", f"{m.tree_skew:.2f}",
            f"{m.cross_boundary_ratio:.3f}", f"{m.note_ratio:.3f}",
            str(m.table_analyses),
        )
        for m in rows
    ]
    widths = [
        max(len(h), *(len(c[i]) for c in cells)) if cells else len(h)
        for i, h in enumerate(headers)
    ]
    print("  ".join(h.ljust(w) for h, w in zip(headers, widths, strict=True)))
    for c in cells:
        print("  ".join(v.ljust(w) for v, w in zip(c, widths, strict=True)))

    if len(rows) > 1:
        print()
        for label, values in (
            ("joint_ratio", [m.joint_ratio for m in rows]),
            ("tree_skew", [m.tree_skew for m in rows]),
            ("cross_boundary_ratio", [m.cross_boundary_ratio for m in rows]),
            ("note_ratio", [m.note_ratio for m in rows]),
        ):
            print(
                f"{label}: mean={mean(values):.3f} median={median(values):.3f} "
                f"max={max(values):.3f}"
            )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="RST quality diagnostics over a corpus — no gold annotations required."
    )
    ap.add_argument("paths", nargs="+", type=Path, help="source files or directories")
    ap.add_argument("--model-version", default="gumrrg", dest="model_version")
    ap.add_argument("--relinventory", default=None)
    ap.add_argument("--device", default="auto")
    ap.add_argument("--dtype", default=None)
    ap.add_argument("--json", action="store_true", help="emit JSON instead of a table")
    args = ap.parse_args(argv)

    sources = _discover(args.paths)
    if not sources:
        print("No supported sources found.", file=sys.stderr)
        return 1

    from isanlp_rst.parser import Parser

    parser = Parser(
        hf_model_version=args.model_version,
        relinventory=args.relinventory,
        device=args.device,
        dtype=args.dtype,
    )

    rows: list[DocMetrics] = []
    for path in sources:
        fmt = _format_of(path)
        result = _parse(path, fmt, parser)
        rows.append(_metrics(path, fmt, result))

    if args.json:
        print(json.dumps([asdict(m) for m in rows], ensure_ascii=False, indent=2))
    else:
        _print_table(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

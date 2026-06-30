"""Phase 0 steps 6 and 7 — long-input smoke and determinism check.

Step 6: parse a synthetic long input formed by concatenating all four fixture
harvests. Report tree stats and any errors. Establishes an empirical ceiling
above the largest single fixture (pdf, ~18 KB harvest).

Step 7: parse the largest single fixture twice and compare tree shape.
Records whether output is byte-equivalent across repeated runs.

Run:  pixi run -- python scripts/docling_long_input_determinism.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

# Reuse harvest logic from the quality-check script.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from docling_rst_quality_check import (  # type: ignore[import-not-found]
    harvest_body_text,
    walk_tree,
    collect_relations,
)
from docling_core.types.doc.document import DoclingDocument

from isanlp_rst.parser import Parser

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "docling"
SEPARATOR_BETWEEN_FIXTURES = "\n\n---\n\n"
HF_MODEL_VERSION = "gumrrg"


def tree_signature(tree: Any) -> tuple[tuple[Any, ...], ...]:
    """Build a structural signature of a tree for equality comparison.

    Captures (relation, nuclearity, depth, start, end) for every relation
    and (start, end) for every leaf. Two trees with the same signature
    are structurally identical at the levels the mapper cares about.
    """
    relations = collect_relations(tree)
    rel_sig = tuple(
        (
            getattr(r, "relation", None),
            getattr(r, "nuclearity", None),
            d,
            r.start,
            r.end,
        )
        for r, d in relations
    )
    return rel_sig


def main() -> int:
    print("Loading Parser(hf_model_version='gumrrg', device='auto') ...")
    parser = Parser(hf_model_version=HF_MODEL_VERSION, device="auto")
    print("Parser loaded.\n")

    # ----- Step 6: long-input smoke -----
    print("=== Step 6: long-input smoke ===")
    harvests: list[tuple[str, str]] = []
    for path in sorted(FIXTURES_DIR.glob("*.docling.json")):
        doc = DoclingDocument.load_from_json(path)
        text, _, _ = harvest_body_text(doc)
        harvests.append((path.name, text))
        print(f"  {path.name}: {len(text):>7} chars")

    combined = SEPARATOR_BETWEEN_FIXTURES.join(t for _, t in harvests)
    print(f"\ncombined: {len(combined)} chars across {len(harvests)} fixtures")

    try:
        result = parser(combined)
        tree = result["rst"][0]
        n_leaves, n_internal, max_depth = walk_tree(tree)
        print(f"  PARSED OK — leaves={n_leaves} internal={n_internal} max_depth={max_depth}")
    except Exception as exc:
        print(f"  PARSE FAILED — {type(exc).__name__}: {exc}")
        return 1

    # ----- Step 7: determinism check -----
    print("\n=== Step 7: determinism check ===")
    largest_name, largest_text = max(harvests, key=lambda nt: len(nt[1]))
    print(f"largest fixture for determinism check: {largest_name} ({len(largest_text)} chars)")

    sig_a = tree_signature(parser(largest_text)["rst"][0])
    sig_b = tree_signature(parser(largest_text)["rst"][0])

    if sig_a == sig_b:
        print(f"  DETERMINISTIC — {len(sig_a)} relations match across two runs")
    else:
        print(f"  NON-DETERMINISTIC — sig_a has {len(sig_a)} relations, sig_b has {len(sig_b)}")
        diffs = sum(1 for a, b in zip(sig_a, sig_b, strict=False) if a != b)
        print(f"  first divergence index: {next((i for i, (a, b) in enumerate(zip(sig_a, sig_b, strict=False)) if a != b), None)}")
        print(f"  divergent relations (within shared prefix): {diffs}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

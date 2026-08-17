"""Phase 0 step 5 — RST quality eyeball on each Docling fixture.

For each fixture:
  1. Harvest body text via iterate_items (body + notes; skip tables).
  2. Run the existing Parser with gumrrg over the harvested text.
  3. Print harvest stats, tree stats, first EDUs, first relations.

The output is for human judgement: does each tree look like meaningful RST or
arbitrary noise? Slide content and VTT transcripts are the high-risk cases —
the parsers were trained on prose.

Run:  pixi run -- python scripts/docling_rst_quality_check.py
"""

from pathlib import Path
from typing import Any

from docling_core.types.doc.document import ContentLayer, DoclingDocument, PictureItem, TextItem

from isanlp_rst.parser import Parser

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "docling"
SEPARATOR = "\n\n"
LAYERS = {ContentLayer.BODY, ContentLayer.NOTES}
HF_MODEL_VERSION = "gumrrg"


def extract_picture_description(picture: PictureItem) -> str | None:
    """Return the picture's VLM description text if any.

    Reads `picture.meta.description.text` — `meta` is a typed `PictureMeta`
    model in docling-core 2.75+; `description` is a `DescriptionMetaField`
    with `.text`, `.created_by`, `.confidence`. Returns None if any layer
    in the chain is missing or empty.
    """
    meta = getattr(picture, "meta", None)
    if meta is None:
        return None
    description = getattr(meta, "description", None)
    if description is None:
        return None
    text = getattr(description, "text", None)
    if isinstance(text, str) and text.strip():
        return text
    return None


def harvest_body_text(doc: DoclingDocument) -> tuple[str, int, int]:
    """Concatenate text from iterate_items in canonical order.

    Includes picture VLM descriptions where present. Tables are skipped.
    Returns (full_text, n_text_items, n_picture_descriptions).
    """
    pieces: list[str] = []
    n_text_items = 0
    n_picture_descriptions = 0
    for item, _ in doc.iterate_items(
        traverse_pictures=True,
        included_content_layers=LAYERS,
    ):
        if isinstance(item, TextItem):
            text = item.text or ""
            if text:
                pieces.append(text)
                n_text_items += 1
        elif isinstance(item, PictureItem):
            desc = extract_picture_description(item)
            if desc:
                pieces.append(desc)
                n_picture_descriptions += 1
    return SEPARATOR.join(pieces), n_text_items, n_picture_descriptions


def walk_tree(node: Any) -> tuple[int, int, int]:
    """Return (n_leaves, n_internal, max_depth) for a DiscourseUnit tree."""

    def rec(n: Any, depth: int) -> tuple[int, int, int]:
        left, right = getattr(n, "left", None), getattr(n, "right", None)
        if left is None and right is None:
            return 1, 0, depth
        ln, li, ld = rec(left, depth + 1) if left is not None else (0, 0, depth)
        rn, ri, rd = rec(right, depth + 1) if right is not None else (0, 0, depth)
        return ln + rn, li + ri + 1, max(ld, rd)

    return rec(node, 0)


def collect_leaves(node: Any) -> list[Any]:
    leaves: list[Any] = []

    def rec(n: Any) -> None:
        left, right = getattr(n, "left", None), getattr(n, "right", None)
        if left is None and right is None:
            leaves.append(n)
            return
        if left is not None:
            rec(left)
        if right is not None:
            rec(right)

    rec(node)
    return leaves


def collect_relations(node: Any) -> list[Any]:
    rels: list[Any] = []

    def rec(n: Any, depth: int) -> None:
        left, right = getattr(n, "left", None), getattr(n, "right", None)
        if left is None and right is None:
            return
        rels.append((n, depth))
        if left is not None:
            rec(left, depth + 1)
        if right is not None:
            rec(right, depth + 1)

    rec(node, 0)
    return rels


def quality_check(parser: Parser, path: Path) -> None:
    print(f"\n=== {path.name} ===")
    doc = DoclingDocument.load_from_json(path)
    harvest_text, n_text_items, n_picture_descs = harvest_body_text(doc)
    n_chars = len(harvest_text)
    print(
        f"harvest: {n_text_items} text items, {n_picture_descs} picture VLM descriptions, "
        f"{n_chars} chars, {harvest_text.count(SEPARATOR)} separator gaps"
    )

    if n_chars == 0:
        print("EMPTY harvest, skipping parse.")
        return

    print(f"first 300 chars: {harvest_text[:300]!r}")
    print(f"last 200 chars:  {harvest_text[-200:]!r}")

    result = parser(harvest_text)
    tree = result["rst"][0]
    n_leaves, n_internal, max_depth = walk_tree(tree)
    print(f"tree: leaves={n_leaves} internal={n_internal} max_depth={max_depth}")

    leaves = collect_leaves(tree)
    print("first 10 EDUs:")
    for i, leaf in enumerate(leaves[:10]):
        edu_text = (leaf.text or "").replace("\n", " ")[:100]
        print(f"  [{i}] ({leaf.start:>5}, {leaf.end:>5}) {edu_text!r}")

    rels = collect_relations(tree)
    print("first 15 relations (pre-order):")
    for i, (rel, depth) in enumerate(rels[:15]):
        relation = getattr(rel, "relation", None)
        nuclearity = getattr(rel, "nuclearity", None)
        print(
            f"  [{i}] d={depth} {relation:<24} {nuclearity:<4} "
            f"span=({rel.start},{rel.end}) ({rel.end - rel.start} chars)"
        )


def main() -> int:
    print("Loading Parser(hf_model_version='gumrrg', device='auto') ...")
    parser = Parser(hf_model_version=HF_MODEL_VERSION, device="auto")
    print("Parser loaded.")

    for path in sorted(FIXTURES_DIR.glob("*.docling.json")):
        try:
            quality_check(parser, path)
        except (KeyError, IndexError, OSError, RuntimeError, ValueError) as exc:
            print(f"\n=== {path.name} === ERROR\n{type(exc).__name__}: {exc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

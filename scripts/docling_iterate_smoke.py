"""Smoke-iterate Docling JSON fixtures via docling-core's canonical walker.

Phase 0 step 2 of the Docling-native RST build plan
(docs/plans/2026-05-15-docling-native-rst-build.md): confirm at runtime what we
inferred from reading the source — canonical iteration order, content-layer
filter behaviour, picture-children traversal, no surprises.

Run:  pixi run -- python scripts/docling_iterate_smoke.py
"""

import sys
from collections import Counter
from pathlib import Path

from docling_core.types.doc.document import ContentLayer, DoclingDocument

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "docling"
PREVIEW_LEN = 50
LAYERS = {ContentLayer.BODY, ContentLayer.FURNITURE, ContentLayer.NOTES}


def smoke_iterate(path: Path) -> None:
    print(f"\n=== {path.name} ===")
    doc = DoclingDocument.load_from_json(path)
    print(f"version={doc.version!r}  mimetype={doc.origin.mimetype if doc.origin else None!r}")

    layer_counter: Counter[str] = Counter()
    label_counter: Counter[str] = Counter()
    items_yielded = 0
    picture_child_items = 0
    first_ten: list[tuple[str, int, str, str, str]] = []

    for item, depth in doc.iterate_items(
        traverse_pictures=True,
        included_content_layers=LAYERS,
    ):
        items_yielded += 1
        self_ref = getattr(item, "self_ref", "<no-self-ref>")
        content_layer = getattr(item, "content_layer", None)
        layer_key = content_layer.value if content_layer is not None else "<none>"
        label = getattr(item, "label", None)
        label_key = label.value if hasattr(label, "value") and label is not None else str(label)
        text = getattr(item, "text", "") or ""
        preview = text[:PREVIEW_LEN].replace("\n", " ")

        layer_counter[layer_key] += 1
        label_counter[label_key] += 1

        parent_ref_obj = getattr(item, "parent", None)
        parent_ref = parent_ref_obj.cref if parent_ref_obj is not None else None
        if parent_ref and parent_ref.startswith("#/pictures/"):
            picture_child_items += 1

        if items_yielded <= 10:
            first_ten.append((self_ref, depth, layer_key, label_key, preview))

    print(f"items_yielded={items_yielded}  picture_child_items={picture_child_items}")
    print(f"by_layer={dict(layer_counter)}")
    print(f"by_label={dict(label_counter)}")
    print("first 10 items:")
    for self_ref, depth, layer_key, label_key, preview in first_ten:
        print(f"  d={depth} {self_ref:<20} layer={layer_key:<10} label={label_key:<18} text={preview!r}")


def main() -> int:
    fixtures = sorted(FIXTURES_DIR.glob("*.docling.json"))
    if not fixtures:
        print(f"no fixtures found in {FIXTURES_DIR}", file=sys.stderr)
        return 1
    for path in fixtures:
        smoke_iterate(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

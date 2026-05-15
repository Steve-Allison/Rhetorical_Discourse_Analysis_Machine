---
name: open-parser-facade-unverified
description: RESOLVED 2026-05-15. Parser facade returns {'rst': [tree]}; tree has character-level absolute offsets via remap_tree_offsets; strictly binary; leaves are EDUs. Verified by reading parser.py, base_predictor.py, dmrst_parser/predictor.py.
metadata:
  type: reference
---

**Status: RESOLVED 2026-05-15.** Verified by reading the source.

**`Parser` facade public surface** (from `isanlp_rst/parser.py`):

- Construct: `Parser(model_dir=None, hf_model_name='tchewik/isanlp_rst_v3', hf_model_version=None, relinventory=None, relinventory_idx=0, cuda_device=-1, family=None, dtype=None)`.
- Resolves a family (`'dmrst'` or `'unirst'`) in priority order: explicit `family` arg → `hf_model_version` lookup → `model_dir` content auto-detection.
- `parser(text)` → `predictor.parse_rst(text)`. Returns `{'rst': [tree]}`.
- `parser.from_edus(edus)` → `predictor.parse_from_edus(edus)`. Returns `{'rst': [tree]}` (same shape).

**Tree shape** (DMRST verified from `isanlp_rst/dmrst_parser/predictor.py:248-316`):

- The single value of `'rst'` is a list containing exactly one root `DiscourseUnit` (from `iinemo/isanlp`).
- After `remap_tree_offsets` (in `base_predictor.py:126-167`), every node carries:
  - `.start: int` — absolute character offset into the input text.
  - `.end: int` — absolute character offset (exclusive).
  - `.text: str` — the substring `input_text[start:end]`.
- Trees are **strictly binary.** Internal nodes have both `.left` and `.right`; leaves have neither. Unary nodes are an error condition and raise (`base_predictor.py:161`).
- Leaves = EDUs (elementary discourse units). Internal nodes = relations (with `.relation`, `.nuclearity` attributes).
- Short inputs (< 3 tokens) get a `DUConverter.dummy_tree` fallback (still binary, just minimal).

**For the Docling-native build:**

- The mapper can recurse the tree, treating leaves as `RstEdu` and internal nodes as `RstRelation`. The binary invariant means flattening is simple.
- Offsets are absolute into the harvested text — no further remapping needed before the overlap rule.
- The Parser facade is called once per document: `result = parser(harvest.full_text); tree = result['rst'][0]`.
- Short-document edge case (< 3 razdel tokens) gets a dummy tree; the mapper must handle it (one EDU, no relations).

**How to apply:**

- In `parse_docling()`, call `parser(harvest.full_text)` and access `result['rst'][0]` for the tree root.
- Recurse via `node.left` and `node.right`; check `node.left is None and node.right is None` for leaf detection.
- Use `node.start`, `node.end` directly for overlap-rule computation against `HarvestSpan`s.

Related: [[decision-one-tree-per-document]], [[verified-docling-core-api]].

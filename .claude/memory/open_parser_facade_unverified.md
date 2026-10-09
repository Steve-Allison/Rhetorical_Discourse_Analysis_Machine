---
name: open-parser-facade-unverified
description: RESOLVED 2026-05-15. Parser facade returns {'rst': [tree]}; tree has character-level absolute offsets via remap_tree_offsets; strictly binary; leaves are EDUs. Verified by reading parser.py, base_predictor.py, dmrst_parser/predictor.py.
metadata:
  type: reference
---

> **Historical note — current status reconciled 2026-09-06.** The observations,
> proposed APIs and open questions below describe the dated work recorded here.
> They are not current installation or implementation instructions. The current
> source boundary is `rdam.ingest`; format-specific `parse_docling`/`parse_doclang`
> APIs and envelopes have been removed. See the [current ingest guide](../../docs/production-source-ingest.md)
> and [documentation guide](../../docs/README.md). Original decisions and measurements
> remain below for traceability; eRST work is suspended.

**Status: RESOLVED 2026-05-15.** Verified by reading the source.

**`Parser` facade public surface** (from `isanlp_rst/parser.py`):

- Construct: `Parser(model_dir=None, hf_model_name='tchewik/isanlp_rst_v3', hf_model_version=None, relinventory=None, relinventory_idx=0, device=None, cuda_device=None, family=None, dtype=None)`. (Updated 2026-06-30: `device=` — `"auto"` default — is now the canonical device knob; `cuda_device:int` is a deprecated warned shim. See [open-device-api](open_device_api.md).)
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

Related: [verified-docling-core-api](verified_docling_core_api.md).

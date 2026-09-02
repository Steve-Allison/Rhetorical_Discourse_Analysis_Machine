# Architecture

The parser is a thin façade over two parallel predictor families. Both families inherit a shared `BasePredictor` that owns tokenisation, batching, offset remapping, MPS-safe init, and mixed-precision dispatch.

## Two parser families, one façade

> **Production status (verified 2026-09-01, `rst/isanlp_rst/parser.py:90-93`)**: the DMRST
> and UniRST families described below are **archived from production**. `Parser` raises
> `ValueError("Legacy … has been archived from production. Use family='modernbert'")`
> for any of their five `hf_model_version` values before loading anything. The sole
> production family is **ModernBERT** (`rst/isanlp_rst/transformer_parser/`), loaded from an
> immutable local release via `Parser.from_model_release(store, release_id,
> family="modernbert")`. The family description below is retained as the record of the
> archived research parsers; the production smoke
> (`tests/integration/test_production_smoke.py`, `pixi run smoke`) exercises only the
> production family, on every available device.

`isanlp_rst.parser.Parser` is a thin dispatcher. It picks one of two predictors based on either `hf_model_version` (HF-pulled) or `family=` / auto-detected (`model_dir=` for local checkpoints):

| Family | Versions | Predictor | Source dir |
|---|---|---|---|
| **DMRST** (monolingual / bilingual) | `rstdt`, `gumrrg`, `rstreebank` | `dmrst_parser.predictor.PredictorDMRST` | `rst/isanlp_rst/dmrst_parser/` |
| **UniRST** (multilingual, 11 languages) | `rrtrrg`, `unirst` | `universal_parser.predictor.PredictorUniRST` | `rst/isanlp_rst/universal_parser/` |

Each family has its own `src/parser/` (network: `parsing_net.py`, `segmenters.py`, `modules.py`, `discriminator.py`, `metrics.py`) and `src/corpus/` (dataset I/O, `.rs3` / `.dis` utilities). The two trees evolved in parallel and share patterns but **not** code — do not refactor one to import from the other without explicit instruction.

## Shared base (`BasePredictor`)

Both predictors inherit `isanlp_rst.base_predictor.BasePredictor`, which centralises:

- razdel / word-level tokenisation and offset bookkeeping
- subword EDU-break recounting (`_recount_spans`)
- offset remapping from tokenised space back to original-text character offsets (`remap_tree_offsets`) — every leaf and internal node ends up with `start` / `end` / `text` fields aligned to the input string
- `_collect_leaf_texts` for round-trip validation against pre-segmented EDUs
- MPS-safe initialisation (orthogonal init routed via CPU on MPS tensors — see [`rst/isanlp_rst/utils/mps_init.py`](../../rst/isanlp_rst/utils/mps_init.py))
- mixed-precision dispatch via `torch.autocast` (`dtype=float32 | bf16 | fp16`)

## Inference flow (DMRST, simplified)

1. `Parser(...)` → `PredictorDMRST.__init__` downloads `best_weights.pt`, `config.json`, `relation_table.txt` from HuggingFace for the requested `hf_model_version` (a git ref/tag on the HF repo), or loads from `model_dir` if supplied.
2. `_load_model()` builds an `AutoTokenizer` + `AutoModel` from the transformer name in `config['model']['transformer']['model_name']` (default: `xlm-roberta-large`), wires it into a `ParsingNet`, and loads the weights.
3. `parse_rst(text)` razdel-tokenises → builds an offset converter → tokenises with the transformer → `model.testing_loss(..., generate_tree=True)` returns spans + EDU breaks + relation labels → `DUConverter` builds an `isanlp.annotation_rst.DiscourseUnit` tree → `remap_tree_offsets` rewrites every node's `start` / `end` to original-text indices.
4. `parse_from_edus(edus)` follows the same path but with `use_pred_segmentation=False`, validating that the produced leaves match the input EDUs character-for-character.

`UniRST` adds a `relinventory` parameter (`Optional[str]`) so a single multilingual model can target a specific corpus's relation set (e.g. `eng.erst.gum`, `rus.rst.rrt`). When `None`, falls back to `relinventory_idx` (default `0`); the dataset at index 0 in the loaded model's `dataset_names` becomes the active inventory. Available inventories: [`UniRST_Metrics.md`](../../UniRST_Metrics.md). Source: `universal_parser/predictor.py:49-110`.

## Device handling

`device=` is the canonical knob (default `"auto"`), resolved by `resolve_device` in [`rst/isanlp_rst/base_predictor.py`](../../rst/isanlp_rst/base_predictor.py):

- `"auto"` (default) → CUDA if present, else MPS on Apple Silicon, else CPU
- `"cpu"` → CPU
- `"mps"` → Apple Silicon Metal backend (`RuntimeError` if unavailable)
- `"cuda"` / `"cuda:N"` → a specific NVIDIA device (`RuntimeError` if no CUDA)
- a `torch.device` → used as-is

The resolved device is stored on the predictor as `self._device` (a `torch.device`). The legacy integer `cuda_device=` is a deprecated shim (`-1` → CPU, `>= 0` → best accelerator) that emits a `DeprecationWarning`; both families still pass the resolved device into the inherited `ParsingNet` under its original `cuda_device=` kwarg name (a Mode-B research-network parameter, not renamed).

PyTorch has no MPS kernel for `torch.linalg.qr` (used by `torch.nn.init.orthogonal_`). The parser routes this via CPU automatically — see [`rst/isanlp_rst/utils/mps_init.py`](../../rst/isanlp_rst/utils/mps_init.py). No manual env-var hacks required.

## Mixed precision (`dtype=`)

Forward passes go through `torch.autocast`. The model runs in `float32`, `float16`, or `bfloat16` without changing trained weights. Default is `float32` on every device.

- **Apple Silicon (~1k-char inputs):** `float32` beats `bfloat16` / `float16` for every published model — claim per `base_predictor.py:470-478` source comment, measured by the maintainer at the time.
- **Large-batch CUDA (Hopper / Ada Tensor Cores):** `bfloat16` is likely faster — same source comment. Measure with `pixi run bench` before pinning.
- **Tree topology + EDU segmentation are bit-equivalent across all three dtypes** for all five published models — **but relation / nuclearity labels are not.** A node's label is an argmax over a per-node distribution; on a near-tied (high-entropy) node, bf16/fp16 can flip the winner with no structural change. Verified 2026-06-27 (numpy 2.5.0, MPS): rrtrrg on `LONG_EN` flips one entropy-0.40 node from `Elaboration`/NS to `Cause-effect`/SN under bf16 while every span stays byte-identical; the other four models show no flip on their test inputs (and rrtrrg itself does not flip under fp16). Assertion source: `tests/test_integration.py` — `test_dmrst_dtype_equivalence_on_mps`, `test_unirst_dtype_equivalence_on_mps`, `test_dtype_equivalence_rstdt`, `test_dtype_equivalence_rstreebank`, `test_dtype_equivalence_rrtrrg`, each comparing fp16/bf16 **topology** (see `_topology`, labels deliberately excluded) against an fp32-CPU baseline. **Suite PASS re-run and verified this session.**

## Visualisation (`isanlp_rst.rstviewer`)

Standalone subpackage ported from `rstviewer`. Public surface lives in the package `__init__.py`:

- `render(rs3_source)` — Jupyter / Colab inline render
- `to_html(rs3_path, html_path)` — write standalone HTML
- `to_png(rs3_path, png_path)` / `to_pdf(rs3_path, pdf_path)` — Playwright / Chromium-driven; both have sync and async paths. They detect a running event loop (e.g. inside Jupyter) and dispatch via a worker thread when needed.
- `DiscourseUnit.to_rs3(filename, encoding='utf8')` (provided by the `iinemo/isanlp` runtime — verified by reading the pinned commit's `src/isanlp/annotation_rst.py:81`) is the bridge from a parsed tree to the visualiser format.

Chromium launch, the offline navigation guard, viewport JS, graph-bbox JS, and PNG whitespace trim live in [`rst/isanlp_rst/rstviewer/_chromium.py`](../../rst/isanlp_rst/rstviewer/_chromium.py). The viewer is on the same ruff / pyright bar as the rest of `rst/isanlp_rst/`.

The async / sync dispatch in `rst/isanlp_rst/__init__.py:_run_coro_sync_result` is load-bearing — don't simplify it without checking notebook compatibility.

## Memory management

`DiscourseUnit` trees keep the substring per node, which dominates memory on large corpora. Pattern:

```python
res["rst"][0].clear_textfields()  # drop .text on every node — keep structure
# … serialise / store …
tree.fill_textfields(full_text)  # repopulate from the original document
```

Calling `.to_rs3()` on a tree with cleared textfields will fail.

## Output shape (`DiscourseUnit`)

Each node carries:

```python
{
 'id': 21,
 'left':  (id=14, start=1,   end=323),  # child node refs
 'right': (id=20, start=324, end=570),
 'relation':    'elaboration',           # rhetorical relation
 'nuclearity':  'NS',                    # nucleus-satellite status (NS / NN / "")
 'entropy':     0.92,                    # entropy of the split
 'start':       1,                       # original-text character offset
 'end':         570,
 'text':        "On Saturday, ... took two wickets."
}
```

Leaves are EDUs; internal nodes are relations. Every node has `start` / `end` in **original-text character coordinates** after `remap_tree_offsets`.

## Native RST tree representation (`DiscourseUnit`)

`DiscourseUnit` is natively provided in [`rst/isanlp_rst/annotation_rst.py`](../../rst/isanlp_rst/annotation_rst.py) in modern Python 3.14 (Mode A, slotted, strictly typed). The legacy `iinemo/isanlp` Git dependency has been retired, and `isanlp_rst` provides transparent `sys.modules` backward-compatibility aliasing for legacy `from isanlp.annotation_rst import DiscourseUnit` imports.

`DiscourseUnit` fields: `id`, `left`, `right`, `text`, `start`, `end`, `orig_text`, `relation`, `nuclearity`, `proba`, `entropy`. Methods: `clear_textfields()` (recursively sets `.text = ''`), `fill_textfields(full_text)` (re-extracts substring per node), `to_rs3(filename, encoding='utf8')` (writes RS3 XML via internal `Exporter`).

## Machine architecture (feature 006)

`specs/006-rhetorical-discourse-machine/` is the authority for everything in this
section. The rules below are the bindings a session needs without reading the feature;
where a rule and the feature disagree, the feature wins. Do not restate its requirements
here as a competing source — cite and follow.

This repository is the first provider of the **Rhetorical Discourse Analysis Machine**: a
permanently analysis-only machine that runs several discourse and argumentation
techniques natively, side by side, without collapsing them into a common formalism.
`isanlp_rst` is its established RST/eRST provider.

### Boundary roster and ownership

One flat top-level boundary per technique, plus `machine/` (aggregate contract),
`ontology/` (vendored Central distribution), and the existing `workbench/`, `tests/`,
`tools/`, `specs/`, `scripts/`, `docs/`, `models/`, `config/`, `dist/`, `graphify-out/`.
Every top-level path has exactly one owner — roster in
[`contracts/architecture-boundaries.md`](../../specs/006-rhetorical-discourse-machine/contracts/architecture-boundaries.md),
verified against the live tree in
[`evidence/boundary-audit.md`](../../specs/006-rhetorical-discourse-machine/evidence/boundary-audit.md).

- **A technique boundary IS the production boundary.** No `production/` subdirectory
  inside one, ever (FR-003).
- **Boundaries appear only on promotion.** A technique's directory is created when that
  technique first promotes a provider (FR-002) — never speculatively. `machine/` and
  `ontology/` exist (feature 007); `rst/` exists because RST is the established provider
  (its adapter `rdam_rst` is there, feature 009; `isanlp_rst` moves in at migration). Any
  other technique boundary directory exists only once its provider is promoted, and
  creating an empty one is a defect.
- **Exactly one `workbench/`.** No second experimentation root, no per-boundary scratch
  area, no "temporary" candidate directory outside it (FR-004).

### No top-level import names

Boundary directories are never importable Python packages. Packages inside them carry
namespaced import names — `isanlp_rst` lives under `rst/` and keeps its import name
unchanged. Top-level import names `rst`, `pdtb`, `sdrt`, `toulmin`, `walton`, `dung`,
`ibis` are never created. (`ibis` is the import name of the PyPI Ibis dataframe library;
the rule removes the whole class of shadowing hazards.)

### Import and distribution

Production code never imports `workbench.*`, directly or transitively, and no wheel or
sdist member contains a `workbench/` path (FR-006). Enforcement lives in
`tools.production_boundary` (feature 007, 2026-09-02): the import walk starts from every
production root — `isanlp_rst` and the boundary packages under `machine/`, `rst/`,
`dung/`, `ibis/` — and the artifact inspector admits only those import roots in a wheel.
Run it as `pixi run -e default production-boundary`; the bare form is ambiguous across
three environments.

### Identity binding

Each boundary declares exactly one canonical framework identity from
`coe:artifact/narrative/analytical_frameworks_taxonomy` in Central_Configs. `coe:`
identifiers are **referenced, never redefined locally**. The binding is identity only —
native relation inventories, role sets, and result payloads stay provider-owned, and
Central's simplified vocabulary profiles never constrain a native contract. A provider
serves a sibling concept through a declared **formalism** with its own identity and
capability state, not through a second boundary: the RST provider binds to `…/rst` and
declares `rst_tree → …/rst`, `erst_graph → …/erst` (the eRST ruling, feature 006
data-model §Formalism). All eight identifiers resolve today:
[`evidence/identity-binding-audit.md`](../../specs/006-rhetorical-discourse-machine/evidence/identity-binding-audit.md).

### Analysis-only scope, and scale

The machine analyses discourse; it never generates or rewrites it. It serves one person
on one local machine (FR-028) — no multi-user, distributed, remote-control-plane, or
enterprise infrastructure without a new explicit requirement.

A shared production abstraction is introduced only when at least two proven production
callers need the same semantic contract with unambiguous ownership (FR-029). The
aggregate contract in `machine/` is the single approved instance.

### Preservation and follow-on order

The RST public surface is preserved across migration byte-for-byte where serialized and
semantically where computed — obligations and the equivalence procedure in
[`contracts/rst-preservation.md`](../../specs/006-rhetorical-discourse-machine/contracts/rst-preservation.md).
Migration is **blocked** while protected workbench runs are live or unreconciled
(FR-026); it starts only from a recorded MigrationSafetyState with the owner's dated
confirmation.

Feature order (FR-025): three features — **aggregate analysis contract** (with ontology
vendoring), **workbench promotion system**, and **RST provider adapter** — must be
specified and cross-artifact consistency checked before repository migration begins.
**Repository migration** is its own fourth decision-closed feature. Providers follow,
strictly on workbench evidence, in the order Dung → IBIS → SDRT → Toulmin → Walton →
PDTB-if-ever, with cross-provider orchestration last. Each technique gets its own
decision-closed Spec Kit feature, authored only once workbench evidence identifies a
credible candidate (FR-024, FR-025). Eleven follow-on features in total.

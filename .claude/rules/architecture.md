# Architecture

The parser is a thin façade over two parallel predictor families. Both families inherit a shared `BasePredictor` that owns tokenisation, batching, offset remapping, MPS-safe init, and mixed-precision dispatch.

## Two parser families, one façade

`isanlp_rst.parser.Parser` is a thin dispatcher. It picks one of two predictors based on either `hf_model_version` (HF-pulled) or `family=` / auto-detected (`model_dir=` for local checkpoints):

| Family | Versions | Predictor | Source dir |
|---|---|---|---|
| **DMRST** (monolingual / bilingual) | `rstdt`, `gumrrg`, `rstreebank` | `dmrst_parser.predictor.PredictorDMRST` | `isanlp_rst/dmrst_parser/` |
| **UniRST** (multilingual, 11 languages) | `rrtrrg`, `unirst` | `universal_parser.predictor.PredictorUniRST` | `isanlp_rst/universal_parser/` |

Each family has its own `src/parser/` (network: `parsing_net.py`, `segmenters.py`, `modules.py`, `discriminator.py`, `metrics.py`) and `src/corpus/` (dataset I/O, `.rs3` / `.dis` utilities). The two trees evolved in parallel and share patterns but **not** code — do not refactor one to import from the other without explicit instruction.

## Shared base (`BasePredictor`)

Both predictors inherit `isanlp_rst.base_predictor.BasePredictor`, which centralises:

- razdel / word-level tokenisation and offset bookkeeping
- subword EDU-break recounting (`_recount_spans`)
- offset remapping from tokenised space back to original-text character offsets (`remap_tree_offsets`) — every leaf and internal node ends up with `start` / `end` / `text` fields aligned to the input string
- `_collect_leaf_texts` for round-trip validation against pre-segmented EDUs
- MPS-safe initialisation (orthogonal init routed via CPU on MPS tensors — see [`isanlp_rst/utils/mps_init.py`](../../isanlp_rst/utils/mps_init.py))
- mixed-precision dispatch via `torch.autocast` (`dtype=float32 | bf16 | fp16`)

## Inference flow (DMRST, simplified)

1. `Parser(...)` → `PredictorDMRST.__init__` downloads `best_weights.pt`, `config.json`, `relation_table.txt` from HuggingFace for the requested `hf_model_version` (a git ref/tag on the HF repo), or loads from `model_dir` if supplied.
2. `_load_model()` builds an `AutoTokenizer` + `AutoModel` from the transformer name in `config['model']['transformer']['model_name']` (default: `xlm-roberta-large`), wires it into a `ParsingNet`, and loads the weights.
3. `parse_rst(text)` razdel-tokenises → builds an offset converter → tokenises with the transformer → `model.testing_loss(..., generate_tree=True)` returns spans + EDU breaks + relation labels → `DUConverter` builds an `isanlp.annotation_rst.DiscourseUnit` tree → `remap_tree_offsets` rewrites every node's `start` / `end` to original-text indices.
4. `parse_from_edus(edus)` follows the same path but with `use_pred_segmentation=False`, validating that the produced leaves match the input EDUs character-for-character.

`UniRST` adds a `relinventory` parameter (`Optional[str]`) so a single multilingual model can target a specific corpus's relation set (e.g. `eng.erst.gum`, `rus.rst.rrt`). When `None`, falls back to `relinventory_idx` (default `0`); the dataset at index 0 in the loaded model's `dataset_names` becomes the active inventory. Available inventories: [`UniRST_Metrics.md`](../../UniRST_Metrics.md). Source: `universal_parser/predictor.py:49-110`.

## Device handling

`device=` is the canonical knob (default `"auto"`), resolved by `resolve_device` in [`isanlp_rst/base_predictor.py`](../../isanlp_rst/base_predictor.py):

- `"auto"` (default) → CUDA if present, else MPS on Apple Silicon, else CPU
- `"cpu"` → CPU
- `"mps"` → Apple Silicon Metal backend (`RuntimeError` if unavailable)
- `"cuda"` / `"cuda:N"` → a specific NVIDIA device (`RuntimeError` if no CUDA)
- a `torch.device` → used as-is

The resolved device is stored on the predictor as `self._device` (a `torch.device`). The legacy integer `cuda_device=` is a deprecated shim (`-1` → CPU, `>= 0` → best accelerator) that emits a `DeprecationWarning`; both families still pass the resolved device into the inherited `ParsingNet` under its original `cuda_device=` kwarg name (a Mode-B research-network parameter, not renamed).

PyTorch has no MPS kernel for `torch.linalg.qr` (used by `torch.nn.init.orthogonal_`). The parser routes this via CPU automatically — see [`isanlp_rst/utils/mps_init.py`](../../isanlp_rst/utils/mps_init.py). No manual env-var hacks required.

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

Chromium launch, the offline navigation guard, viewport JS, graph-bbox JS, and PNG whitespace trim live in [`isanlp_rst/rstviewer/_chromium.py`](../../isanlp_rst/rstviewer/_chromium.py). The viewer is on the same ruff / pyright bar as the rest of `isanlp_rst/`.

The async / sync dispatch in `isanlp_rst/__init__.py:_run_coro_sync_result` is load-bearing — don't simplify it without checking notebook compatibility.

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

## Companion runtime

[`iinemo/isanlp`](https://github.com/iinemo/isanlp) supplies the `DiscourseUnit` class (at `src/isanlp/annotation_rst.py`) and is a hard runtime dependency. Installed via the `git+` URL pinned in `pyproject.toml` (commit `2a102e59f9718acc7fe259dd8d83c66d5da39794`). If `DiscourseUnit` import fails, that pin is the first place to check.

`DiscourseUnit` constructor fields (verified at the pinned commit): `id`, `left`, `right`, `text`, `start`, `end`, `orig_text`, `relation`, `nuclearity`, `proba`, `entropy`. Methods: `clear_textfields()` (recursively sets `.text = ''`), `fill_textfields(full_text)` (re-extracts substring per node), `to_rs3(filename, encoding='utf8')` (writes RS3 XML via internal `Exporter`).

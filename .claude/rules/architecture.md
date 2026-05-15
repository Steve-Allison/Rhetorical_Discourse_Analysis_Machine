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
3. `parse_rst(text)` razdel-tokenises → builds an offset converter → tokenises with the transformer → `model.testing_loss(..., generate_tree=True)` returns spans + EDU breaks + relation labels → `DUConverter` builds an `isanlp.DiscourseUnit` tree → `remap_tree_offsets` rewrites every node's `start` / `end` to original-text indices.
4. `parse_from_edus(edus)` follows the same path but with `use_pred_segmentation=False`, validating that the produced leaves match the input EDUs character-for-character.

`UniRST` adds a `relinventory` parameter so a single multilingual model can target a specific corpus's relation set (e.g. `eng.erst.gum`, `rus.rst.rrt`). Default inventory for `unirst` is `eng.rst.rstdt`. Available inventories: [`UniRST_Metrics.md`](../../UniRST_Metrics.md).

## Device handling

`cuda_device=N` (any non-negative integer) auto-selects the best available GPU backend:

- NVIDIA CUDA host → `cuda:N`
- Apple Silicon (no CUDA) → `mps` (the integer is ignored; MPS exposes a single device)
- No GPU available → `RuntimeError` (use `cuda_device=-1` for CPU)

PyTorch has no MPS kernel for `torch.linalg.qr` (used by `torch.nn.init.orthogonal_`). The parser routes this via CPU automatically — see [`isanlp_rst/utils/mps_init.py`](../../isanlp_rst/utils/mps_init.py). No manual env-var hacks required.

## Mixed precision (`dtype=`)

Forward passes go through `torch.autocast`. The model runs in `float32`, `float16`, or `bfloat16` without changing trained weights. Default is `float32` on every device.

- **Apple Silicon (~1k-char inputs):** `float32` beats `bfloat16` / `float16` for every published model. Autocast dispatch overhead dominates the matmul speedup at this scale.
- **Large-batch CUDA (Hopper / Ada Tensor Cores):** `bfloat16` is likely faster. Measure with `pixi run bench` before pinning.
- **Tree structure is bit-equivalent across all three dtypes** for all five published models — see [`tests/test_integration.py`](../../tests/test_integration.py) for the equivalence suite.

## Visualisation (`isanlp_rst.rstviewer`)

Standalone subpackage ported from `rstviewer`. Public surface lives in the package `__init__.py`:

- `render(rs3_source)` — Jupyter / Colab inline render
- `to_html(rs3_path, html_path)` — write standalone HTML
- `to_png(rs3_path, png_path)` / `to_pdf(rs3_path, pdf_path)` — Playwright / Chromium-driven; both have sync and async paths. They detect a running event loop (e.g. inside Jupyter) and dispatch via a worker thread when needed.
- `DiscourseUnit.to_rs3('file.rs3')` (provided by the `iinemo/isanlp` runtime) is the bridge from a parsed tree to the visualiser format.

The async / sync dispatch in `isanlp_rst/__init__.py:_run_coro_sync_result` is load-bearing — don't simplify it without checking notebook compatibility.

## Memory management

`DiscourseUnit` trees keep the substring per node, which dominates memory on large corpora. Pattern:

```python
res['rst'][0].clear_textfields()      # drop .text on every node — keep structure
# … pickle / store …
tree.fill_textfields(full_text)       # repopulate from the original document
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

[`iinemo/isanlp`](https://github.com/iinemo/isanlp) supplies the `DiscourseUnit` class and is a hard runtime dependency. Installed via the `git+` URL pinned in `pyproject.toml`. If `DiscourseUnit` import fails, that pin is the first place to check.

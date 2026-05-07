# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Third-party RST (Rhetorical Structure Theory) parser library by Elena Chistova (`tchewik/isanlp_rst`, PyPI: `isanlp_rst`, currently v3.2.0). Predicts discourse trees from raw text or pre-segmented EDUs, across 11 languages via the `unirst` multilingual model. Models are pulled from Hugging Face (`tchewik/isanlp_rst_v3`) at runtime — there are no model weights in the repo.

This is an **external library**, not Steve's own code. Treat it as a vendored dependency: changes should stay surgical and upstream-aware. The companion runtime `isanlp` (`iinemo/isanlp`) is a separate GitHub package that must be installed for `DiscourseUnit` to be available.

## Common commands

There is no test suite, no lint config, no `pixi.toml`, no Makefile. The project ships as a `pip`-installable package via `pyproject.toml` (setuptools build).

```bash
# Install for development (raw venv / pip — this repo is not pixi-managed)
pip install git+https://github.com/iinemo/isanlp.git    # required runtime dep
pip install -e .                                         # this package
playwright install chromium                              # only needed for to_png / to_pdf

# Smoke test — parse a sentence with each model family
python -c "from isanlp_rst.parser import Parser; p = Parser(hf_model_name='tchewik/isanlp_rst_v3', hf_model_version='gumrrg', cuda_device=-1); print(p('Hello. World.')['rst'][0])"

# Train / evaluate (research scripts; require corpora not in this repo)
python isanlp_rst/dmrst_parser/multiple_runs.py --corpus "$CORPUS" --lang "$LANG" --model_type "$TYPE" train
python isanlp_rst/dmrst_parser/multiple_runs.py --corpus "$CORPUS" --lang "$LANG" --model_type "$TYPE" evaluate
python isanlp_rst/universal_parser/multiple_runs.py --corpus "$CORPUS" --lang "$LANG" --model_type "$TYPE" train_mixed --mixed 100
```

GPU: pass `cuda_device=N` to `Parser(...)`; `-1` selects CPU.

## Architecture

### Two parser families, one façade

`isanlp_rst.parser.Parser` is a thin dispatcher. It picks one of two predictors based on `hf_model_version`:

| Family | Versions | Predictor | Source dir |
|---|---|---|---|
| **DMRST** (monolingual / bilingual) | `rstdt`, `gumrrg`, `rstreebank` | `dmrst_parser.predictor.PredictorDMRST` | `isanlp_rst/dmrst_parser/` |
| **UniRST** (multilingual) | `rrtrrg`, `unirst` | `universal_parser.predictor.PredictorUniRST` | `isanlp_rst/universal_parser/` |

Both predictors inherit `isanlp_rst.base_predictor.BasePredictor`, which centralises:

- razdel/word-level tokenisation and offset bookkeeping
- subword EDU-break recounting (`_recount_spans`)
- offset remapping from tokenised space back to original-text character offsets (`remap_tree_offsets`) — every leaf and internal node ends up with `start`/`end`/`text` fields aligned to the input string
- `_collect_leaf_texts` for round-trip validation against pre-segmented EDUs

Each model family has its own `src/parser/` (network — `parsing_net.py`, `segmenters.py`, `modules.py`, `discriminator.py`, `metrics.py`) and `src/corpus/` (dataset I/O, `.rs3`/`.dis` utilities). The two trees evolved in parallel and share patterns but **not** code; do not refactor one to import from the other without explicit instruction.

### Inference flow (DMRST, simplified)

1. `Parser(...)` → `PredictorDMRST.__init__` downloads `best_weights.pt`, `config.json`, `relation_table.txt` from HF for the requested `hf_model_version` (a git revision/tag of the HF repo).
2. `_load_model()` builds an `AutoTokenizer` + `AutoModel` from the transformer name in `config['model']['transformer']['model_name']` (default: `xlm-roberta-large`), wires it into a `ParsingNet`, and loads the weights.
3. `parse_rst(text)` razdel-tokenises → builds an offset converter → tokenises with the transformer → `model.testing_loss(..., generate_tree=True)` returns spans + EDU breaks + relation labels → `DUConverter` builds an `isanlp.DiscourseUnit` tree → `remap_tree_offsets` rewrites every node's `start`/`end` to original-text indices.
4. `parse_from_edus(edus)` follows the same path but with `use_pred_segmentation=False`, validating that the produced leaves match the input EDUs character-for-character.

`UniRST` adds a `relinventory` parameter so a single multilingual model can target a specific corpus's relation set (e.g. `eng.erst.gum`, `rus.rst.rrt`). Default inventory for `unirst` is `eng.rst.rstdt`. The available inventories are listed in [UniRST_Metrics.md](UniRST_Metrics.md).

### Visualisation (`isanlp_rst.rstviewer`)

Standalone subpackage ported from `rstviewer`. Public surface lives in the package `__init__.py`:

- `render(rs3_source)` — Jupyter/Colab inline render
- `to_html(rs3_path, html_path)` — write standalone HTML
- `to_png(rs3_path, png_path)` / `to_pdf(rs3_path, pdf_path)` — Playwright/Chromium-driven; both have sync and async paths and detect a running event loop (e.g. inside Jupyter), then dispatch via a worker thread when needed
- `DiscourseUnit.to_rs3('file.rs3')` (provided by upstream `isanlp`) is the bridge from a parsed tree to the visualiser format

The async/sync dispatch in `__init__.py:_run_coro_sync_result` is load-bearing — don't simplify it without checking notebook compatibility.

### Memory management

`DiscourseUnit` trees keep the substring per node, which dominates memory on large corpora. Pattern:

```python
res['rst'][0].clear_textfields()      # drop .text on every node — keep structure
# … pickle / store …
tree.fill_textfields(full_text)       # repopulate from the original document
```

Calling `.to_rs3()` on a tree with cleared textfields will fail.

## Conventions and gotchas

- **No tests.** Don't claim "tests pass" — verification is by running the parser end-to-end on a known input. Use a tiny string and inspect `res['rst'][0]`'s `relation`, `nuclearity`, `start`, `end`, `text` against expectations.
- **Python 3.10+** in CI badge, but `pyproject.toml` says `requires-python = ">=3.8"`. Trust `pyproject.toml`.
- **`numpy==1.26.4`** is pinned. Don't bump it without checking transformer compatibility.
- **HF revisions are the version channel.** `hf_model_version` is mapped to a git ref on the HF repo — switching versions re-downloads weights/config/relation table.
- **`<P>` token** is added to the tokenizer at load time (`tokenizer.add_tokens(['<P>'])`) and the transformer embeddings are resized accordingly. Anything that re-instantiates the tokenizer must replicate this.
- **`tokenizer.model_max_length = 1e9`** is intentional — the parser uses sliding-window encoding and suppresses HF's max-length warning this way. Don't "fix" it.
- **Razdel** does the initial word-level tokenisation regardless of language. The transformer subword tokenisation runs on top.
- **Adjacent-code editing.** Match the existing code style (no type hints in the older modules, occasional `str2bool` helpers duplicated between `predictor.py` and `base_predictor.py`). Don't refactor for taste.

## Files worth knowing

- [isanlp_rst/parser.py](isanlp_rst/parser.py) — public entry point, dispatches to the two predictor families
- [isanlp_rst/base_predictor.py](isanlp_rst/base_predictor.py) — shared tokenisation, batching, offset remapping
- [isanlp_rst/dmrst_parser/predictor.py](isanlp_rst/dmrst_parser/predictor.py) — DMRST inference path (most-edited file historically)
- [isanlp_rst/universal_parser/predictor.py](isanlp_rst/universal_parser/predictor.py) — UniRST inference path with `relinventory` selection
- [isanlp_rst/**init**.py](isanlp_rst/__init__.py) — viewer convenience helpers (`render`, `to_html`, `to_png`, `to_pdf`)
- [isanlp_rst/utils/du_converter.py](isanlp_rst/utils/du_converter.py) — model-output → `isanlp.DiscourseUnit` tree
- [README.md](README.md) — user-facing usage and performance tables
- [UniRST_Metrics.md](UniRST_Metrics.md) — full per-corpus metrics for the multilingual model

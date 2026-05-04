# Fork Notes — Story_Analyser maintenance fork

**Fork of:** [tchewik/isanlp_rst](https://github.com/tchewik/isanlp_rst)
**Maintained by:** Steve Allison
**Reason:** Upstream `pyproject.toml` pins `numpy==1.26.4`, blocking installation in projects that have moved to numpy 2.x. The fork additionally addresses a numpy 2.x regression on the training path, a `torch.load` security warning, missing Apple Silicon (MPS) device support, missing HF Hub controls (cache / offline / token), missing batch-parsing API, missing parse-result cache hook, and several quality-of-life fixes (logging hygiene, deprecated PyTorch API).
**Forked at upstream commit:** `249feb6` (v3.2.0 merge)

## Changes vs upstream `v3.2.0`

### Dependency / packaging fixes (`pyproject.toml`)

- **`numpy==1.26.4` → `numpy>=1.26,<3.0`.** Inspection of all 21 numpy call sites in `isanlp_rst/` showed usage limited to APIs stable across numpy 1.26 and 2.x (`np.unique`, `np.array(..., dtype=object)`, `np.mean`). Verified with end-to-end parse on numpy 2.2.6.
- **Added missing runtime deps:** `huggingface_hub`, `tqdm`, `networkx`, `pillow`. All four are imported at module load via the predictor's import chain but were missing from upstream's dependency list.
- **`asyncio` removed.** Stdlib module — listing it as a dependency is a documentation error (no-op for installers).
- **`requires-python` raised from `>=3.8` to `>=3.10`.** Reflects the actual PyTorch / transformers floor in 2026.
- **`pytorch-lightning` moved to optional `[training]` extra.** Used only by `*/multiple_runs.py` training launchers, never on the inference path.
- **New `[test]` extra: `pytest>=7`.** Lets contributors run the new test suite via `pip install '.[test]'`.

**Note on optional extras:** an earlier attempt moved `playwright`, `lxml`, `fire`, `jsonnet` into optional `[viewer]` and `[training]` extras. Reverted because these packages are imported at module load via the predictor's import chain (`data_manager.py` imports `fire`, `corpus/utils_rs3.py` imports `lxml`, `src/config_reader.py` imports `jsonnet`, `rstviewer/main.py` imports `playwright`). Splitting them into extras would require lazy-import patches across 5+ upstream modules. The hard-dep approach is the smaller patch surface.

### Bug fixes (cross-applicable to upstream)

- **Removed dead `from PIL import Image`** in two files where `Image` is never referenced (verified zero `Image.` call sites):
  - `isanlp_rst/dmrst_parser/src/parser/parsing_net.py:5`
  - `isanlp_rst/universal_parser/src/parser/parsing_net.py:5`

- **`np.string_` → `np.bytes_`** in `isanlp_rst/dmrst_parser/src/parser/training_manager.py:36`. `np.string_` was removed in numpy 2.0; `string_` was an alias for `bytes_` in numpy 1.x — behaviour-preserving. The matching line in `universal_parser/src/parser/training_manager.py:36` was already commented out upstream. Affects only the *training* path; without this fix, retraining on numpy 2.x crashes.

- **`torch.load(..., weights_only=True)`** in both predictors (`dmrst_parser/predictor.py:91`, `universal_parser/predictor.py:321`). Mitigates the arbitrary-code-execution vector that motivated PyTorch 2.6's default flip. State dicts from huggingface_hub are tensor-only, so this is a safe-default upgrade with no behavioural change. Eliminates the `FutureWarning` that otherwise fires on every parse in PyTorch 2.4+.

- **Removed deprecated `verbose=True` from `ReduceLROnPlateau`** in both training managers. The argument was removed in PyTorch 2.x; the scheduler's native logging hook covers the same use case. Affects the training path only.

### Quality of life (cross-applicable to upstream)

- **Replaced `print()` with structured `logging`** in corpus utilities:
  - `isanlp_rst/{universal,dmrst}_parser/src/corpus/data.py` — 5 prints each → `logger.debug`/`logger.info`
  - `isanlp_rst/{universal,dmrst}_parser/src/corpus/utils_dis_thiago.py` — 7 prints each → conditional `logger.info`/`logger.debug` (preserved the `verbose` flag)
  - `printLabels` migrated to logger.info so callers piping the output get clean stdout

  Output now respects host log configuration and goes to stderr instead of stdout, which matters for callers that consume parser output via subprocess.

### New API surface (fork-only — Story_Analyser additions)

These add API rather than fix bugs; they live only in the fork. The upstream maintainer may want to review them separately.

#### Device abstraction with Apple Silicon (MPS) support

- **New module `isanlp_rst/utils/device.py`** exposing `resolve_device(spec)` and the `DeviceSpec` type alias.
- **New keyword-only `device` parameter** on `Parser.__init__` and both predictor `__init__`s. Accepts:
  - `None` / `'auto'` — picks the best available accelerator (CUDA → MPS → CPU)
  - `'cpu'` / `'cuda'` / `'cuda:N'` / `'mps'` — explicit device strings
  - `int` — legacy isanlp_rst convention (`-1` = CPU, `N` = `cuda:N`)
  - `torch.device` — passed through unchanged
- **MPS edge case handled:** `torch.linalg.qr` (used in LSTM orthogonal init) is not yet implemented for MPS in PyTorch 2.11 (see [pytorch#141287](https://github.com/pytorch/pytorch/issues/141287)). The auto-selector probes the op at resolve time and falls back to CPU silently with a clear warning if it fails. The `PYTORCH_ENABLE_MPS_FALLBACK=1` env var (set in the shell *before* Python starts) bypasses the probe and runs inference on MPS with CPU fallback only for the missing init op.
- **Backward compatibility:** the legacy `cuda_device: int` parameter still works exactly as before. The new `device` parameter takes precedence when supplied.

#### HF Hub control: cache / offline / auth

- **New keyword-only parameters** `cache_dir`, `local_files_only`, `token` on `Parser.__init__` and both predictor `__init__`s. All four `hf_hub_download` call sites now honour these settings.
- **`cache_dir`** — override the HF Hub cache directory (defaults to `~/.cache/huggingface`).
- **`local_files_only=True`** — refuse to reach out to HF Hub; fail if files aren't already cached. Useful for airgapped / reproducible runs.
- **`token`** — HF Hub auth token. Skips the "unauthenticated requests" warning and avoids the lower rate-limit ceiling.

#### Pluggable parse cache

- **New module `isanlp_rst/utils/cache.py`** exposing the `ParseCache` Protocol (runtime-checkable).
- **New keyword-only `cache` parameter** on `Parser.__init__`. Any object with `get(text) -> result | None` and `put(text, result) -> None` methods works.
- The parser checks the cache on every `__call__` and stores results on miss. Cache `put` failures are caught and logged — they never break the parse.

#### Batch parsing

- **New `Parser.parse_batch(texts, *, show_progress=False, skip_empty=True)`** — parse multiple documents with optional tqdm progress bar. Cache-aware (delegates to `__call__`). Empty / whitespace-only inputs return `None` at their position in the result list when `skip_empty=True`.
- Implementation today is a sequential loop. The API exists so a future move to true batched inference is a drop-in replacement for callers.

#### Slide / section-grain parsing

- **`Parser.parse_segments(segments, join_with=" ")`** — convenience method for parsing pre-segmented documents (slides in a deck, sections in a Docling/Markdown document, emails in a thread, paragraphs in a research paper). Joins segments with the supplied separator and dispatches to `__call__`. Story_Analyser uses this for slide decks; the same method is suitable for any structurally pre-divided input.

#### JSON tree serialiser

- **New module `isanlp_rst/utils/serialization.py`** — `tree_to_dict()` and `tree_from_dict()` for JSON-safe round-trip of `DiscourseUnit` trees. Preserves `id`, `relation`, `nuclearity`, `start`, `end`, `text`, `proba` plus children (`left`, `right`).
- `tree_from_dict` falls back to returning the dict unchanged when `isanlp` isn't importable, so dict-shaped consumers still work.

#### Type stubs

- **`isanlp_rst/py.typed`** (PEP 561 marker, empty file) plus type hints on every public method of `Parser`. Pyright/mypy now resolve types through the parser API instead of seeing `Any`.
- The Predictor imports inside `Parser.__init__` are lazy — constructing a DMRST parser no longer requires the UniRST predictor to import successfully (and vice versa).

### Test suite (fork-only)

- **40 new pytest tests across 4 modules:**
  - `tests/test_device.py` — 14 tests covering `resolve_device` (legacy ints, modern strings, auto-selection, MPS/CUDA availability gating, `torch.device` pass-through, type errors)
  - `tests/test_cache_protocol.py` — 5 tests covering `ParseCache` protocol membership and round-trip
  - `tests/test_serialization.py` — 8 tests covering `tree_to_dict`/`tree_from_dict` (None handling, recursive children, JSON serialisability, round-trip, isanlp-unavailable fallback)
  - `tests/test_parser_construction.py` — 13 tests covering Parser version validation, input validation in `parse_segments`/`parse_batch`/`__call__`, and cache-hook behaviour (hit, miss, write-failure)
- Tests do **not** require the model weights — they stub the predictor where needed. Run with `pip install '.[test]' && pytest tests/`.

### `isanlp` (parent library) — upstream documentation issue carried forward

The `isanlp` package is imported at runtime (`from isanlp.annotation import Token` in `universal_parser/predictor.py`) but is not declared as a dependency upstream. It is also not on PyPI. Install separately:

```bash
pip install git+https://github.com/iinemo/isanlp.git
```

Unchanged from upstream behaviour but documented here because it is the most common installation friction point for new users.

## Verification (2026-05-04)

All checks pass against an isolated Python 3.12 venv with numpy 2.2.6 on Apple Silicon (M-series).

1. **Install:** `pip install -e '.[test]'` succeeded; no version conflicts.
2. **Test suite:** `pytest tests/` — 40 passed, 2 skipped (skips are gated on CUDA / isanlp availability).
3. **End-to-end parse on CPU:** `Parser(hf_model_version='rstdt', device='cpu')` returned correct tree (relation=Elaboration, nuclearity=NS).
4. **End-to-end parse on MPS** (with `PYTORCH_ENABLE_MPS_FALLBACK=1` exported before Python launch): `Parser(device='auto')` resolved to MPS, model constructed successfully (LSTM init's QR op fell back to CPU, everything else ran on MPS), inference returned correct tree.
5. **MPS auto-fallback** (without env var): probe correctly detected the missing op and resolved to CPU with a clear warning naming the env var to set.
6. **`parse_segments`:** 3-slide deck joined with `\n\n` → single tree spanning all three.
7. **`parse_batch`:** 4-element list with one empty entry → 4-element output list with `None` at the empty position.
8. **Cache hook:** 3 calls with the same text → 1 miss + 2 hits.
9. **`tree_to_dict` round-trip:** parsed tree → JSON → restored tree, `relation` and `nuclearity` preserved.
10. **`torch.load(weights_only=True)`:** `FutureWarning` no longer fires; checkpoint loads identically.

## Rebase plan

Upstream releases roughly twice a year. To incorporate upstream changes:

```bash
git remote add upstream https://github.com/tchewik/isanlp_rst.git
git fetch upstream
git checkout story-analyser-numpy2-repin
git rebase upstream/master
# Re-apply pyproject.toml changes if upstream re-pinned numpy / restored
# the removed PIL imports / removed the missing-deps additions.
```

**Open question on every rebase:** has upstream merged the open PR ([tchewik/isanlp_rst#13](https://github.com/tchewik/isanlp_rst/pull/13))? If yes, the dependency-fix portion of this fork is no longer needed and the fork shrinks to the Story_Analyser-specific additions only.

## Out of scope

- No changes to parser model architecture, weights, or output schema.
- No re-training, no model weight changes.
- No language-support changes.
- No new algorithmic bug fixes beyond the unused-import removals.
- No CI / pre-commit / lint config (upstream has none; adding it would be its own PR).

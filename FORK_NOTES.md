# Fork Notes — Story_Analyser maintenance fork

**Fork of:** [tchewik/isanlp_rst](https://github.com/tchewik/isanlp_rst)
**Maintained by:** Steve Allison
**Reason:** Upstream `pyproject.toml` pins `numpy==1.26.4`, blocking installation in projects that have moved to `numpy` 2.x. Also missing several runtime-imported packages from the declared dependency list.
**Forked at upstream commit:** `249feb6` (v3.2.0 merge)

## Changes vs upstream `v3.2.0`

### `pyproject.toml`

- **`numpy==1.26.4` → `numpy>=1.26,<3.0`.** Inspection of all 21 numpy call sites in `isanlp_rst/` shows usage limited to stable APIs (`np.unique`, `np.array(..., dtype=object)`, `np.mean`). No use of removed numpy 1.x aliases (`np.float`, `np.int`, `np.bool`, `np.string_`). Verified by full end-to-end parse against `numpy 2.2.6` — see *Verification* below.
- **Added missing runtime deps:** `huggingface_hub`, `tqdm`, `networkx`, `pillow`. All four are imported at module load via the predictor's import chain but were missing from upstream's dependency list.
- **`asyncio` removed.** Stdlib module — listing it as a dependency is a documentation error (no-op for installers).
- **`requires-python` raised from `>=3.8` to `>=3.10`.** Reflects the actual PyTorch / transformers floor in 2026.
- **`pytorch-lightning` moved to optional `[training]` extra.** Only used by `*/multiple_runs.py` training launchers, never on the inference path.

**Note on optional extras:** an earlier attempt moved `playwright`, `lxml`, `fire`, `jsonnet` into optional `[viewer]` and `[training]` extras. Reverted — these packages are imported at module load via the predictor's import chain (`data_manager.py` imports `fire`, `corpus/utils_rs3.py` imports `lxml`, `src/config_reader.py` imports `jsonnet`, `rstviewer/main.py` imports `playwright`). Splitting them into extras would require either lazy-import patches across 5+ upstream modules or breaking the package on import. The hard-dep approach is the smaller patch surface.

### Source code (surgical fixes)

- **Removed dead `from PIL import Image`** in two files where `Image` is never referenced:
  - `isanlp_rst/dmrst_parser/src/parser/parsing_net.py:5`
  - `isanlp_rst/universal_parser/src/parser/parsing_net.py:5`

  Verified with `grep "Image\."`: zero call sites in either file. These are upstream dead imports — likely IDE auto-added — that became a problem only when a downstream tool tried to load the predictor without `pillow` installed.

- **`np.string_` → `np.bytes_`** in `isanlp_rst/dmrst_parser/src/parser/training_manager.py:36`. `np.string_` was removed in numpy 2.0; `string_` was an alias for `bytes_` in numpy 1.x, so this is behaviour-preserving. (The matching line in `universal_parser/src/parser/training_manager.py:36` was already commented out upstream.) This affects only the *training* path — inference doesn't load `training_manager` — so missed in the original numpy-usage audit. Without this fix, retraining on numpy 2.x crashes.

### Story_Analyser-specific additions (not in upstream PR)

These add API surface rather than fix bugs, so they live only in the fork. The upstream maintainer may want to review them separately later.

- **`isanlp_rst/py.typed`** (PEP 561 marker, empty file) plus type hints on `Parser.__init__`, `Parser.__call__`, `Parser.from_edus`, and the new `Parser.parse_segments`. Pyright/mypy now resolve types through the parser API instead of seeing `Any`. The lazy `PredictorDMRST` / `PredictorUniRST` imports inside `__init__` mean the package no longer requires both predictor families to import successfully just to construct one.
- **`Parser.parse_segments(segments, join_with=" ")`** — convenience method for parsing pre-segmented documents (slides, sections, emails) without losing the caller's segment intent. Implementation joins with `join_with` and dispatches to `__call__`; future revisions could push hard segment boundaries down to the parser.
- **`isanlp_rst/utils/serialization.py`** — `tree_to_dict()` and `tree_from_dict()` for JSON-safe round-trip of `DiscourseUnit` trees. Lets downstream consumers cache/transmit trees without holding the live object graph. Story_Analyser previously had a private copy of this in `nlp/rst_utils.py::serialize_rst_tree`; the project can now drop that and import from the fork.

### `isanlp` (parent library) — upstream documentation issue carried forward

The `isanlp` package is imported at runtime (`from isanlp.annotation import Token` in `universal_parser/predictor.py`) but is not declared as a dependency upstream. It is also not on PyPI. Install separately:

```bash
pip install git+https://github.com/iinemo/isanlp.git
```

Unchanged from upstream behaviour but documented here because it is the most common installation friction point for new users.

## Verification (2026-05-04)

1. **Install:** `pip install -e .` succeeded against an isolated venv backed by Python 3.12 + numpy 2.2.6. No version conflicts.
2. **Import:** `from isanlp_rst.parser import Parser` succeeded; `py.typed` shipped in the wheel.
3. **End-to-end parse:** Loaded `tchewik/isanlp_rst_v3` model with `hf_model_version='rstdt'`, parsed a 32-word business text. Root DiscourseUnit returned with attributes:
   - `id, left, right, relation, nuclearity, start, end, text, proba` (matches `story_analyser/nlp/rst_utils.py::serialize_rst_tree` field expectations exactly)
   - Bonus attributes returned: `entropy`, `_exporter`
   - Root: `relation='Elaboration'`, `nuclearity='NS'`, span 0..212, both children present.
4. **`parse_segments`:** Parsed a 3-slide deck with `join_with="\n\n"`. Root: `Elaboration`/`NS`, span 0..117 covering all three concatenated slides.
5. **`tree_to_dict` round-trip:** Serialised the parsed tree to JSON (795 chars) and round-tripped back through `tree_from_dict`; `relation` and `nuclearity` preserved at root.
6. **`np.string_ → np.bytes_`:** `import isanlp_rst.dmrst_parser.src.parser.training_manager` succeeds on numpy 2.2.6 (would have crashed before this patch).

## Rebase plan

Upstream releases roughly twice a year. To incorporate upstream changes:

```bash
git remote add upstream https://github.com/tchewik/isanlp_rst.git
git fetch upstream
git checkout main
git rebase upstream/main
# Re-apply pyproject.toml changes if upstream re-pinned numpy or restored
# the removed PIL imports.
```

**Open question on every rebase:** did upstream relax `numpy==1.26.4`? If yes, this fork is no longer needed and Story_Analyser can switch back to upstream PyPI.

## Out of scope

- No changes to parser internals, model loading, or output schema.
- No re-training, no model weight changes.
- No language-support changes.
- No algorithmic bug fixes — purely a packaging + dead-import-removal fork.

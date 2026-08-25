# Production package and offline workbench boundary

## The rule

`isanlp_rst` owns only capabilities required while another project performs RST/eRST analysis. `offline_workbench` owns everything that creates, fits, calibrates, evaluates, benchmarks, or promotes those runtime capabilities. `research_harness` is repository-only research code operating inside the same offline environment.

The distinction is purpose, not provenance: old research code that is required for inference remains production and must meet the production standard. Conversely, high-quality evaluation or training code remains offline because a consuming project does not need it to analyse a document.

Feature 002 source ingest is independent of this split. The canonical `isanlp_rst.ingest` service processes real-world text, Markdown, Docling JSON, DocLang XML, and DocLang archives into production RST analysis and therefore remains production. Corpus conversion for training/evaluation is offline.

## Install and run

Production checkout:

```bash
pixi install -e production
pixi run -e production production-smoke
pixi run -e production production-artifacts
pixi run -e production production-clean-install
```

Production package for another project:

```bash
pip install ./dist/isanlp_rst-4.0.0-py3-none-any.whl
# Add format-native ingest when needed:
pip install "./dist/isanlp_rst-4.0.0-py3-none-any.whl[formats]"
```

Load a promoted local parser without permitting a loose candidate path:

```python
from isanlp_rst import Parser

parser = Parser.from_model_release(
    "/Users/steveallison/.cache/isanlp_rst/model-releases",
    "gumrrg-eb1d5745f3a1",
    family="dmrst",
    device="auto",
)
```

Offline repository work:

```bash
pixi install -e offline
pixi run -e offline offline-smoke
pixi run -e offline test
```

## Ownership map

| Capability | Canonical owner | Published |
|---|---|---:|
| Raw text and predefined-EDU inference | `isanlp_rst.parser` and runtime predictors | yes |
| Typed request/result contracts and serialization | `isanlp_rst.contracts` | yes |
| Real-source inventory, preparation, analysis, receipts, and cache identity | `isanlp_rst.ingest` via `formats` | optional production extra |
| DocLang/Markdown source decoding helpers | private `isanlp_rst.doclang` / `.markdown` modules called only by `isanlp_rst.ingest` | optional implementation detail |
| RS4/eRST reading, conversion, decoding, validation, and loading | `isanlp_rst.erst` | yes |
| Released-model manifest validation/loading | `isanlp_rst.model_loading` | yes |
| Corpus conversion and relation-inventory derivation | `offline_workbench.corpus` | no |
| Segmenter, parser, and eRST fitting | `offline_workbench.training` | no |
| Parseval, calibration, and eRST evaluation | `offline_workbench.evaluation` | no |
| Bundle creation and model promotion | `offline_workbench.promotion` | no |
| Experimental comparison systems | `research_harness` in the root offline environment | no |
| Tests, scripts, specs, corpora, caches, and evidence | repository-only | no |

## Import migrations

These are deliberate offline migrations, not production compatibility aliases:

| Previous path | Canonical offline path |
|---|---|
| `isanlp_rst.eval.*` | `offline_workbench.evaluation.rst.*` |
| `isanlp_rst.segmentation.dataset` | `offline_workbench.training.segmentation.dataset` |
| `isanlp_rst.erst.dataset.GUMSecondaryEdgeDataset` | `offline_workbench.training.erst.dataset.GUMSecondaryEdgeDataset` |
| `isanlp_rst.erst.corpus` | `offline_workbench.corpus.erst.corpus` |
| `isanlp_rst.erst.sampling` | `offline_workbench.corpus.erst.sampling` |
| parser-family `data_manager` and `src.corpus` modules | `offline_workbench.corpus.dmrst` / `.unirst` |
| parser-family training managers, config readers, and run orchestration | `offline_workbench.training.parsers` |
| `isanlp_rst.erst.checkpoint.save_erst_checkpoint_bundle` | `offline_workbench.promotion.erst.save_erst_checkpoint_bundle` |

`isanlp_rst.model_loading.ParserInput` remains production-owned solely to reconstruct released legacy UniRST inventories through the restricted unpickler. That compatibility leaf does not expose corpus preparation or training.

## Enforcement and proof

`pixi run -e production production-boundary` performs the sub-second exhaustive ownership, AST import-closure, and declared-dependency check. `production-artifacts` adds exact wheel/sdist membership and metadata receipts. Negative tests prove unmatched, ambiguous, direct, transitive, dependency, wheel-member, and source-distribution-member failures. All relevant paths must match exactly one ownership rule; there is no fallback classification or second module allowlist.

Completion acceptance builds the wheel and source distribution, inspects their exact members and metadata dependencies, and independently installs the exact wheel into core-only and formats-enabled temporary environments outside this repository. It proves all five promoted parser variants, raw and predefined-EDU analysis, typed serialization/reload, hierarchy, eRST runtime behavior, all five canonical source forms, CPU/MPS parity, and the absence of offline packages. This catches packaging or environment leakage that a source-tree inspection cannot detect.

Model creation never runs in production. Offline promotion validates a complete strict manifest, copies to a temporary sibling, verifies every copied byte, and atomically renames to an immutable release ID. Production loading rejects loose, partial, changed, incompatible, symlinked, or unpromoted inputs before inference.

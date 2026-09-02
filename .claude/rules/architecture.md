# Architecture

## The machine (features 006–012; owner rulings 2026-09-02)

`specs/006-rhetorical-discourse-machine/` is the decision-closed authority for the
machine's rules; `specs/007-…` to `specs/012-…` record what was built against them; the
owner rulings of 2026-09-02 on layout are recorded in
[`specs/010-repository-migration/spec.md`](../../specs/010-repository-migration/spec.md)
and supersede the 006 boundary roster. Where a rule here and a feature disagree, the
feature wins.

### One package, one wheel

```text
rdam/                  the distribution `rdam` and the import package `rdam` — the machine
├── contracts.py       provider/formalism declarations, capability states, native results, outcomes
├── machine.py         Machine.capabilities() (side-effect-free), Machine.analyse() (N outcomes)
├── promotion.py       PromotionDecision — the evidence-gated record every provider is bound by
├── frameworks.py      Technique, coe: identities from resources/framework-identities.json
├── rst/               RST/eRST provider: parser, ingest, eRST, viewer, cli (`rdam-rst`), provider.py
├── dung/              Dung provider: semantics.py, provider.py, resources/promotion-decision.json
└── ibis/              IBIS provider: grammar.py, provider.py, resources/promotion-decision.json
ontology/              vendored Central distribution + rdam LinkML profile (repository, not shipped)
workbench/             the one experimentation root; never imported by rdam
tools/production_boundary/   boundary inspection, reproducible build, validation, clean install
```

- A technique is a sub-package of `rdam`; it is created when that technique first promotes
  a provider (006 FR-002), never speculatively. SDRT, Toulmin, Walton, and PDTB have no
  sub-package and the machine reports them `unavailable(no_promoted_implementation)`.
- No top-level import name other than `rdam` is ever created (`rst`, `dung`, `ibis`, … are
  never packages; `ibis` would shadow the PyPI Ibis dataframe library).
- Exactly one `workbench/`. Production code never imports `workbench.*`, directly or
  transitively, and no wheel or sdist member carries a `workbench/` path (006 FR-006).
  Enforcement: `tools.production_boundary` walks imports from `rdam` and admits only the
  `rdam/` import root in a wheel — `pixi run -e default production-boundary` (the bare
  form is ambiguous across environments).
- Release tooling derives distribution name, version, and package directory from
  `pyproject.toml` (`tools/production_boundary/identity.py`); no tool restates them.

### Capability comes from evidence

A provider's capability is derived from a `PromotionDecision` (006 promotion-evidence
contract; feature 008), never from whether code happens to import or a model happens to
load:

- `rdam.rst.provider.RstProvider` reads the decision published beside the configured
  release (`<store>/<release_id>.promotion.json`) and checks its artifact digest against
  the release manifest before any inference.
- `rdam.dung` and `rdam.ibis` package their decision as a resource bound to the digest of
  their own source files; a source change without a new decision makes the provider
  `unavailable(no_promoted_implementation)`.
- Outcomes are `promote | withhold | replace | retire`; `promote`/`replace` are
  unconstructible without every evidence class admissible. Decisions are recorded in the
  workbench ledger `workbench/promotions/<technique>/`.

### Identity binding

Each technique declares exactly one canonical framework identity from
`coe:artifact/narrative/analytical_frameworks_taxonomy` in Central_Configs. `coe:`
identifiers are **referenced, never redefined locally**; the projection the package ships
(`rdam/resources/framework-identities.json`) is generated from the vendored taxonomy and
checked current by `pixi run ontology-validate`. The RST provider binds to `…/rst` and
declares the formalisms `rst_tree → …/rst` and `erst_graph → …/erst`.

### Persisted identifiers

The package, distribution, command, and provider ids are `rdam`-named. The persisted
contract identifiers are not: `isanlp_rst.production` 2.0.0, `isanlp_rst.parser/modernbert-v1`
(named by the immutable release manifests), `isanlp_rst.build_provenance`,
`isanlp_rst.public_surface`, the schema `$id`s, and `ISANLP_RST_ERST_CHECKPOINT`. They
name contracts and stored releases; changing them is an owner ruling, not a refactor.

### Analysis-only scope, and scale

The machine analyses discourse; it never generates or rewrites it. It serves one person
on one local machine (006 FR-028) — no multi-user, distributed, remote-control-plane, or
enterprise infrastructure without a new explicit requirement. A shared production
abstraction is introduced only when at least two proven production callers need the same
semantic contract with unambiguous ownership (FR-029); the aggregate contract in `rdam`
is the single approved instance.

### Preservation across the migration and the rename

The RST public surface was preserved across the relocation byte-for-byte (010 baseline,
`equivalent: true`). Across the rename to `rdam` 6.0.0 it is preserved **analytically**:
`pixi run rst-baseline compare` diffs every serialized record field by field and
classifies each difference as execution, package identity, package source identity,
derived digest, or analytical; the verdict against the pre-migration baseline is zero
analytical differences
([`specs/010-repository-migration/evidence/release/rename-6.0.0-baseline-comparison.json`](../../specs/010-repository-migration/evidence/release/rename-6.0.0-baseline-comparison.json)).

Immutable release manifests declare `compatibility_range` as of promotion time. A stored
release is shown to run under a later package line by a manifest-bound
`CompatibilityRedeclaration` sidecar (`<store>/<release_id>.compatibility.json`, written
by `pixi run redeclare-compatibility` with its evidence), never by editing the manifest.

## The RST parser (`rdam.rst`)

The parser is a thin façade over predictor families that share a `BasePredictor`
(tokenisation, batching, offset remapping, MPS-safe init, mixed-precision dispatch).

> **Production status (verified 2026-09-01, `rdam/rst/parser.py:90-93`)**: the DMRST
> and UniRST families described below are **archived from production**. `Parser` raises
> `ValueError("Legacy … has been archived from production. Use family='modernbert'")`
> for any of their five `hf_model_version` values before loading anything. The sole
> production family is **ModernBERT** (`rdam/rst/transformer_parser/`), loaded from an
> immutable local release via `Parser.from_model_release(store, release_id,
> family="modernbert")`. The family description below is retained as the record of the
> archived research parsers (their code lives under `workbench/archive/legacy_2021/`);
> the production smoke (`tests/integration/test_production_smoke.py`, `pixi run smoke`)
> exercises only the production family, on every available device.

### Archived research families

`rdam.rst.parser.Parser` dispatched on either `hf_model_version` (HF-pulled) or `family=` / auto-detection (`model_dir=` for local checkpoints):

| Family | Versions | Predictor |
|---|---|---|
| **DMRST** (monolingual / bilingual) | `rstdt`, `gumrrg`, `rstreebank` | `PredictorDMRST` |
| **UniRST** (multilingual, 11 languages) | `rrtrrg`, `unirst` | `PredictorUniRST` |

Each family had its own `src/parser/` (network: `parsing_net.py`, `segmenters.py`, `modules.py`, `discriminator.py`, `metrics.py`) and `src/corpus/` (dataset I/O, `.rs3` / `.dis` utilities). The two trees evolved in parallel and share patterns but **not** code.

`UniRST` adds a `relinventory` parameter so a single multilingual model can target a specific corpus's relation set (e.g. `eng.erst.gum`, `rus.rst.rrt`). Available inventories: [`UniRST_Metrics.md`](../../docs/metrics/UniRST_Metrics.md).

### Shared base (`BasePredictor`)

- razdel / word-level tokenisation and offset bookkeeping
- subword EDU-break recounting (`_recount_spans`)
- offset remapping from tokenised space back to original-text character offsets (`remap_tree_offsets`) — every leaf and internal node ends up with `start` / `end` / `text` fields aligned to the input string
- `_collect_leaf_texts` for round-trip validation against pre-segmented EDUs
- MPS-safe initialisation (orthogonal init routed via CPU on MPS tensors)
- mixed-precision dispatch via `torch.autocast` (`dtype=float32 | bf16 | fp16`)

### Device handling

`device=` is the canonical knob (default `"auto"`):

- `"auto"` (default) → CUDA if present, else MPS on Apple Silicon, else CPU
- `"cpu"` → CPU
- `"mps"` → Apple Silicon Metal backend (`RuntimeError` if unavailable)
- `"cuda"` / `"cuda:N"` → a specific NVIDIA device (`RuntimeError` if no CUDA)
- a `torch.device` → used as-is

The resolved device is stored on the predictor as `self._device` (a `torch.device`). PyTorch has no MPS kernel for `torch.linalg.qr` (used by `torch.nn.init.orthogonal_`); the parser routes this via CPU automatically. No manual env-var hacks required.

### Mixed precision (`dtype=`)

Forward passes go through `torch.autocast`. The model runs in `float32`, `float16`, or `bfloat16` without changing trained weights. Default is `float32` on every device.

- **Apple Silicon (~1k-char inputs):** `float32` beat `bfloat16` / `float16` for every published research model — measured by the maintainer at the time (source comment in the archived base predictor).
- **Large-batch CUDA (Hopper / Ada Tensor Cores):** `bfloat16` is likely faster. Measure with `pixi run bench` before pinning.
- **Tree topology + EDU segmentation are bit-equivalent across all three dtypes** for the published research models — **but relation / nuclearity labels are not.** A node's label is an argmax over a per-node distribution; on a near-tied (high-entropy) node, bf16/fp16 can flip the winner with no structural change. Verified 2026-06-27 (numpy 2.5.0, MPS): rrtrrg on `LONG_EN` flips one entropy-0.40 node from `Elaboration`/NS to `Cause-effect`/SN under bf16 while every span stays byte-identical. Assertion source: `tests/integration/test_integration.py` (the dtype-equivalence suite compares fp16/bf16 **topology**, labels deliberately excluded, against an fp32-CPU baseline).

### Visualisation (`rdam.rst.rstviewer`)

Standalone subpackage ported from `rstviewer`. Public surface lives in `rdam/rst/__init__.py`:

- `render(rs3_source)` — Jupyter / Colab inline render
- `to_html(rs3_path, html_path)` — write standalone HTML
- `to_png(rs3_path, png_path)` / `to_pdf(rs3_path, pdf_path)` — Playwright / Chromium-driven; both have sync and async paths. They detect a running event loop (e.g. inside Jupyter) and dispatch via a worker thread when needed.
- `DiscourseUnit.to_rs3(filename, encoding='utf8')` is the bridge from a parsed tree to the visualiser format.

Chromium launch, the offline navigation guard, viewport JS, graph-bbox JS, and PNG whitespace trim live in [`rdam/rst/rstviewer/_chromium.py`](../../rdam/rst/rstviewer/_chromium.py). The viewer is on the same ruff / pyright bar as the rest of `rdam/`.

The async / sync dispatch in `rdam/rst/__init__.py:_run_coro_sync_result` is load-bearing — don't simplify it without checking notebook compatibility.

### Memory management

`DiscourseUnit` trees keep the substring per node, which dominates memory on large corpora. Pattern:

```python
res["rst"][0].clear_textfields()  # drop .text on every node — keep structure
# … serialise / store …
tree.fill_textfields(full_text)  # repopulate from the original document
```

Calling `.to_rs3()` on a tree with cleared textfields will fail.

### Output shape (`DiscourseUnit`)

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

### Native RST tree representation (`DiscourseUnit`)

`DiscourseUnit` is natively provided in [`rdam/rst/annotation_rst.py`](../../rdam/rst/annotation_rst.py) in modern Python 3.14 (slotted, strictly typed). The legacy `iinemo/isanlp` Git dependency has been retired; `rdam.rst` provides transparent `sys.modules` backward-compatibility aliasing for legacy `from isanlp.annotation_rst import DiscourseUnit` imports.

`DiscourseUnit` fields: `id`, `left`, `right`, `text`, `start`, `end`, `orig_text`, `relation`, `nuclearity`, `proba`, `entropy`. Methods: `clear_textfields()` (recursively sets `.text = ''`), `fill_textfields(full_text)` (re-extracts substring per node), `to_rs3(filename, encoding='utf8')` (writes RS3 XML via internal `Exporter`).

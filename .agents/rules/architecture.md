---
trigger: glob
globs: "rdam/**, workbench/**, tools/**, tests/**"
paths:
  - "rdam/**"
  - "workbench/**"
  - "tools/**"
  - "tests/**"
---

# Architecture

## The machine (features 006–019 and 2026-11-15 13-technique `dclq`/DocLang runtime)

`specs/006-rhetorical-discourse-machine/` is the decision-closed authority for the
machine's core rules; `specs/007-…` to `specs/021-…` record subsequent features; the
owner rulings of 2026-09-02 on layout are recorded in
[`specs/010-repository-migration/spec.md`](../../specs/010-repository-migration/spec.md)
and supersede the 006 boundary roster; the 2026-11-15 expansion unified source ingestion
around `dclq` + DocLang (`6.1.0`) and expanded the composition to thirteen production
technique boundaries (`rdam/frameworks.py:55-69`, `rdam/composition.py:14-73`).

### One package, one wheel

```text
rdam/                        the distribution `rdam` and the import package `rdam` — the machine
├── contracts.py             provider/formalism declarations, capability states, derivations, xpath_alignment, outcomes
├── machine.py               Machine.capabilities() (side-effect-free), Machine.prepare(), Machine.analyse() (2-wave DAG)
├── _llm.py, _grounding.py   vendor KV-cache + Google v1 Interactions adapters, single-turn QuoteRef grounder
├── cli.py, http.py          unified command and optional loopback /v1/ interfaces
├── composition.py           lazy registration of the thirteen production providers
├── ingest/                  dclq + DocLang 0.9 inventory, substrate.py, provider projections, plans, and anchors
├── concepts/                Rust ahocorasick_rs lexical linker over Central semantic resources
├── frameworks.py            Technique, coe: identities from resources/framework-identities.json
├── rst/                     RST provider: DMRST/UniRST parsers, converter, viewer, provider.py
├── centering/               deterministic Centering Theory & Entity Grid provider
├── pdtb/                    PDTB-3 native relations and LLM-backed provider
├── sdrt/                    native SDRS graphs, DISCOR polarity, RFC validator, and LLM-backed provider
├── speech_acts/             Searle & Vanderveken illocutionary acts, felicity conditions, and uptake provider
├── classical_rhetoric/      Aristotelian pisteis, enthymemes, stasis, kairos, and figures provider
├── argument_mining/         Inference Anchoring Theory (IAT) propositions and RA/CA/MA/PA provider
├── toulmin/                 native Toulmin layouts, source-anchored rebuttals, and LLM-backed provider
├── walton/                  12 discriminated Walton scheme instances, critical questions, and provider
├── pragma_dialectics/       four dialectical stages, strategic manoeuvring, and ten-rule fallacy provider
├── ibis/                    dual-mode IBIS provider: gIBIS grammar.py + DocLang extraction
├── aspic/                   dual-mode ASPIC+ provider: structured theory.py + DocLang extraction
└── dung/                    Dung provider: CaDiCaL SAT semantics.py, Wave-2 compilers.py, provider.py
ontology/                    vendored Central distribution + rdam LinkML profile (repository, not shipped)
workbench/                   the one experimentation root; never imported by rdam
tools/production_boundary/   boundary inspection, reproducible build, validation, clean install
```

- Every technique is a real sub-package of `rdam`, created with its provider. The
  supported `production_machine()` composition registers all thirteen boundaries in
  `BOUNDARY_TECHNIQUES` order (`rdam/frameworks.py:55-69`, `rdam/composition.py:47-73`).
- No top-level import name other than `rdam` is ever created (`rst`, `dung`, `ibis`, … are
  never packages; `ibis` would shadow the PyPI Ibis dataframe library).
- Exactly one `workbench/`. Production code never imports `workbench.*`, directly or
  transitively, and no wheel or sdist member carries a `workbench/` path (006 FR-006).
  Enforcement: `tools.production_boundary` walks imports from `rdam` and admits only the
  `rdam/` import root in a wheel — `pixi run -e default production-boundary` (source
  boundary; built archives require artifact validation).
- Release tooling derives distribution name, version, and package directory from
  `pyproject.toml` (`tools/production_boundary/identity.py`); no tool restates them.

### Capability reports checked local prerequisites

`rdam.ingest` owns source material for every technique across the four supported
`SourceForm` values (`text`, `edus`, `doclang_xml`, `doclang_archive`;
`rdam/ingest/contracts/source.py:17-21`), backed by `dclq` (`LoadedDocument`, `NS`) and
`doclang` (`pyproject.toml:44-45`). `rdam.rst.ingest`, `_inventory_docling`, and
`rdam.rst.markdown` have no compatibility shims. Generic machine orchestration imports no
technique package; `rdam/composition.py` imports providers lazily when called.

Inventory and default disposition run once per source, followed by a shared
`LinguisticSubstrate` (`rdam/ingest/substrate.py:330-346` — Razdel sentences/tokens,
Rust `ahocorasick_rs` discourse/epistemic/speech-act cues, and `rdam.concepts` lexical
mentions) and one pure projection per distinct content requirement:

- Centering and all ten LLM-capable text providers share `SUBSTANTIVE_CLASSES`
  (`rdam/ingest/requirements.py:10-24`), admitting prose, headings, lists, dialogue turns,
  captions, VLM `<description>` blocks, speaker `<notes>`, code, formulas, tables, cells,
  and fields into one XPath-anchored stream.
- Neural `RstProvider` uses `AUTHORED_PROSE_V1`, keeping tables, code, formulas, pictures,
  notes, and machine-generated descriptions as receipted side channels.
- `DungProvider` declares no content requirement and receives no text projection
  (`rdam/dung/provider.py:85-109`). Dual-mode `IbisProvider` and `AspicProvider` bypass
  text projections when caller-supplied `StructuredInput` is given and consume the
  substantive projection when analysing a source document (`rdam/frameworks.py:75-79`).

Execution is in-process with four workers by default (bounded 1–13) and request-ordered
results (`rdam/machine.py`). Wave-1 techniques execute concurrently (with a Prefix-Warmth
Coordinator in `rdam/_llm.py` warming shared vendor KV caches across OpenAI
`prompt_cache_key`, Anthropic `cache_control`, and Google GA `v1` Interactions
`aclient.interactions.create(..., store=False)`). When `AggregateRequest.derivations`
specifies `DerivationSpec` (`from_aspic`, `from_argument_mining`, `from_ibis`, or
`from_toulmin_walton`), Wave-2 `DungProvider` compiles the completed Wave-1 payload(s)
deterministically (`rdam/dung/compilers.py:213-236`) and records exact `lineage`. Across
all aligned outcomes, `AggregateAnalysis.xpath_alignment` indexes findings by canonical
`dclq` XPath (`rdam/contracts.py:508`).

> The promotion-evidence gate (feature 008) was removed on 2026-09-02 by owner ruling. It
> was never requested and it reported working parsers as `unavailable`. Capability is now
> exactly what it says: can this provider run?

- `rdam.rst.provider.RstProvider` is `available` when the configured `hf_model_version` is
  one the façade knows how to load, or when the named local release validates.
  The check loads no model and touches no network; the parser is built on first `analyse`.
- `rdam.centering` (`entity-grid-v1`) and `rdam.dung` (`cadical-sat-v2`, capacity 128 via
  `python-sat` CaDiCaL 1.9.5) are exact and deterministic, so they are `available`
  whenever imported.
- `rdam.ibis` (`gibis-v2`) and `rdam.aspic` (`aspic-plus-v1`) are dual-mode: deterministic
  validation/evaluation on `structured_input` is always available, while document
  extraction requires a resolved LLM model (`rdam/ibis/provider.py:203-237`,
  `rdam/aspic/provider.py:276-310`).
- `rdam.pdtb`, `rdam.sdrt`, `rdam.speech_acts`, `rdam.classical_rhetoric`,
  `rdam.argument_mining`, `rdam.toulmin`, `rdam.walton`, and `rdam.pragma_dialectics` are
  available when their configured LLM model resolves. Declarations do not construct an LLM
  client; model proposals resolve `QuoteRef` spans via `rdam/_grounding.py` and pass each
  technique's deterministic native validator before becoming results.
- The three unavailability reasons are `not_implemented`, `model_unavailable`, and
  `missing_structured_input`. None of them is retryable.

eRST execution, checkpoint handling, and research contracts live in `workbench/erst/`
by owner instruction on 2026-09-06. Production retains only passive saved-report
graph/evidence data; it cannot select or load eRST.

### Identity binding

Each technique declares exactly one framework identity from
`coe:artifact/narrative/analytical_frameworks_taxonomy` in Central_Configs
(`rdam/frameworks.py:1-19`, verified at
`ontology/vendor/central-configs/domains/narrative/analytical_frameworks.yaml:21-176`).
`coe:` identifiers are **referenced, never redefined locally**; the projection the package
ships (`rdam/resources/framework-identities.json`) is generated from the vendored taxonomy
and checked current by `pixi run ontology-validate`. The RST provider binds to `…/rst` and
declares only `rst_tree → …/rst`. The `erst` identity remains in `rdam/frameworks.py` for
historical records and workbench evaluation.

### Persisted identifiers

The package, distribution, command, and provider ids are `rdam`-named. The persisted
contract identifiers are not: `isanlp_rst.production` 3.0.0 (historical 2.0.0 remains
readable), `isanlp_rst.parser/modernbert-v1` (a historical immutable manifest identity,
not the active architecture), `isanlp_rst.build_provenance`, `isanlp_rst.public_surface`,
the schema `$id`s, and `ISANLP_RST_ERST_CHECKPOINT`. They name contracts and stored
releases; changing them is an owner ruling, not a refactor.

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

Immutable release manifests declare `compatibility_range` as of release time. A stored
release is shown to run under a later package line by a manifest-bound
`CompatibilityRedeclaration` sidecar (`<store>/<release_id>.compatibility.json`, written
by `pixi run python -m workbench.promotion.compatibility` with its evidence), never by
editing the manifest.

## The RST parser (`rdam.rst`)

The parser is a thin façade over predictor families that share a `BasePredictor`
(tokenisation, batching, offset remapping, MPS-safe init, mixed-precision dispatch).

> **Production status**: The active production families are **DMRST** and **UniRST**
> (`rdam.rst.dmrst_parser.predictor.PredictorDMRST` and `rdam.rst.universal_parser.PredictorUniRST`),
> loaded either via `hf_model_version` or from an immutable local release via
> `Parser.from_model_release(store, release_id)`. Experimental pure-transformer
> research architectures reside strictly under `workbench/training/modern/` and are not
> in production code.

### Production families

`rdam.rst.parser.Parser` dispatched on either `hf_model_version` (HF-pulled) or `family=` / auto-detection (`model_dir=` for local checkpoints):

| Family | Versions | Predictor |
|---|---|---|
| **DMRST** (monolingual / bilingual) | `rstdt`, `gumrrg`, `rstreebank` | `PredictorDMRST` |
| **UniRST** (multilingual, 11 languages) | `rrtrrg`, `unirst` | `PredictorUniRST` |

Each family retains its own neural modules under `src/parser/` to preserve trained
parameter and pickle identities. Shared infrastructure covers metrics, device/dtype
selection and base predictor behavior; corpus construction lives in `workbench`.
See the [consolidation decision](../../artifacts/reviews/architecture-decisions/parser-infrastructure-consolidation.md).

`UniRST` adds a `relinventory` parameter so a single multilingual model can target a specific corpus's relation set (e.g. `eng.erst.gum`, `rus.rst.rrt`). Available inventories: [`UniRST_Metrics.md`](../../docs/metrics/UniRST_Metrics.md).

### Shared base (`BasePredictor`)

- razdel / word-level tokenisation and offset bookkeeping
- subword EDU-break recounting (`_recount_spans`)
- offset remapping from tokenised space back to original-text character offsets (`remap_tree_offsets`) — every leaf and internal node ends up with `start` / `end` / `text` fields aligned to the input string
- `_collect_leaf_texts` for round-trip validation against pre-segmented EDUs
- MPS-safe initialisation (orthogonal init routed via CPU on MPS tensors)
- mixed-precision dispatch via `torch.autocast` (`dtype=float32 | bf16 | fp16`)

### Device handling

`device=` is the default-auto device selector (`rdam/rst/parser.py`):

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
- **The dtype fixtures check tree topology and EDU segmentation across three dtypes**; this is sample-scoped evidence for the published models — **but relation / nuclearity labels are not.** A node's label is an argmax over a per-node distribution; on a near-tied (high-entropy) node, bf16/fp16 can flip the winner with no structural change. Verified 2026-06-27 (numpy 2.5.0, MPS): rrtrrg on `LONG_EN` flips one entropy-0.40 node from `Elaboration`/NS to `Cause-effect`/SN under bf16 while every span stays byte-identical. Assertion source: `tests/integration/test_integration.py` (the dtype-equivalence suite compares fp16/bf16 **topology**, labels deliberately excluded, against an fp32-CPU baseline).

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

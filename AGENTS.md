# AGENTS.md — rdam, the Rhetorical Discourse Analysis Machine

The operating manual for every AI agent in this repository (Claude Code, Codex, Gemini,
Antigravity). `CLAUDE.md` imports this file and adds only Claude Code mechanics. The
global working agreement (`~/.claude/CLAUDE.md`) applies first.

## What this is

`rdam` is Steve Allison's permanently analysis-only machine: it runs several discourse and
argumentation techniques natively, side by side, without collapsing them into a common
formalism. One distribution, one package, every technique a sub-package:

| Sub-package | Technique |
|---|---|
| `rdam` | the machine: provider and formalism declarations, capability states, native results, `Machine.prepare()` and `Machine.analyse()`, 2-wave derivations, `xpath_alignment`, unified CLI and optional HTTP |
| `rdam.ingest` | `dclq` + DocLang 0.9 single-stream source inventory, `LinguisticSubstrate`, provider-specific projections, capacity planning, speaker evidence and anchors |
| `rdam.rst` | RST: DMRST and UniRST discourse parsers (Steve's evolution of Elena Chistova's IsaNLP RST Parser), viewer, and the machine adapter `rdam.rst.provider.RstProvider` |
| `rdam.centering` | Centering Theory & Entity Grid: deterministic `Cb`/`Cp`/`Cf` transitions and Barzilay–Lapata role grids |
| `rdam.pdtb` | PDTB-3 binary relations with exact source spans, all seven relation types, signal evidence, canonical senses |
| `rdam.sdrt` | SDRS graphs with EDUs, CDUs, coordinating/subordinating relations, DISCOR polarity, deterministic graph and right-frontier validation |
| `rdam.speech_acts` | Searle & Vanderveken illocutionary force, direction of fit, felicity conditions, and conversational uptake |
| `rdam.classical_rhetoric` | Aristotelian rhetorical pisteis (`ethos`, `pathos`, `logos`), enthymemes, stasis, kairos, and figures |
| `rdam.argument_mining` | Inference Anchoring Theory (IAT) propositions (`I`-nodes) and `RA`/`CA`/`MA`/`PA` relational anchors |
| `rdam.toulmin` | complete Toulmin layouts with claim, grounds, warrant, backing, qualifiers, and source-anchored rebuttals |
| `rdam.walton` | 12 typed Walton scheme instances with exact premise roles and critical-question states |
| `rdam.pragma_dialectics` | four dialectical stages, strategic manoeuvring, and ten-rule fallacy violations |
| `rdam.ibis` | dual-mode IBIS: deterministic validation on supplied structures or grounded DocLang/text extraction under the gIBIS link grammar |
| `rdam.aspic` | dual-mode ASPIC+: structured argumentation theories, preferences, defeats, and rationality postulates on supplied theories or grounded source documents |
| `rdam.dung` | Dung abstract argumentation: grounded, complete, preferred and stable semantics via bitmask kernel + CaDiCaL 1.9.5 (`cadical-sat-v2`, capacity 128) over a supplied or explicitly derived framework |
| `rdam.concepts` | exact Rust `ahocorasick_rs` lexical links from source surfaces to Central's semantic resources (labels and typed terms); never semantic acceptance |

The machine analyses discourse; it never generates or rewrites it. It serves one person on
one local machine. `rdam.production_machine()` is the supported composition of all thirteen
provider boundaries (`rdam/composition.py:14-73`); each provider remains directly callable.
eRST is workbench-only (owner instruction 2026-09-06). What a provider can run is what
`describe_capabilities()` / `machine.capabilities()` reports; that call is the authority,
not this file.

## Provenance and licence

The original RST research code and the trained model weights are by Elena Chistova
(`tchewik/isanlp_rst`). The MIT-licensed source carries her copyright (`LICENSE`). Model
weights are **CC BY-NC 4.0, research and non-commercial use only** (`LICENSE_MODELS`).
This repository is Steve's evolution of that code: own design direction, own
infrastructure, own roadmap; not a tracking fork. The machine and every non-RST provider
are Steve's own code under MIT; LLM-produced analyses remain subject to the configured
model provider's terms. Commercial use requires retraining weights under a permissive
licence or replacing the models.

## Git

Single remote `origin` → `Steve-Allison/Rhetorical_Discourse_Analysis_Machine` (renamed
from `isanlp_rst` on 2026-09-02; the old name redirects). No upstream tracking. Commit
directly to `master` and push; no pull requests. The `post-commit` and `post-checkout`
hooks rebuild `graphify-out/` in the background, so it shows as modified afterwards;
commit it with the next change.

## HARD RULE: this is Steve's code

Treat **every** module as Steve Allison's production Python. Provenance is licence and
history, not a quality waiver.

- One bar: modern Python 3.14 (`.claude/rules/code-standards.md`), applied always,
  including `*/src/parser/`, `*/src/corpus/`, `rstviewer/`, `data_manager.py`,
  `du_converter.py` and anything else that started as research code. Do not add
  `from __future__ import annotations` (PEP 563 stringification; 3.14 deferred evaluation
  is the default).
- Always fix quality issues you meet: warnings, no-op constructor args, footguns, outdated
  idioms, missing types on code you touch. Never leave them because the file is
  "inherited" or "not the task". Refactor when it pays off; "what would upstream accept"
  is not a consideration.
- Do not change trained architecture or inference maths in the name of style. Constructor
  no-ops and dead warnings are in scope; swapping a 1-layer LSTM for a 2-layer one is not.

## HARD RULE: pixi environment topology

Two environments, declared in `pyproject.toml`:

- **`default`** (the `offline` feature; `offline` is an explicit alias): everything for
  daily work (`dev`, `offline`, `http`; `pyproject.toml:136-140`). Every everyday task runs
  here without `-e`.
- **`production`**: the isolated clean-room consumer environment holding only what
  `pip install rdam` provides (`dclq` and `doclang[schematron-saxon]` included in core
  `[project.dependencies]` at `pyproject.toml:44-45`), installed as the editable source.

Production code (everything under `rdam/`) never imports offline or dev packages
(`pytest`, `nltk`, `peft`, `fire`, `jsonnet`, `blake3`) or `workbench`;
`pixi run production-boundary` enforces it.

The task table in `pyproject.toml` is the authority; `pixi task list` shows every task with
its description. When to use what:

- **Everyday:** `pixi run lint`, `typecheck`, `mdlint`, `test` (the fast set, no model
  loads). The Stop gate runs these four.
- **Predictor stack** (`rdam/rst/dmrst_parser/`, `rdam/rst/universal_parser/`,
  `parser.py`, `model_loading/`): targeted tests while working, then `pixi run test-all`
  once at the end; it includes the dtype-equivalence suite and the production smoke
  (`pixi run smoke` alone loads every release in `models/model-releases` on every device).
- **Local package build:** clean committed inputs; any HEAD tag matches `v<version>` from
  `pyproject.toml`. `pixi run build-production`, `pixi run validate-production-artifacts`,
  `pixi run -e production production-clean-install --model-store <store> --release-id <id>`.
  `dist/<version>/` is ignored build output; the committed record is the evidence JSON the
  build task names. `production-import-check` imports the editable source and certifies no
  wheel.
- **Stored model compatibility:** `pixi run python -m workbench.promotion.compatibility --help`.
- **Quality diagnostics:** `pixi run rst-diag <paths>` (`--json` for machine output):
  preparation coverage, content-class decisions, anchor integrity, tree structure, relation
  distribution, subdivision and timing across the canonical source forms.
- **Format & mutation gates:** `pixi run rst-format-coverage` and
  `pixi run rst-mutation-test` locally. All verification and release gates are local-only
  (no GitHub Actions workflows).

## HARD RULE: no invented release theatre

When asked to release or publish, deliver the requested artefacts and the requested
publication action directly. Never invent, require or preserve receipt files, evidence
lifecycles, promotion gates, second-machine ceremonies, downstream-specific contracts or
other process machinery unless Steve has explicitly asked for that mechanism or it is
technically necessary for the stated release.

External publication is forbidden unless Steve names the exact destination in that
request: never upload this project or its artefacts to PyPI, package indexes, registries,
release services or any other external destination by inference from the word "release".
A repository tag and tracked artefacts are a complete release when that is what was asked.

Verification establishes the requested fact, then stops. Do not turn a build, install,
commit, tag or push into a new release system, and do not delay a release for a process
requirement the project does not already have. If an existing mechanism blocks the
requested delivery without serving it, remove that mechanism rather than asking Steve to
satisfy it. The promotion-evidence system was removed on 2026-09-02 for exactly this
reason; discovery checks local prerequisites without probing a remote model, and actual
analysis determines runtime success.

## HARD RULE: `dclq` and DocLang spec currency

Before changing DocLang loading (`inventory_doclang` in `rdam/ingest/_doclang.py` and the
`rdam.ingest.doclang` decoder/loader), `dclq` XPath handling (`rdam/ingest/doclang/loader.py`
and `rdam/ingest/substrate.py`), format harvest (`rdam/ingest/_harvest.py`), boundaries,
mappers, fixtures, or docs that describe those contracts, **verify compliance with the
current `dclq` and DocLang specs**, even when the task looks unrelated to a version bump.
The pixi lock, the in-repo fixtures, and `.claude/memory/` are what was last shipped, not
what upstream is today; stating a lock version as "the spec" is an evidence-marking
violation.

1. **`dclq`:** `dclq` PyPI latest vs the `pyproject.toml` pin (`dclq>=2.107.0,<3`,
   `pyproject.toml:44`) vs `pixi.lock`; verify `LoadedDocument`, `NS`, and canonical XPath
   indexing against the installed `dclq` source. Raw `DoclingDocument` JSON and Markdown
   ingestion (`_inventory_docling`, `rdam.rst.markdown`) were retired in `6.1.0` in favour
   of unified DocLang-native ingestion (`SourceForm.TEXT`, `EDUS`, `DOCLANG_XML`,
   `DOCLANG_ARCHIVE` at `rdam/ingest/contracts/source.py:17-21`).
2. **DocLang:** owner instruction 2026-10-09: "yes, track main and build track support."
   Upstream `main` latest commit vs the `doclang` git pin in `pyproject.toml:45` vs the
   fixture manifest commit (all three match); the current upstream `spec.md`; upstream
   `tests/data/valid` vs `tests/fixtures/doclang/` (count, names, `.dclg` extension);
   whether `validate()` still needs `doclang[schematron-saxon]`.
3. **Our envelopes:** `isanlp_rst.production` / `isanlp_rst_doclang` contract and schema
   versions bump only when *our* result shape changes, never with an upstream package
   version.

If lock, fixtures or harvest behaviour lag the current spec, update them in the same work
or flag the gap explicitly. Never document a stale contract as current.

## HARD RULE: evidence marking

A factual claim about this repository's data, schema, code or runtime is either
**verified**, with its evidence cited inline, or written as
`ASSUMED (<date>, to verify): <claim>` with the verification needed. There is no third
category, and a sample is reported at the sample's scope ("all five fixtures inspected on
<date>"), never as a universal.

| Claim about | Evidence required |
|---|---|
| what code does | a `path:line` read this session |
| what data contains | the actual contents opened, not summary statistics over it |
| a dependency's API | its source at a named version, `path:line` |
| runtime behaviour | a command run and its output, in the session |
| a repo-wide property | a written rule, or a survey that exhausts the scope |

`.claude/hooks/no-assumptions-check.sh` blocks a Write or Edit that makes a canonicity,
custom-field or extension claim without an evidence anchor or `ASSUMED` marker in the
same edit.

## Layout, identity and ingest

The layout rulings of 2026-09-02 (one package `rdam/` shipped as one wheel; `isanlp_rst` is
not a protected name; the persisted contract identifiers that keep their `isanlp_rst.*`
names; `ontology/` at the top level; exactly one `workbench/`, never imported by production
code) and the ingest and execution mechanics are in `.claude/rules/architecture.md`, which
loads whenever a file under `rdam/`, `workbench/`, `tools/` or `tests/` is touched. Two
facts needed everywhere: `rdam.ingest` is the one public ingest surface
(`ProductionIngestor.capabilities()`, `.prepare()`, `.analyse()`), with no compatibility
shim for removed format-specific functions; and `dclq` + `doclang[schematron-saxon]` now
ship in core `[project.dependencies]` (`pyproject.toml:44-45`), leaving `http`, `dev`, and
`offline` as the optional extras (`pyproject.toml:58-82`).

## Central model store (`../_models`)

- **Single shared cache**: All local ML/NLP/LLM/embedding models and caches
  (`HF_HOME`, `HF_HUB_CACHE`, `HF_ASSETS_CACHE`, `HF_XET_CACHE`, `TORCH_HOME`)
  MUST resolve to the workspace-level `../_models` directory (configured in
  `pyproject.toml` `[tool.pixi.activation.env]`). Never create per-repo model
  caches or store model weights in `~/.cache/`.
- **Reuse before adding**: Before introducing, configuring, or downloading any
  new model, inspect `../_models` (including `../_models/huggingface/hub` and
  `../_models/torch`) to reuse an already-installed model for that capability
  instead of adding a duplicate or second variant.

## Shared subject-matter linking and Central_Configs

`rdam.concepts` consumes `Central_Configs` v5.0.0 proper-noun surface rules (`LinkableProperNoun`
only, `../Central_Configs/AGENTS.md` Rule 6) and emits deterministic Stage 1 lexical mention
evidence; see `docs/concept-linking.md`. `Central_Configs` (`../Central_Configs`) is the
sole shared authority, with zero vendored YAML snapshots in this repository. After it
changes: rebuild `../Central_Configs` (`pixi run build`), then run
`pixi run project-framework-identities`, `pixi run project-discourse-concepts`,
`pixi run compile-concept-index`, and `pixi run ontology-validate`.
`tests/concepts/test_ontology.py` and `tests/concepts/test_golden_grounding.py` verify parity
and Stage 1 grounding against `../Central_Configs`.

## Where things are

The annotated source tree is the first section of `.claude/rules/architecture.md`. Outside
`rdam/`: `ontology/` (the `rdam` LinkML application profile and `rdam-providers.yaml`),
`tools/production_boundary/` (boundary inspection, build, artifact validation,
clean install, `rst-baseline`), `workbench/` (offline corpus, training, evaluation,
model-store release tooling; `workbench/erst/` is the suspended eRST work), and
`.claude/memory/` (hand-maintained `verified_*` and `open_*` notes indexed by its
`MEMORY.md`; read on demand, nothing loads them automatically).

## graphify

The knowledge graph lives under `graphify-out/`; it exists only when
`graphify-out/graph.json` does. For codebase questions run `graphify query "<question>"`
first, `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"`
for one concept; use `graphify-out/wiki/index.md` for broad navigation and read
`GRAPH_REPORT.md` only when those do not surface enough. When the user types `/graphify`,
use the installed graphify skill before anything else.

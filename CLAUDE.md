# CLAUDE.md

`isanlp_rst` — Steve Allison's RST (Rhetorical Structure Theory) parser. Predicts discourse trees across 11 languages via the `unirst` multilingual model plus three monolingual / bilingual models (`rstdt`, `gumrrg`, `rstreebank`). Pixi-managed, MPS-aware, Apple-Silicon-first, real test suite, real CI.

## Provenance & licence

The original RST research code and the trained model weights are by Elena Chistova (`tchewik/isanlp_rst`). The MIT-licensed source carries her copyright (see [`LICENSE`](LICENSE)). Model weights are **CC BY-NC 4.0 — research and non-commercial use only** (see [`LICENSE_MODELS`](LICENSE_MODELS)). This repository is Steve's evolution of that code: own design direction, own infrastructure (pixi, tests, CI, MPS), own roadmap. Not a tracking fork.

Commercial use requires either retraining new weights under a permissive licence or replacing the models entirely.

## Git remotes

Single remote: `origin` → `Steve-Allison/isanlp_rst`. No upstream tracking. All pushes go to `origin`. Verify: `git remote -v`.

## Pixi commands

Two environments: **`default`** (everything for daily work; active without `-e`) and **`production`** (isolated clean-room environment; its installed distribution is the editable source). The task table in `pyproject.toml` is the authority — `pixi task list` shows every task with its description, and [`commands.md`](.claude/rules/commands.md) says when to use which. Adding dependencies: `pixi add <package>`. Never `pip install`.

CI (`.github/workflows/ci.yml`) runs lint, typecheck, mdlint, and the fast tests on macOS arm64 with the pixi lock (**Python 3.14**; `requires-python` is `>=3.14`); the slow suite runs nightly. The model smoke is local-only because weights are not in git: `pixi run smoke`.

## Project-specific overrides of global rules

- **No fork-only-push rule.** This repo is not a fork in spirit; `origin` is the only valid push target by virtue of remote configuration. The earlier "fork-only push" rule has been retired.
- **No vendored-dependency mentality.** This is Steve's code. Refactor when it pays off; don't defer to "what would upstream accept".
- **One quality bar.** Every module is Steve's production Python — modern, world-class, always. Provenance is not a style freeze. See [`AGENTS.md`](AGENTS.md). **HARD RULE.**
- **No assumptions.** Factual claims about data / schema / code / runtime are either verified (with cited evidence) or explicitly marked `ASSUMED`. No silent inference, no sample-to-universal escalation, no eyeballing summary stats and concluding semantics. See [`no-assumptions.md`](.claude/rules/no-assumptions.md). **This is a project HARD RULE.**
- **Docling / DocLang spec currency.** Before format-native work, verify we match current upstream specs — lockfile and fixtures are last-shipped, not the spec. See [`AGENTS.md`](AGENTS.md). **HARD RULE.**

## Detail in `.claude/rules/`

| File | Loads when |
|---|---|
| [`no-assumptions.md`](.claude/rules/no-assumptions.md) | Always. **HARD RULE.** Forbids stating assumptions as fact; requires evidence-cited claims or explicit `ASSUMED` marking. |
| [`architecture.md`](.claude/rules/architecture.md) | Always. Parser families, inference flow, visualisation, memory management. |
| [`code-standards.md`](.claude/rules/code-standards.md) | Always. Modern Python everywhere (one bar). Testing and gotchas. |
| [`commands.md`](.claude/rules/commands.md) | Always. Full pixi command reference + when to use each. |
| [`AGENTS.md`](AGENTS.md) | Always. **HARD RULES.** One quality bar (Steve's code, modern Python). Docling / DocLang spec currency. |

## Active roadmap

### Machine direction (feature 006, planned)

This repository becomes the first provider of the **Rhetorical Discourse Analysis
Machine** — a permanently analysis-only machine running several discourse and
argumentation techniques natively, side by side, without collapsing them into a common
formalism. `isanlp_rst` is its established RST/eRST provider and keeps its import name
and public contract unchanged across the eventual relocation into `rst/`.

Feature 006 is decision-closed architecture and governance: it ships no code and moves no
files. Authority is [`specs/006-rhetorical-discourse-machine/`](specs/006-rhetorical-discourse-machine/);
the working rules are summarised in [`architecture.md`](.claude/rules/architecture.md)
§"Machine architecture (feature 006)".

Three features must be specified and cross-artifact consistency checked **before
repository migration begins** (FR-025):

1. **Aggregate analysis contract + ontology vendoring** — `machine/`, `ontology/`, and the
   `production-boundary` extension enforcing the no-`workbench`-import and
   no-`workbench`-in-distributable rules (neither is implemented yet).
2. **Workbench promotion system** — the evidence-gated promotion the current flow does
   not provide; its truthful gap list is
   [`evidence/promotion-gap-audit.md`](specs/006-rhetorical-discourse-machine/evidence/promotion-gap-audit.md).
3. **RST provider adapter** — consumes the supported `isanlp_rst` public contract without
   duplicating, reinterpreting, or bypassing its authority (FR-010).

**Repository migration** is then its own fourth decision-closed feature, executed under
the RST-preservation contract and carrying the baseline capture, migration safety state,
packaging verification, and project-identity adoption (including sibling-repo reference
updates and per-project memory/settings path migration).

Provider order thereafter: **Dung → IBIS → SDRT → Toulmin/Walton → PDTB-if-ever**. Each
technique gets its own decision-closed Spec Kit feature, authored only once workbench
evidence identifies a credible candidate.

**Migration is blocked (FR-026)** while protected workbench runs are live or
unreconciled. It starts only from a recorded MigrationSafetyState: zero live protected
processes, the run/checkpoint inventory reconciled, and Steve's dated confirmation. The
20-epoch ModernBERT convergence run (task-636) is live on this machine's MPS; nothing may
compete with it.

### Production source ingest

Production source ingest has one public surface: `isanlp_rst.ingest` — `ProductionIngestor.capabilities()`, `.prepare()`, and `.analyse()`. The accepted source forms and their availability are whatever `describe_capabilities()` reports; that call is the authority, not this file. The old format-specific parsing functions and result envelopes were removed rather than deprecated; no compatibility route remains.

The optional **`formats` extra** supplies `docling-core`, `doclang`, `markdown-it-py`, and `mdit-py-plugins`: `pip install isanlp_rst[formats]`. Core parser consumers avoid that dependency chain. `pixi install` includes `formats`; keep these dependencies outside `[project.dependencies]`.

Canonical ingest inventories source content before applying the explicit `AUTHORED_PROSE_V1` relevance policy. Authored prose reaches the RST parser; tables, code, machine descriptions, furniture, and other non-prose remain traceable side channels unless a future named policy explicitly changes their role. Every decision is represented in the preparation receipt, source anchors survive into the analysis, long or structured material uses the governed subdivision/stitching path, and persistent cache identity includes the complete analytical pipeline fingerprint.

Format code beneath `isanlp_rst.doclang` and `isanlp_rst.markdown` is private decoding support for the canonical service. Docling JSON is loaded directly with current `docling-core`. There is no independent format mapper, result schema, cache, or public entry point.

Quality measurement: `pixi run rst-diag <paths>` ([`scripts/rst_diag.py`](scripts/rst_diag.py)) — preparation coverage, content-class decisions, anchor integrity, tree structure, relation distribution, subdivision, and timing across the canonical source forms.

Project memory at [`.claude/memory/MEMORY.md`](.claude/memory/MEMORY.md) tracks verified facts (spec citations, fixture evidence) and open design questions.

## Files worth knowing

- [`rst/isanlp_rst/parser.py`](rst/isanlp_rst/parser.py) — public entry point, dispatches to predictor families.
- [`rst/isanlp_rst/cli.py`](rst/isanlp_rst/cli.py) — unified `isanlp-rst` CLI (parse, view, serve, version).
- [`rst/isanlp_rst/transformer_parser/`](rst/isanlp_rst/transformer_parser/) — SOTA ModernBERT pure-transformer parsing net, biaffine scorer, and CKY chart decoder.
- [`rst/isanlp_rst/annotation_rst.py`](rst/isanlp_rst/annotation_rst.py) — native `DiscourseUnit` and RS3 XML serialization.
- [`rst/isanlp_rst/ingest/`](rst/isanlp_rst/ingest/) — sole production source inventory, preparation, analysis, receipt, subdivision, and cache API.
- [`rst/isanlp_rst/contracts/`](rst/isanlp_rst/contracts/) — typed contracts: `RstAnalysis`, `RstDocument`, `SecondaryRelationEdge`, `DiscourseSignal`, envelope serializations.
- [`rst/isanlp_rst/erst/`](rst/isanlp_rst/erst/) — Extended RST (eRST): RS4 reader/writer, typed signals, complete candidates, and formally constrained `ErstSecondaryEdgeDecoder`.
- [`rst/isanlp_rst/hierarchical/stitcher.py`](rst/isanlp_rst/hierarchical/stitcher.py) — `MacroMicroStitcher`: two-stage hierarchical section/macro tree stitching.
- [`rst/isanlp_rst/rstviewer/`](rst/isanlp_rst/rstviewer/) — visualizer and HTML/PNG export engine.
- [`rst/isanlp_rst/doclang/`](rst/isanlp_rst/doclang/) — private DocLang XML/archive decoding helpers used by canonical ingest.
- [`rst/isanlp_rst/markdown/`](rst/isanlp_rst/markdown/) — private Markdown decoding helper used by canonical ingest.
- [`machine/rdam/`](machine/rdam/) — the machine's aggregate analysis contract (import name `rdam`): provider and formalism declarations, capability states, native results, `Machine.analyse()` returning one explicit outcome per technique. Feature 007.
- [`rst/rdam_rst/`](rst/rdam_rst/) — the machine-facing RST/eRST provider adapter (import name `rdam_rst`): declares capability from the promotion decision published beside the configured release and hands the machine `isanlp_rst`'s outcome envelope verbatim. Feature 009.
- [`ontology/`](ontology/) — vendored Central distribution (read-only, `vendor/central-configs/`) and the `rdam` LinkML application profile binding boundaries to `coe:` framework identities; `pixi run ontology-validate`.
- [`workbench/`](workbench/) — offline workbench: corpus ingestion, training recipes, Parseval evaluation, and central audit ledger (`workbench/experiments/central_ledger.jsonl`).
- [`docs/metrics/UniRST_Metrics.md`](docs/metrics/UniRST_Metrics.md) — per-corpus metrics for the multilingual model.

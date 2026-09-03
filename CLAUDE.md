# CLAUDE.md

`rdam` — the **Rhetorical Discourse Analysis Machine**: Steve Allison's permanently
analysis-only machine that runs several discourse and argumentation techniques natively,
side by side, without collapsing them into a common formalism. One distribution, one
package, every technique a sub-package:

| Sub-package | Technique | State (2026-09-02) |
|---|---|---|
| `rdam` | the machine: provider and formalism declarations, capability states, native results, `Machine.analyse()` returning one explicit outcome per technique | feature 007 |
| `rdam.rst` | RST / eRST — DMRST and UniRST discourse parsers (Steve's evolution of Elena Chistova's IsaNLP RST Parser), canonical source ingest, eRST completion, viewer, the `rdam-rst` command, and the machine adapter `rdam.rst.provider.RstProvider` | `available` |
| `rdam.dung` | Dung abstract argumentation: grounded, complete, preferred, stable semantics over a supplied or explicitly derived framework | `available` |
| `rdam.ibis` | IBIS: issue–position–argument structures validated under the gIBIS link grammar | `available` |
| SDRT, Toulmin, Walton, PDTB | no provider — the machine reports `unavailable(not_implemented)`; no stubs | not yet built (006 FR-024) |

Pixi-managed, MPS-aware, Apple-Silicon-first, real test suite, real CI.

## Provenance & licence

The original RST research code and the trained model weights are by Elena Chistova (`tchewik/isanlp_rst`). The MIT-licensed source carries her copyright (see [`LICENSE`](LICENSE)). Model weights are **CC BY-NC 4.0 — research and non-commercial use only** (see [`LICENSE_MODELS`](LICENSE_MODELS)). This repository is Steve's evolution of that code: own design direction, own infrastructure (pixi, tests, CI, MPS), own roadmap. Not a tracking fork. The Dung and IBIS providers and the machine are Steve's own code under MIT.

Commercial use requires either retraining new weights under a permissive licence or replacing the models entirely.

## Git remotes

Single remote: `origin` → `Steve-Allison/Rhetorical_Discourse_Analysis_Machine` (GitHub renamed from `isanlp_rst` on 2026-09-02; the old name redirects). No upstream tracking. All pushes go to `origin`. Verify: `git remote -v`.

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
| [`architecture.md`](.claude/rules/architecture.md) | Always. The machine's layout and rules, the RST parser family, inference flow, visualisation, memory management. |
| [`code-standards.md`](.claude/rules/code-standards.md) | Always. Modern Python everywhere (one bar). Testing and gotchas. |
| [`commands.md`](.claude/rules/commands.md) | Always. Full pixi command reference + when to use each. |
| [`AGENTS.md`](AGENTS.md) | Always. **HARD RULES.** One quality bar (Steve's code, modern Python). Docling / DocLang spec currency. |

## Layout and identity (owner rulings, 2026-09-02)

- **One production package at the repository root, `rdam/`, shipped as one wheel** (`rdam` 6.0.0). Every technique is a sub-package of it. This supersedes the per-technique top-level boundary roster of feature 006 (`machine/`, `rst/`, `dung/`, …); the supersession is recorded in [`specs/010-repository-migration/spec.md`](specs/010-repository-migration/spec.md) and noted at the top of the 006 boundary contract.
- `isanlp_rst` is not a protected name. The RST provider is `rdam.rst`; the console command is `rdam-rst`.
- **Persisted contract identifiers are unchanged**: `isanlp_rst.production` 2.0.0 (the ingest envelope), `isanlp_rst.parser/modernbert-v1` (the runtime contract named by the immutable release manifests), `isanlp_rst.build_provenance`, `isanlp_rst.public_surface`, the schema `$id`s, and `ISANLP_RST_ERST_CHECKPOINT`. They name contracts and stored releases, not the package. Renaming them is a separate owner ruling.
- `ontology/` stays a top-level repository directory (vendored Central distribution and the LinkML profile); only the projected `rdam/resources/framework-identities.json` ships in the wheel.
- Exactly one `workbench/`; production code never imports it (enforced by `pixi run -e default production-boundary`).

## Active roadmap

The build ordered by the owner on 2026-09-02 ("Go — archive the runs, version 6.0.0, build it all") is recorded feature by feature under `specs/007-…` to `specs/012-…`, with the running handoff in [`docs/plans/2026-09-02-machine-build.md`](docs/plans/2026-09-02-machine-build.md). Remaining: release 6.0.0 (tag, build, validate, clean-install, evidence) and, last, the repository directory rename to `Rhetorical_Discourse_Analysis_Machine` with the sibling-repo and memory-path sweep.

The promotion-evidence system (feature 008) was removed on 2026-09-02 by owner ruling: it was never requested, and it made the machine report `unavailable` for parsers that ran correctly. Capability now means one thing — the provider can run.

**Owner ruling outstanding**: whether the persisted contract identifiers above should also move to the `rdam` name.

Provider order thereafter: **SDRT → Toulmin/Walton → PDTB-if-ever**, each on workbench evidence with its own decision-closed Spec Kit feature.

### Production source ingest

Production source ingest has one public surface: `rdam.rst.ingest` — `ProductionIngestor.capabilities()`, `.prepare()`, and `.analyse()`. The accepted source forms and their availability are whatever `describe_capabilities()` reports; that call is the authority, not this file. The old format-specific parsing functions and result envelopes were removed rather than deprecated; no compatibility route remains.

The optional **`formats` extra** supplies `docling-core`, `doclang`, `markdown-it-py`, and `mdit-py-plugins`: `pip install rdam[formats]`. Core parser consumers avoid that dependency chain. `pixi install` includes `formats`; keep these dependencies outside `[project.dependencies]`.

Canonical ingest inventories source content before applying the explicit `AUTHORED_PROSE_V1` relevance policy. Authored prose reaches the RST parser; tables, code, machine descriptions, furniture, and other non-prose remain traceable side channels unless a future named policy explicitly changes their role. Every decision is represented in the preparation receipt, source anchors survive into the analysis, long or structured material uses the governed subdivision/stitching path, and persistent cache identity includes the complete analytical pipeline fingerprint.

Format code beneath `rdam.rst.doclang` and `rdam.rst.markdown` is private decoding support for the canonical service. Docling JSON is loaded directly with current `docling-core`. There is no independent format mapper, result schema, cache, or public entry point.

Quality measurement: `pixi run rst-diag <paths>` ([`scripts/rst_diag.py`](scripts/rst_diag.py)) — preparation coverage, content-class decisions, anchor integrity, tree structure, relation distribution, subdivision, and timing across the canonical source forms.

Project memory at [`.claude/memory/MEMORY.md`](.claude/memory/MEMORY.md) tracks verified facts (spec citations, fixture evidence) and open design questions.

## Files worth knowing

- [`rdam/machine.py`](rdam/machine.py), [`rdam/contracts.py`](rdam/contracts.py) — the machine and its typed contracts.
- [`rdam/rst/parser.py`](rdam/rst/parser.py) — RST public entry point; production families are DMRST and UniRST, loaded from an immutable local release or HF version.
- [`rdam/rst/provider.py`](rdam/rst/provider.py) — the machine-facing RST/eRST adapter: capability from whether the configured parser can run; the ingest outcome envelope is handed to the machine verbatim.
- [`rdam/rst/cli.py`](rdam/rst/cli.py) — the `rdam-rst` command (parse, capabilities, serve, version).
- [`rdam/rst/parser_annotator.py`](rdam/rst/parser_annotator.py), [`rdam/rst/universal_parser/`](rdam/rst/universal_parser/) — DMRST and UniRST production parser implementations.
- [`rdam/rst/annotation_rst.py`](rdam/rst/annotation_rst.py) — native `DiscourseUnit` and RS3 XML serialization.
- [`rdam/rst/ingest/`](rdam/rst/ingest/) — sole production source inventory, preparation, analysis, receipt, subdivision, and cache API.
- [`rdam/rst/contracts/`](rdam/rst/contracts/) — typed contracts: `RstAnalysis`, `RstDocument`, `SecondaryRelationEdge`, `DiscourseSignal`, envelope serializations.
- [`rdam/rst/erst/`](rdam/rst/erst/) — Extended RST (eRST): RS4 reader/writer, typed signals, complete candidates, and formally constrained `ErstSecondaryEdgeDecoder`.
- [`rdam/rst/model_loading/release.py`](rdam/rst/model_loading/release.py) — immutable release manifests, and the manifest-bound `CompatibilityRedeclaration` sidecar by which a stored release is shown to run under a later package line.
- [`rdam/rst/hierarchical/stitcher.py`](rdam/rst/hierarchical/stitcher.py) — `HierarchicalSectionStitcher`: two-stage hierarchical section/macro tree stitching for long documents.
- [`rdam/rst/rstviewer/`](rdam/rst/rstviewer/) — visualizer and HTML/PNG export engine.
- [`rdam/dung/`](rdam/dung/) — Dung semantics (`semantics.py`) and provider; exact and deterministic, so available whenever imported.
- [`rdam/ibis/`](rdam/ibis/) — gIBIS link grammar (`grammar.py`) and provider; same.
- [`ontology/`](ontology/) — vendored Central distribution (read-only, `vendor/central-configs/`) and the `rdam` LinkML application profile binding techniques to `coe:` framework identities; `pixi run ontology-validate`.
- [`tools/production_boundary/`](tools/production_boundary/) — boundary inspection, reproducible build, artifact validation, clean install, and the classified `rst-baseline` comparison; every tool derives name and version from `pyproject.toml` (`identity.py`).
- [`workbench/`](workbench/) — offline workbench: corpus ingestion, training recipes, Parseval evaluation, model-store release tooling (`workbench/promotion/`), and the central audit ledger (`workbench/experiments/central_ledger.jsonl`).
- [`docs/metrics/UniRST_Metrics.md`](docs/metrics/UniRST_Metrics.md) — per-corpus metrics for the archived multilingual research model.

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
| `rdam` | the machine: provider and formalism declarations, capability states, native results, `Machine.prepare()` and `Machine.analyse()`, unified CLI and optional HTTP |
| `rdam.ingest` | shared source inventory, provider-specific projections, capacity planning, speaker evidence and anchors |
| `rdam.rst` | RST: DMRST and UniRST discourse parsers (Steve's evolution of Elena Chistova's IsaNLP RST Parser), viewer, and the machine adapter `rdam.rst.provider.RstProvider` |
| `rdam.pdtb` | PDTB-3 binary relations with exact source spans, all seven relation types, signal evidence, canonical senses |
| `rdam.sdrt` | SDRS graphs with EDUs, CDUs, coordinating/subordinating relations, deterministic graph and right-frontier validation |
| `rdam.toulmin` | complete Toulmin layouts with claim, grounds, warrant and optional qualifiers |
| `rdam.walton` | Walton scheme instances with exact premise roles and critical-question states |
| `rdam.dung` | Dung abstract argumentation: grounded, complete, preferred and stable semantics over a supplied or explicitly derived framework |
| `rdam.ibis` | IBIS: issue–position–argument structures validated under the gIBIS link grammar |
| `rdam.concepts` | exact lexical links from source surfaces to Central's semantic resources (labels and typed terms); never semantic acceptance |

The machine analyses discourse; it never generates or rewrites it. It serves one person on
one local machine. `rdam.production_machine()` is the supported composition of all seven
provider boundaries; each provider remains directly callable. eRST is workbench-only (owner
instruction 2026-09-06). What a provider can run is what `describe_capabilities()` reports;
that call is the authority, not this file.

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
  daily work (`dev`, `formats`, `offline`). Every everyday task runs here without `-e`.
- **`production`**: the isolated clean-room consumer environment holding only what
  `pip install rdam` provides, installed as the editable source.

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
- **CI** (`.github/workflows/`): lint, typecheck, mdlint, the fast tests,
  `rst-format-coverage` and `rst-mutation-test` on every push; the slow suite nightly;
  `deps-compat.yml` re-tests the latest Docling Core and DocLang weekly. The model smoke is
  local-only because weights are not in git.

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

## HARD RULE: Docling and DocLang spec currency

Before changing Docling JSON loading (`_inventory_docling` in `rdam/ingest/_harvest.py`),
DocLang loading (`inventory_doclang` in `rdam/ingest/_doclang.py` and the
`rdam.ingest.doclang` decoder), format harvest, boundaries, mappers, fixtures, or docs that
describe those contracts, **verify compliance with the current Docling and DocLang specs**,
even when the task looks unrelated to a version bump. The pixi lock, the in-repo fixtures
and `.claude/memory/` are what was last shipped, not what upstream is today; stating a lock
version as "the spec" is an evidence-marking violation.

1. **Docling:** `docling-core` PyPI latest vs the `pyproject.toml` pin vs `pixi.lock`;
   fixture `DoclingDocument` `version` vs what the current `load_from_json` accepts;
   `iterate_items` and `ContentLayer` against the current `docling-core` source. Owner
   instruction 2026-10-09: "we should stay up to date with docling - always." The range is
   `>=<latest>,<3`; never cap it below the next major version.
2. **DocLang:** owner instruction 2026-10-09: "yes, track main and build track support."
   Upstream `main` latest commit vs the `doclang` git pin in `pyproject.toml` vs the fixture
   manifest commit (all three match); the current upstream `spec.md`; upstream
   `tests/data/valid` vs `tests/fixtures/doclang/` (count, names, `.dclg` extension);
   whether `validate()` still needs `doclang[schematron-saxon]`.
3. **Our envelopes:** `isanlp_rst_docling` / `isanlp_rst_doclang` `schema_version` bumps
   only when *our* result shape changes, never with an upstream package version.

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
shim for the removed format-specific functions; and the optional `formats` extra
(`docling-core`, `doclang`, `markdown-it-py`, `mdit-py-plugins`) is installed by
`pixi install` and stays outside `[project.dependencies]`.

## Shared subject-matter linking and Central_Configs

`rdam.concepts` consumes shared inventories and Central-generated terminology projections
and emits exact lexical mention evidence; see `docs/concept-linking.md`. Central_Configs
(sibling repo) is the authority. After it changes: sync `ontology/vendor/central-configs/`
(its `ontology/data/{distribution.yaml,domains,manifests}` and
`ontology/schema/{coe.linkml.yaml,modules}`), then `pixi run project-framework-identities`,
`pixi run python -m tools.ontology.project_discourse_concepts`,
`pixi run python tools/compile_concept_index.py ../Central_Configs rdam/resources/concept-index.json`,
and `pixi run ontology-validate`. `tests/concepts/test_ontology.py` recompiles from the
live sibling repo.

## Where things are

The annotated source tree is the first section of `.claude/rules/architecture.md`. Outside
`rdam/`: `ontology/` (vendored Central distribution, read-only, and the `rdam` LinkML
profile), `tools/production_boundary/` (boundary inspection, build, artifact validation,
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

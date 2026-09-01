# Research: Rhetorical Discourse Analysis Machine Architecture

**Feature**: 006 | **Date**: 2026-09-01 | **Input**: [spec.md](spec.md)

Eight decisions close every unknown the plan's Technical Context raised. Each cites the
evidence inspected in the current work; the single claim that cannot be verified before
the migration feature is marked `ASSUMED` with its verification gate.

## D1 — Name of the aggregate boundary: `machine/`

**Decision**: The machine-aggregation boundary (SC-001's "machine aggregation") is the
top-level directory `machine/`, home of the aggregate analysis contract and, later,
cross-provider orchestration.

**Rationale**: SC-001 requires machine aggregation to have exactly one named top-level
boundary, but FR-002 names only the seven technique boundaries. `machine/` states the
role directly, cannot be confused with a technique, and is not an importable name the
ecosystem uses.

**Alternatives considered**: `aggregate/` (describes the artifact, not the role);
`core/` (implies the RST provider is not core); placing the aggregate contract inside
`rst/` (violates FR-029 — it is a shared abstraction with multiple provider callers by
design, the one case where shared production ownership is justified from the start).

## D2 — Packaging mechanics for relocating `isanlp_rst` under `rst/`

**Decision**: At migration, `[tool.hatch.build.targets.wheel] packages = ["isanlp_rst"]`
becomes `packages = ["rst/isanlp_rst"]`, the sdist include list gains the new path, and
the pixi editable installs (`path = "."`, verified `pyproject.toml:110,123`) are
unchanged because `pyproject.toml` stays at the repository root. The distribution name
`isanlp_rst` and console script `isanlp-rst` are untouched.

**Rationale**: Hatchling's `packages` option ships the final path component as the
import package, so the public import name survives the physical move with a one-line
change and no shims. **ASSUMED (2026-09-01, to verify)**: hatchling maps
`rst/isanlp_rst` → importable `isanlp_rst` exactly as documented. Verification gate: the
migration feature builds the wheel, installs it in the `production` clean-room
environment, and runs `production-smoke` plus the SC-002 equivalence suite before any
other migration step is declared complete.

**Alternatives considered**: a `src/`-style layout under `rst/src/` (adds a level FR-003's
spirit rejects); a compatibility shim package re-exporting from a renamed package
(explicitly forbidden — the repo bans aliases and dual paths); leaving `isanlp_rst/` at
the top level permanently (violates FR-008's requirement that the provider live under the
`rst/` boundary).

## D3 — Project identity adoption (FR-001)

**Decision**: The identity `Rhetorical_Discourse_Analysis_Machine` is adopted at
migration time as the repository name and top-level documentation identity (README,
CLAUDE.md, AGENTS.md). The Python distribution and import name remain `isanlp_rst`,
recorded in those documents as the RST provider package and historical source project.

**Rationale**: FR-001 requires the complete project identity while FR-009 requires the
`isanlp_rst` import to survive. Renaming the repository directory is a migration-window
action (external references in sibling repos update in the same pass); renaming the
distribution would break every consumer for zero analytical gain.

**Alternatives considered**: renaming the distribution to match the machine (breaks
FR-009's preserved contract); keeping the repo name `isanlp_rst` and treating the machine
name as a docs-only alias (fails FR-001's "complete project identity").

## D4 — RST equivalence baseline for SC-002

**Decision**: Before migration, a baseline capture runs the full existing verification
surface — `pixi run test-all` (dtype-equivalence and end-to-end integration suite),
`pixi run production-api-contract`, and `pixi run smoke-full-mps` — and serialises
representative contract outputs (parser results, ingest receipts, envelope
serializations) for the supported source forms into a versioned baseline directory.
Post-migration, the identical commands re-run and outputs compare byte-equal for
serialized contracts and semantically equal for parse results, using the same equivalence
definitions `tests/test_integration.py` already encodes (topology comparison per
`.claude/rules/architecture.md`).

**Rationale**: SC-002 demands 100% of supported public operations pass equivalence
against a captured baseline. The equivalence machinery already exists and is trusted;
the baseline capture only persists what the suites already compute. No new test
framework is invented (constitution III).

**Alternatives considered**: trusting the green suite alone post-migration (fails SC-002's
"against the captured pre-migration baseline" — a suite edited during migration could
drift); golden-file snapshots of every API call (over-broad; the supported contract
surface enumerated in `contracts/rst-preservation.md` is the governed scope).

## D5 — Boundary import enforcement for SC-003

**Decision**: SC-003's automated boundary inspection extends the existing
`tools.production_boundary` inspection (pixi task `production-boundary`, verified
`pyproject.toml:113,181`) with two checks: (a) no module inside any technique boundary or
`machine/` transitively imports `workbench.*`; (b) no distributable artifact (wheel/sdist
member list) contains a `workbench/` path.

**Rationale**: the repository already owns a production-boundary inspection tool wired
into pixi and the release evidence flow; extending it is the direct design. A new
standalone checker would duplicate authority (constitution V).

**Alternatives considered**: import-linter or similar third-party contract tools (new
dependency for a check two functions express); grep-based CI scripting (weaker than
walking the real import graph the existing tool already parses).

## D6 — Ontology binding mechanics (FR-002 identity binding)

**Decision**: Feature 007 (aggregate analysis contract) vendors the Central_Configs
staged distribution under `ontology/vendor/central-configs/` and authors the consumer
application profile `ontology/schema/rdam.linkml.yaml` importing `coe.linkml`, exactly
per Central's consumer contract (Central_Configs README §"Using Central Configs from
another project", read in full this session). Capability declarations carry the
canonical identifiers from `coe:artifact/narrative/analytical_frameworks_taxonomy`
(registered and pushed at Central `f701df7`, amended context at `9c48ca6`). Binding is
identity-only: native technique inventories and result semantics are provider-owned and
are never constrained to Central's simplified vocabulary profiles (e.g. the registered
six-token Toulmin `argument_role` set is a consumer-annotation vocabulary, not this
machine's Toulmin contract).

**Rationale**: one semantic authority per fact (constitution V); every estate consumer
names the same framework by the same identifier; the identity/inventory split prevents
FR-013's forbidden flattening from re-entering through the ontology.

**Alternatives considered**: spec-local framework name strings (the drift this binding
exists to kill); constraining native contracts to Central profiles (destroys native
semantics — rejected by FR-013 and recorded in Central's own registration decision).

## D7 — Follow-on feature ordering

**Decision**: Feature order: (1) aggregate analysis contract, (2) workbench promotion
system, (3) RST provider adapter — all three specified and cross-checked before
migration (FR-025) — then (4) repository migration as its own decision-closed feature
(spec Assumptions, amended per analysis finding I1), then providers strictly on
workbench evidence in priority order Dung → IBIS → SDRT → Toulmin → Walton →
PDTB-if-ever, with cross-provider orchestration last.

**Rationale**: recorded owner rulings in spec Assumptions (2026-08-31/09-01): Dung and
IBIS are formal and deterministic (proof- and property-testable per FR-022's formal
clause); SDRT matches the owner's real transcript corpus; Toulmin/Walton are expected to
be LLM-based and need calibration evidence; PDTB adds little over the existing RST/eRST
coverage of monologue prose and its canonical corpora are LDC-licensed.

**Alternatives considered**: specifying all ten features up front (the original FR-025,
amended away — it forced unverifiable provider specs before evidence existed).

## D8 — Migration safety procedure (FR-026, SC-008)

**Decision**: The migration feature begins with a machine-checked safety state: (a) zero
live workbench processes (process listing filtered to training/evaluation entry points);
(b) an inventory of `workbench/experiments/runs/` and the central ledger reconciled —
every run directory either committed, archived, or explicitly recorded as discardable by
the owner; (c) the owner's explicit confirmation recorded in the migration feature's
evidence directory. Only then may file moves start.

**Rationale**: the hazard is live today — the working tree holds four untracked
ModernBERT run directories (20260830_190321 … 20260831_002811) and a modified
`workbench/experiments/central_ledger.jsonl` (verified via `git status` this session).
FR-026 and SC-008 make reconciliation a hard precondition, and the spec's User Story 1
makes the RST capability's safety the top priority.

**Alternatives considered**: migrating around the run directories with path-preserving
moves (silently couples migration correctness to in-flight training state); waiting for
runs to finish without an inventory (fails SC-008's "complete inventory" requirement).

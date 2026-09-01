# Evidence: Boundary Ownership Audit

**Tasks**: T004, T005 | **Contract**: [../contracts/architecture-boundaries.md](../contracts/architecture-boundaries.md)
**Criteria**: SC-001, SC-003, SC-007 | **Date**: 2026-09-01 | **Repository commit**: `28f3779`

## Top-level path ownership (T004 — SC-001)

Enumerated with `ls -d */` and `ls -p | grep -v /` from the repository root. Every path
present in the working tree is listed; none is omitted.

### Directories

| Path | Roster row | Verdict |
|---|---|---|
| `isanlp_rst/` | `rst/` — "the canonical `isanlp_rst` RST/eRST provider package" | Owned. The roster's `Exists` column reads "at migration", which describes the *boundary directory* `rst/`, not the package. The package exists now at the root and moves inside `rst/` at migration (plan.md §Source Code). One owner. |
| `workbench/` | `workbench/` | Owned |
| `tests/` | `tests/` | Owned — see two-owner resolution below |
| `tools/` | `tools/` | Owned |
| `specs/` | `specs/` | Owned |
| `scripts/` | `scripts/`, `docs/`, `models/` | Owned |
| `docs/` | `scripts/`, `docs/`, `models/` | Owned |
| `models/` | `scripts/`, `docs/`, `models/` | Owned |
| `config/` | **none** | **Defect — resolved below** |
| `dist/` | **none** | **Defect — resolved below** |
| `examples/` | **none** | **Defect — resolved below** |
| `graphify-out/` | **none** | **Defect — resolved below** |

### Root files

| Path | Roster row | Verdict |
|---|---|---|
| `pyproject.toml`, `pixi.lock`, `MANIFEST.in`, `LICENSE`, `LICENSE_MODELS`, `README.md`, `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `cleanup.sh` | **none** | **Defect — resolved below** |

### Technique boundary directories (SC-007)

Checked individually: `rst`, `pdtb`, `sdrt`, `toulmin`, `walton`, `dung`, `ibis`,
`machine`, `ontology` — **all nine absent**. SC-007 ("zero technique directories exist
before their technique's first promotion", FR-002) holds unconditionally today: not one
approved boundary name has been created speculatively.

## Two-owner resolution: `tests/offline/research` (analysis finding I2)

`tests/offline/research/` exists and contains six modules (`test_contracts.py`,
`test_systems.py`, `test_technology.py`, `test_runner.py`,
`test_comparison_foundations.py`, `__init__.py`), driven by the dedicated pixi task
`research-test = "pytest tests/offline/research -q"` (`pyproject.toml:185`) with its own
lint task `research-lint = "ruff check workbench/research tests/offline/research"`
(`:186`) that pairs it with `workbench/research`.

Two roster rows could claim it: `tests/` ("production verification") and `workbench/`
("all … experiments, evaluation, benchmarks"). It is workbench-evaluation material
physically located under `tests/`.

**Ruling**: `tests/` owns the path. FR-007 requires production verification to be *kept
distinct from* workbench evaluation, not to be the only thing under `tests/`; the
distinction is satisfied within `tests/` by the subtree split and by the separate
`research-test` / `research-lint` tasks, which never run as part of `pixi run test`
(`test = "pytest -m 'not slow and not stress' -q"`, `:166`, collects `tests/` under the
`testpaths` setting but the research suite carries no production gate role). Ownership is
therefore unambiguous: one owner, `tests/`, with an internal distinction that FR-007
explicitly allows. Recorded in the roster's `tests/` row.

## Unowned paths: resolution

Five ownership gaps were found. The roster was written as the *target* layout and simply
omitted paths that exist today. All five are resolved by extending the roster — the
alternative (leaving them unowned) would make SC-001's "every owner named, none
ambiguous" false on its face.

| Path | What it actually is (verified) | Assigned owner |
|---|---|---|
| `config/` | Four tracked files: `config/erst/gum-v12.1.0-raw-relations.json`, `config/erst/tokenizer-compatibility.json`, `config/ontology/central.lock.yaml`, `config/ontology/discourse.linkml.yaml` — production configuration data read by the RST/eRST provider and the ontology lock. | New roster row `config/` |
| `dist/` | Two tracked files under `dist/5.0.0/`: the 5.0.0 wheel and sdist, referenced by four pixi tasks (`pyproject.toml:115-116`, `:196`). Deliberately committed, deliberately not gitignored. | New roster row `dist/` |
| `examples/` | Four tracked files: sample `.rs3` inputs and rendered `.png` outputs used as documentation illustrations. | Folded into the `docs/` row |
| `graphify-out/` | 486 tracked files: a generated knowledge-graph artifact set (`graph.json`, `graph.html`, `GRAPH_REPORT.md`, `cache/`, `cost.json`) produced by the `graphify` tooling. Not production code, not workbench experimentation. | New roster row `graphify-out/` |
| Root files | Packaging and lock (`pyproject.toml`, `pixi.lock`, `MANIFEST.in`), licensing (`LICENSE`, `LICENSE_MODELS`), documentation and agent instructions (`README.md`, `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`), and one operational script (`cleanup.sh`). | New roster row "repository root files" |

With these rows added, **100% of top-level repository paths map to exactly one roster
row, and no path has two candidate owners** — SC-001 demonstrated for the current tree.

## `production-boundary` gate state (T005 — SC-003)

Command: `pixi run -e default production-boundary`
(`python -m tools.production_boundary --root .`, `pyproject.toml:181`).

The `-e` flag is required: the bare form fails with
`the task 'production-boundary' is ambiguous` because the task is defined in the
`default`, `production`, and `offline` environments.

Output:

```json
{
  "artifact_receipts": [],
  "elapsed_ms": 1742.5260419840924,
  "production_modules": 92,
  "scanned_files": 321,
  "valid": true,
  "violations": []
}
```

**PASS** — zero violations across 321 scanned files and 92 production modules.

### Declared gap: research decision D5 is not yet implemented

The contract's §"Import and distribution rules (SC-003)" clause 3 states that
`tools.production_boundary` "is extended with both checks (research D5)". As of this
audit that extension **does not exist**. The two checks named by D5 —

1. no module inside a technique boundary or `machine/` imports `workbench.*`, directly or
   transitively (FR-006);
2. no distributable artifact (wheel or sdist member) contains a `workbench/` path (FR-006);

— are **acceptance items of the aggregate-contract feature (007), not of feature 006**,
and are not implemented today. The `valid: true` result above therefore certifies the
inspection's *current* rule set only. It must not be read as evidence that the
workbench-import or distributable-member rules hold; feature 006 makes no such claim.
Note also that `artifact_receipts` is empty in this run because no `--artifact` /
`--release-dir` argument was passed — artifact inspection is available today via
`production-artifacts` (`pyproject.toml:115`) but covers packaging validity, not the D5
`workbench/`-member rule.

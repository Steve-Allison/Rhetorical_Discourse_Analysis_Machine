# Feature 010: Repository Migration

**Status**: relocation implemented 2026-09-02; identity adoption recorded below | **Authority**: [006 spec](../006-rhetorical-discourse-machine/spec.md) FR-001, FR-008, FR-009, FR-011, FR-026; [rst-preservation contract](../006-rhetorical-discourse-machine/contracts/rst-preservation.md); [006 research D2, D3, D8](../006-rhetorical-discourse-machine/research.md) | **Owner ruling**: "Go — archive the runs, version 6.0.0, build it all" (2026-09-02)

## Safety precondition (FR-026, SC-008)

Recorded in [evidence/migration-safety-state.md](evidence/migration-safety-state.md):
zero live protected processes; nine run directories archived under
`workbench/experiments/archive/runs/`, three empty ones removed; ledger intact; owner
confirmation dated 2026-09-02.

## Relocation (FR-008, FR-009; research D2)

| Step | Artifact | Proof |
|---|---|---|
| Baseline capture before any move | `tools/production_boundary/rst_baseline.py` (`pixi run rst-baseline capture`) wrote nine serialized records — capabilities, `prepare` for all six source forms, CPU `analyse` for text and EDUs on `modernbert-v1-a52b70fbc1a3` — with their semantic digests to [evidence/baseline/](evidence/baseline/) | files committed |
| `isanlp_rst/` → `rst/isanlp_rst/` | `git mv` (109 renames); root `pyproject.toml` `packages = ["rst/isanlp_rst"]`, sdist include; `MANIFEST.in`; pyright/ruff scopes; ownership authority (the `rst` boundary rule owns both packages); import walker (`rst/isanlp_rst/x.py` is module `isanlp_rst.x`); build tool derives the provenance location from `pyproject` | boundary inspection `valid: true`, 101 production modules |
| Post-migration comparison | `pixi run rst-baseline compare` | **`equivalent: true`** — all nine digests byte-equal |
| Tools that hard-coded the package's repository path now derive it | `public_surface.py`, `schemas.py` locate resources from the installed package; `build.py` reads the wheel package directory from `pyproject` | `production-api-contract` 247 passed |

### Defects the move surfaced and fixed forward

1. **The Central ontology lock was resolved through a repository path.**
   `isanlp_rst/ontology/loader.py` computed `<package>/../../config/ontology/central.lock.yaml`.
   No installed copy of the package ever had that file; the move made 21 tests fail in
   the checkout too. The lock and its LinkML schema are now package resources
   (`rst/isanlp_rst/ontology/`), resolved with `importlib.resources`.
2. **The baseline's DocLang-archive record was not reproducible.** The acceptance
   fixture builder wrote ZIP entries with wall-clock timestamps, so the archive's byte
   identity — and every digest derived from it — changed per run. The prepared content
   was identical (field-level diff: only `byte_identity`, `source_id`,
   `artifact_identity`, and the digests over them differed). `_archive_bytes` now uses
   fixed entry timestamps, and that one baseline record was **re-captured from the
   pre-migration commit** (`17fb5ce`, in a git worktree, importing the pre-move package)
   so the baseline was never edited to match post-migration output.

## Packaging gate (research D2 `ASSUMED`)

Discharged by `build-production` → `validate-production-artifacts` →
`production-clean-install` on the relocated tree; results in [evidence/gates.md](evidence/gates.md).

## Identity adoption (FR-001; research D3)

Performed as the final step of the build, after release 6.0.0, because renaming the
working directory invalidates the running session's tooling paths (pixi environment
shebangs, hook paths, per-project memory key). See [evidence/identity-adoption.md](evidence/identity-adoption.md).

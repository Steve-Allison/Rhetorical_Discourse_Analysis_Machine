# Feature 010: Repository Migration

**Status**: relocation implemented 2026-09-02; single-package restructure and rename to `rdam` 6.0.0 implemented 2026-09-02 (§below); identity adoption recorded below | **Authority**: [006 spec](../006-rhetorical-discourse-machine/spec.md) FR-001, FR-008, FR-009, FR-011, FR-026; [rst-preservation contract](../006-rhetorical-discourse-machine/contracts/rst-preservation.md); [006 research D2, D3, D8](../006-rhetorical-discourse-machine/research.md) | **Owner ruling**: "Go — archive the runs, version 6.0.0, build it all" (2026-09-02)

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

## Single package and rename to `rdam` 6.0.0 (owner rulings, 2026-09-02)

After the relocation the owner ruled on the layout, superseding the 006 boundary roster
(one flat top-level directory per technique) and the earlier import-name plan:

> "We need a single folder with ALL PRODUCTION techniques (RST, Walton, etc) as sub
> folders under that so we can package them all up ready for dist/ and the wheel." —
> "We do not need to protect the name `isanlp_rst` — just call it RST." — "Why would we
> use both rdam AND production/?" — "rdam is fine for the root folder."

| Change | Artifact | Proof |
|---|---|---|
| One production package, one wheel | `rdam/` at the repository root: `rdam` (machine), `rdam/rst` (was `rst/isanlp_rst` + `rst/rdam_rst/provider.py`), `rdam/dung` (was `dung/rdam_dung`), `rdam/ibis` (new); the per-boundary `pyproject.toml`s removed; root `pyproject.toml` declares distribution `rdam` 6.0.0, `import-names = ["rdam"]`, console script `rdam-rst`, wheel `packages = ["rdam"]` | `production-boundary` `valid: true` in both environments, 106 production modules; `production-import-check` valid |
| `ontology/` stays a repository directory | vendored Central distribution and the LinkML profile are not shipped; the packaged projection `rdam/resources/framework-identities.json` is | `ontology-validate` green |
| Package-named identifiers renamed | import name, distribution, `PACKAGE_NAME`/`TOOL_NAME`, provider ids `rdam.rst/<release>`, `rdam.dung/…`, `rdam.ibis/…`, packaged-component release id `rdam-<version>`, the validator distribution recorded for built-in source forms | fast suite 933 passed |
| Persisted contract identifiers kept | `isanlp_rst.production` 2.0.0, `isanlp_rst.parser/modernbert-v1`, `isanlp_rst.build_provenance`, `isanlp_rst.public_surface`, schema `$id`s, `ISANLP_RST_ERST_CHECKPOINT` — they name contracts and immutable release manifests, not the package. **Owner ruling needed** before any of them moves | `INGEST_SCHEMA_NAME` test |
| Release tooling derives identity, restates nothing | `tools/production_boundary/identity.py` reads name, version, and package directory from `pyproject.toml`; build, artifact validation, clean install (expected version from the wheel filename), installed acceptance, import check, and the ownership authority use it; dead 5.0.0 release-receipt models removed | `tests/production_boundary` (fixture project versioned `7.7.7` to prove derivation) |
| Stored releases run under 6.0.0 without touching their manifests | both manifests declare `>=5.0.0,<6.0.0`; a manifest-bound `CompatibilityRedeclaration` sidecar (`<store>/<release_id>.compatibility.json`, `pixi run redeclare-compatibility`) records the evidence and the loader honours it only for that manifest digest | `tests/offline/test_model_promotion.py::test_compatibility_redeclaration_*`; smoke 43 passed |
| RST preservation across the rename | `rst-baseline compare` now classifies every field-level difference (execution, package identity, package source identity, derived digest, analytical). Against the pre-migration baseline: **analytically equivalent, zero analytical differences**; the non-analytical classes are exactly the package's version and name, the digests and sizes of its own source files (which the rename changed), and the digests derived from them | [evidence/release/rename-6.0.0-baseline-comparison.json](evidence/release/rename-6.0.0-baseline-comparison.json) |
| Dung and IBIS re-bound to their new source | `rdam.dung-exhaustive-subset-v1-replace-2026-09-02` (replace) and `rdam.ibis-gibis-grammar-v1-promote-2026-09-02` (promote), recorded in `workbench/promotions/` and packaged | `Machine([DungProvider(), IbisProvider()]).capabilities()` both `available` |

## Packaging gate (research D2 `ASSUMED`)

Discharged by `build-production` → `validate-production-artifacts` →
`production-clean-install` on the relocated tree; results in [evidence/gates.md](evidence/gates.md).

## Identity adoption (FR-001; research D3)

Performed as the final step of the build, after release 6.0.0, because renaming the
working directory invalidates the running session's tooling paths (pixi environment
shebangs, hook paths, per-project memory key). See [evidence/identity-adoption.md](evidence/identity-adoption.md).

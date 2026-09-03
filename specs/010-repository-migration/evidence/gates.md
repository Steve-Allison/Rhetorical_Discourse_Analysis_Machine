# Feature 010 — release 6.0.0 gate results (2026-09-02)

Release commit `d4d59c0`, tag `v6.0.0` (`v5.0.0` at `cc64f81` untouched). Every tool below
derived the name `rdam` and the version `6.0.0` from `pyproject.toml`.

| Gate | Command | Result |
|---|---|---|
| Reproducible double build | `pixi run build-production` | wheel `rdam-6.0.0-py3-none-any.whl` sha256 `76433f57…49b22` (534 949 bytes), sdist `rdam-6.0.0.tar.gz` sha256 `68c32bbb…bb16d` (479 206 bytes); two independent via-sdist builds byte-identical; `source_tag: v6.0.0`; records [release/source-release.json](release/source-release.json), [release/reproducible-build.json](release/reproducible-build.json) |
| Published pair validation | `pixi run validate-production-artifacts` | `valid: true`: RECORD verified, metadata `rdam 6.0.0`, `Requires-Python >=3.14`, `rdam-rst` entry point, `rdam/py.typed`, packaged provenance (`package_name: rdam`, `source_commit: d4d59c0…`), public surface, schemas; 0 boundary violations, 337 files scanned |
| Wheel membership | `unzip -l` | 135 members, all under `rdam/` or `rdam-6.0.0.dist-info/`. Recorded as built on 2026-09-02; the two `resources/promotion-decision.json` members it then carried were removed later the same day with the promotion system, so a rebuild yields 133. |
| Production-environment artifact gate | `pixi run -e production production-artifacts` | `valid: true`, `forbidden_members: []` for both artifacts |
| Clean-install certification | `pixi run -e production production-clean-install` (full, release `modernbert-v1-a52b70fbc1a3`, CPU, network disabled) | `valid: true` in both fresh venvs. **core**: installed `rdam 6.0.0` from the wheel outside the checkout, `pip check` passed, 202 public-surface entries importable, text and EDUs available and the four optional forms typed-unavailable, installed analysis 4 loaded-component receipts, 7 validation checks, CLI/Python semantic parity. **formats**: all six source forms available, same analysis receipts and parity |
| RST preservation across the rename | `pixi run rst-baseline compare --baseline specs/010-repository-migration/evidence/baseline` | analytically equivalent, zero analytical differences ([release/rename-6.0.0-baseline-comparison.json](release/rename-6.0.0-baseline-comparison.json)) |
| Source gates at the release commit | `pixi run lint`, `pixi run typecheck`, `pixi run test`, `pixi run mdlint`, `pixi run -e default production-boundary`, `pixi run -e production production-import-check`, `pixi run ontology-validate`, `pixi run smoke` | ruff clean; pyright strict 0 errors; 933 passed; 142 Markdown files 0 issues; boundary `valid: true` (106 production modules) in both environments; import check valid; LinkML profile, bindings, and projection current; smoke 43 passed on CPU and MPS |

## Current convergence verification (2026-09-03)

This section validates Feature 010's current contracts and mechanisms. It does not
regenerate, retag, or represent the current checkout as the historical 6.0.0 release.

| Gate | Observed result |
|---|---|
| Identity red phase | New contradictory-metadata cases produced 10 failures and 2 passes before `read_release_identity` was hardened. |
| Focused identity and boundary regression | 35 passed in 2.01 seconds after the implementation and affected fixture correction. |
| Production API contract | 391 passed in 17.95 seconds. |
| Production-boundary mechanisms | `tests/production_boundary`: 31 passed in 3.97 seconds, including reproducible-build, artifact-validation, installed-acceptance, identity, and preservation-tool tests. |
| Historical preservation and causal comparator | `tests/production_boundary/test_rst_baseline.py`: 6 passed in 0.14 seconds; all nine immutable migration records are present, zero historical analytical differences are reported, and causal analytical mutation is classified `analytical`. |
| Source boundary | Default and production environments each reported `valid: true`, 137 production modules/files, and zero violations. |
| Editable import check | Default and production environments each reported `valid: true`, 13 distribution members, and `editable_source: true`; this is explicitly not wheel certification. |
| Ruff | `All checks passed!` |
| Strict Pyright | 0 errors, 0 warnings, 0 information messages. |
| Markdown | 194 files linted, 43 governed exclusions, 0 issues. |
| Ontology | Exit 0; schema and bindings validated and the framework projection matched its vendored authority. The configured ignored `_meta` naming warning remained visible. |
| Fast suite | 1,317 passed and 134 deselected in 33.88 seconds. |
| Complete suite | 1,395 passed and 56 skipped in 239.81 seconds. |

A present-day baseline replay was deliberately rejected as migration proof. ModernBERT
is no longer a production family, and current Docling, DocLang, Markdown, and source
identity records are not the historical migration inputs. The failed exploratory replay
therefore caused no evidence mutation; the immutable comparison above remains the
authoritative preservation record.

# RDAM documentation guide

Current usage is described by the [root README](../README.md),
[production API contract](production-api-contract.md),
[source ingest guide](production-source-ingest.md), and
[package/workbench boundary](production-offline-boundary.md).
The [Feature 019 quickstart](../specs/019-unified-machine-interfaces/quickstart.md)
contains runnable unified CLI, Python and HTTP examples.

## Implementation authority

| Subject | Current source |
|---|---|
| Package version, dependencies, extras and Pixi tasks | [pyproject.toml](../pyproject.toml) |
| Public Python imports | [rdam/__init__.py](../rdam/__init__.py) |
| Provider composition and defaults | [composition.py](../rdam/composition.py), [configuration.py](../rdam/configuration.py) |
| CLI commands and flags | [cli.py](../rdam/cli.py); `pixi run rdam --help` |
| Loopback routes and request limits | [http.py](../rdam/http.py) |
| Persisted machine versions and schemas | [serialization.py](../rdam/serialization.py); `pixi run rdam version` |
| Nested ingest versions | [contracts/base.py](../rdam/ingest/contracts/base.py) |
| Canonical ontology authority | Central_Configs; generated consumer resources in [rdam/resources](../rdam/resources/) |
| Current production verification | [Feature 019 tasks](../specs/019-unified-machine-interfaces/tasks.md) |

Seven technique boundaries are implemented: RST, PDTB, SDRT, Toulmin, Walton,
Dung and IBIS. Dung and IBIS consume supplied structures. eRST is retained in
[the workbench](../workbench/erst/README.md) for testing and evaluation, excluded
from production by owner instruction on 2026-09-06. Code presence,
capability discovery and successful inference are separate facts.

## Reading historical material

`specs/` preserves approved requirements, plans, implementation ledgers and dated
acceptance evidence. Requirements remain requirements unless explicitly superseded;
old execution results describe their named commit or checkpoint. Neither a checked
box nor a historical benchmark certifies today's checkout. Feature 019 supplies
the unified interface; features 017 and 018 supply source and runtime foundations.

Features 001–005 and the dated proposals in `docs/plans/` describe earlier parser,
format and release designs. Their `isanlp_rst` imports, format-specific parse
functions, ModernBERT production proposals, old command names and release ceremonies
are historical. Use the current guides above for execution. Feature 006's original
multi-package layout was superseded by the single `rdam` package in Feature 010.
Features 013–016 retain native technique definitions; later integrity/version
corrections are recorded in Feature 019 and the generated native schemas.

The forensic reports, `artifacts/reviews/`, `docs/metrics/`, and feature `evidence/`
files retain dated findings and measurements. A recorded defect may have been
repaired since its audit. Project notes in `.claude/memory/` retain original
investigations and decisions with current-status notices. Their old source line
numbers are historical citations, not current file locations.

Agent rules, Spec Kit templates and installed skills govern work; they are not
runtime feature claims. Generated Graphify files are navigation aids, not release
proof. Test `.md`/`.txt` inputs and vendored upstream material are data, not usage
documentation; their contents must retain source fidelity.

## Local deliverables

The local wheel and sdist are in `dist/6.0.0/`. They are ignored outputs, not an
external publication. A remote Git install can differ from the local package.
The standard source builder requires a clean checkout; it cannot certify
uncommitted changes merely because an older tag exists.

The current local five-text-technique report is
`build/production-verification-2026-09-06/verified-production-report.json`.
All-seven structured-input transport results are in the same directory.
The original report remains under `build/real-document-reports/`, beside
`RDAM-remediation-plan.md`. These local paths are absent from a fresh clone and
from installed packages. Reports are JSON for AI consumption; optional terminal
summary/view commands do not require companion text or HTML reports.

Broader analytical-quality research remains distinct from production engineering.
SOTA, universal calibration and complete held-out validation have not been
established. Dependency currency and the unverified Docling Core 2.95.0 gap are
recorded in the [source ingest guide](production-source-ingest.md).

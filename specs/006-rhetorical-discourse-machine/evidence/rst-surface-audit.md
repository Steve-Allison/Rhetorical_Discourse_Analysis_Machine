# Evidence: Current RST Preserved-Surface Audit

**Tasks**: T002, T003, T013 | **Contract**:
[../contracts/rst-preservation.md](../contracts/rst-preservation.md) | **Criterion**:
SC-002 | **Observed**: 2026-09-03 | **Starting commit**: `6fdde67`

This evidence supersedes the 2026-09-01 pre-migration audit. It was collected from the
live `rdam` package in the locked default Pixi environment after the single-package
migration. It does not claim compatibility with the removed `isanlp_rst` import; the
recorded owner ruling made `rdam.rst` the sole canonical RST package.

## Public-surface resolution

| Contract surface | Observed result | Evidence |
|---|---|---|
| Package and command | PASS | `pyproject.toml` declares project `rdam`, wheel package `rdam`, and `rdam-rst = "rdam.rst.cli:main"`; `pixi run rdam-rst version` returned `{"package":"rdam","version":"6.0.0"}`. |
| `rdam.rst` exports | PASS | Import probe resolved all 51 declared names, including `Parser`, DMRST/UniRST predictors, native contracts, RS4 support, graph projections, ontology adapter, and rendering helpers. |
| Parser façade | PASS | Probe resolved `__call__`, `analyse_document`, `complete_erst_document`, `describe_analysis_identity`, `from_edus`, `from_model_release`, `parse_document`, `parse_documents`, `parse_hierarchical`, and `parse_tree`. `Parser.AVAILABLE_FAMILIES` is DMRST and UniRST. |
| Machine provider | PASS | `rdam.rst.provider.RstProvider` declares `rst_tree` and `erst_graph` without constructing `Parser`; its tests cover configuration, provenance, formalism availability, and typed unavailability. |
| Canonical ingest | PASS | `rdam.rst.ingest` exposes 184 declared names. Capability probe reported `text`, `edus`, `markdown`, `docling_json`, `doclang_xml`, and `doclang_archive` all available. |
| Native contracts | PASS | `rdam.rst.contracts` exposes 79 declared names, including strict RST/eRST models and canonical dictionary/JSON serializers. |
| CLI/HTTP projections | PASS | `rdam.rst.cli.main` is callable; the ingest suite covers command grammar, canonical output, loopback-only HTTP, boundary error staging, and semantic parity. |

The runtime probe also confirmed that the wheel configuration contains only `rdam`.
There is no second top-level import package. Historical `isanlp_rst` values still used
inside runtime-contract names, media types, and model provenance were not counted as
public imports and were not rewritten.

## Executed checks

| Command | Observed result |
|---|---|
| Public-surface probe through `pixi run python` | PASS — package/script/wheel mapping resolved; 51 RST exports, 79 native-contract exports, 184 ingest exports, ten governed Parser operations, and six available source forms. |
| `pixi run rdam-rst version` | PASS — canonical JSON reported package `rdam`, version `6.0.0`. |
| `pixi run pytest tests/rst tests/ingest/production_ingest tests/ingest/test_doclang_fixture_parity.py tests/ingest/test_doclang_loader.py tests/ingest/test_doclang_text_walker.py tests/ingest/test_markdown_loader.py -q` | PASS — `454 passed in 25.20s`. |
| `pixi run pytest tests/integration/test_production_boundary.py -q` | PASS — `19 passed in 2.26s`. |
| `pixi run -e default production-boundary` | PASS — `valid: true`, 131 production modules/files, zero violations. |

The first boundary run exposed four `SyntaxWarning`s by parsing unrelated vendored corpus
sources under `workbench/`. The gate was corrected to parse only production modules and
to identify a `workbench` import directly from each production AST. The added regression
test places invalid syntax in an unrelated workbench file and proves the gate ignores it;
direct and transitive production-to-workbench tests remain green.

Full-project lint, type, test, and final cross-artifact results are recorded by T019 only
after every convergence task has landed. This file makes no advance claim about them.

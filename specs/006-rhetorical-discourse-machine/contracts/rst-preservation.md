# Contract: RST Preservation Across Migration

**Feature**: 006 | **Authority**: [spec.md](../spec.md) FR-008..FR-011, SC-002; [research.md](../research.md) D2, D4, D8

The existing RST/eRST capability is the machine's only established provider. Migration
is valid only if this contract holds; any breach halts migration until reconciled.

## Preserved public surface

The supported surface that must remain equivalent, byte-for-byte where serialized and
semantically where computed:

| Surface | Anchor |
|---|---|
| Public import name `isanlp_rst` and its package contents | FR-009; hatchling mapping per research D2 (verification gate applies) |
| `isanlp_rst.parser.Parser` dispatch, model versions, device and dtype behaviour | FR-011; dtype-equivalence suite in `tests/test_integration.py` |
| Canonical ingest: `isanlp_rst.ingest` — `ProductionIngestor.capabilities()/.prepare()/.analyse()`, all six declared source forms (`text`, `edus`, `markdown`, `docling_json`, `doclang_xml`, `doclang_archive`), receipts, anchors, subdivision, cache identity | FR-011; `production-api-contract` pixi task; surface verified in [evidence/rst-surface-audit.md](../evidence/rst-surface-audit.md) |
| Typed contracts under `isanlp_rst.contracts` and their envelope serializations | FR-011 serialized-contract compatibility |
| `DiscourseUnit` / RS3 serialization, eRST RS4 and signals, rstviewer exports | FR-011 result semantics and evidence semantics |
| CLI `isanlp-rst` entry point | `pyproject.toml` `[project.scripts]` unchanged |
| Failure algebra and validation rules of all of the above | FR-011 |

Trained architecture, inference mathematics, relation meanings, and model identity change
only via a separately approved and validated feature (FR-011) — never as a migration side
effect.

## Consumer obligations (US1)

1. An existing RST consumer keeps its imports and receives equivalent results with no
   code change (US1 scenario 1–2).
2. No consumer is required to adopt the aggregate result or any theory-neutral type in
   place of native RST/eRST results (US1 scenario 2, FR-013).

## Equivalence procedure (SC-002, research D4)

1. **Baseline capture (pre-migration)**: run `pixi run test-all`,
   `pixi run production-api-contract`, `pixi run smoke-full-mps`; persist serialized
   contract outputs for representative inputs across all six declared source forms into a
   versioned baseline directory recorded in the migration feature's evidence. Tasks
   defined in more than one pixi environment (`production-boundary`, `production-smoke`)
   must be invoked with an explicit `-e`; the bare form is ambiguous and fails.
2. **Post-migration comparison**: identical commands, identical inputs; serialized
   contracts compare byte-equal; parse results compare under the suite's existing
   equivalence definitions (topology per `_topology`, labels per fp32 baseline rules).
3. **Pass condition**: 100% of captured operations and contract kinds equivalent
   (SC-002). Any diff is a migration defect — fixed forward or the migration is rolled
   back; the baseline is never edited to match.
4. **Gate ordering**: the packaging verification (research D2 `ASSUMED` gate — wheel
   built, clean-room `production-smoke` green) precedes every other migration completion
   claim.

## Safety precondition (FR-026, SC-008)

Migration starts only from a recorded MigrationSafetyState: zero live protected
workbench processes, the complete run/checkpoint inventory reconciled, and the owner's
dated confirmation (research D8; the hazard is current — live untracked run directories
exist in the working tree at planning time).

# Quickstart: Validating the Machine Architecture

**Feature**: 006 | **Date**: 2026-09-01 | **Contracts**: [contracts/](contracts/)

Runnable validation per success criterion. Feature 006 itself ships governance
artifacts, so its own acceptance is documentary (V1); the remaining scenarios are the
standing validation each follow-on feature must keep green, stated here so the
architecture's success criteria are checkable from day one.

## Prerequisites

```bash
pixi install          # provision the default environment (pixi.lock)
```

## V1 — Boundary assignment is total and unambiguous (SC-001)

Review [contracts/architecture-boundaries.md](contracts/architecture-boundaries.md)
against the repository root: every top-level path resolves to exactly one boundary row;
no technique directory exists without a promoted provider.

```bash
ls -d */ | sort        # every entry must appear in the boundary roster
```

Expected: zero unlisted top-level directories; zero technique directories while their
techniques report `unavailable(no_promoted_implementation)`.

## V2 — Production never touches the workbench (SC-003)

```bash
pixi run production-boundary
```

Expected (after the research-D5 extension lands with feature 007): zero production
imports of `workbench.*` and zero workbench members in distributable artifacts, reported
by the inspection with exit 0. Until the extension lands, the existing inspection must
stay green and the extension is a feature-007 acceptance item.

## V3 — RST equivalence baseline (SC-002)

Pre-migration capture and post-migration comparison per
[contracts/rst-preservation.md](contracts/rst-preservation.md):

```bash
pixi run test-all
```

```bash
pixi run production-api-contract
```

```bash
pixi run smoke-full-mps
```

Expected: all green pre-migration (baseline capture persists serialized outputs);
identical commands green post-migration with serialized contracts byte-equal and parse
results equivalent under the suite's existing definitions. Any diff halts migration.

## V4 — Packaging identity survives relocation (FR-009; research D2 gate)

Post-relocation only:

```bash
pixi run build-production
```

```bash
pixi run -e production production-smoke
```

Expected: wheel builds with `packages = ["rst/isanlp_rst"]`, clean-room install imports
`isanlp_rst`, smoke passes. This gate discharges the research-D2 `ASSUMED` marker and
precedes every other migration completion claim.

## V5 — Capability honesty (SC-005, SC-007, SC-010)

Once the aggregate contract exists (feature 007+), its acceptance tests must
demonstrate: every success/unavailable/failed combination across providers with no
suppression of successful results; zero stubs or fabricated structures for unavailable
techniques; withholding one provider leaving every other capability declaration
byte-identical. Anchored to
[contracts/capability-declaration.md](contracts/capability-declaration.md).

## V6 — Migration safety (SC-008)

Immediately before any file move:

```bash
ps aux | grep -E "train|workbench" | grep -v grep
```

```bash
git status --porcelain workbench/
```

Expected: no protected workbench processes; every run directory and the central ledger
reconciled (committed, archived, or owner-marked discardable); the owner's dated
confirmation recorded in the migration feature's evidence directory. As of planning time
this gate is **failing by design** — four untracked run directories and a modified
ledger exist — which is precisely why FR-026 blocks migration today.

## V7 — Ontology identity binding (FR-002)

Once feature 007 vendors the distribution: every `technique_id` in capability
declarations resolves to a concept in
`ontology/vendor/central-configs/domains/narrative/analytical_frameworks.yaml`; the
consumer profile validates:

```bash
pixi run linkml validate ontology/schema/rdam.linkml.yaml
```

Expected: all seven curies resolve; profile and instances validate; no `coe:` identifier
is redefined locally.

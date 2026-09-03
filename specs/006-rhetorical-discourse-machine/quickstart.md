# Quickstart: Validating the Machine Architecture

**Feature**: 006 | **Date**: 2026-09-01 | **Contracts**: [contracts/](contracts/)

Runnable validation per success criterion for the live `rdam` package. Documentary
inspection is necessary for ownership and identity, but executable criteria require
observed tests; no checked historical task substitutes for a current result.

## Prerequisites

```bash
pixi install          # provision the default environment (pixi.lock)
```

## V1 — Boundary assignment is total and unambiguous (SC-001)

Review [contracts/architecture-boundaries.md](contracts/architecture-boundaries.md)
against the repository root and `rdam/`: every repository path has one owner and every
technique sub-package contains a real provider.

```bash
find rdam -maxdepth 1 -type d -print | sort
```

Expected: exactly seven technique sub-packages after T015, plus the shared package
modules/resources; no `production/` child and no top-level technique import package.

## V2 — Production never touches the workbench (SC-003)

```bash
pixi run -e default production-boundary
```

Expected: zero production imports of `workbench.*`, complete ownership classification,
and exit 0. Distribution membership is additionally proved by artifact validation.

## V3 — RST equivalence baseline (SC-002)

Current regression and canonical-serialization proof per
[contracts/rst-preservation.md](contracts/rst-preservation.md):

```bash
pixi run test-all
```

```bash
pixi run test
```

```bash
pixi run smoke
```

Expected: public-surface, ingest, contract, format, provider, and smoke tests pass with
canonical serialized contracts byte-equal after round-trip and parse results equal under
the suite's existing semantic assertions. Any unexplained diff fails SC-002.

## V4 — Distribution preserves the public package (FR-009)

For a distribution candidate, `dist/` is ignored build output and the package is built
from the exact release commit:

```bash
git tag v<version>
```

```bash
pixi run build-production
```

```bash
pixi run validate-production-artifacts
```

```bash
pixi run -e production production-clean-install
```

Expected: wheel and sdist build reproducibly from the one wheel package directory
`pyproject.toml` declares (`packages = ["rdam"]`; `"reproducible": true`, provenance
in both); the artifact validator
reports `valid: true`; the clean-room install pip-installs the **wheel** into fresh
`core` and `formats` venvs outside the source tree with the network disabled, imports the
package from `site-packages`, and passes full installed acceptance including CLI/Python
semantic parity. This gate discharges the research-D2 `ASSUMED` marker and precedes every
other migration completion claim.

An editable-source import check is not this gate: it cannot detect a malformed wheel.

## V5 — Capability honesty (SC-005, SC-007, SC-010)

Acceptance tests demonstrate every success/unavailable/failed combination across
providers with no suppression of successful results; zero stubs or fabricated
structures; withholding one provider leaving every unrelated capability declaration
byte-identical; and the supported production composition reporting seven available
techniques. Anchored to
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

Expected: all **eight** curies resolve — the seven technique boundaries plus `erst`,
which the RST provider serves as a declared formalism (ruling in
[data-model.md](data-model.md) §Formalism) — profile and instances
validate; no `coe:` identifier is redefined locally. All eight already resolve against
the live Central taxonomy: [evidence/identity-binding-audit.md](evidence/identity-binding-audit.md).

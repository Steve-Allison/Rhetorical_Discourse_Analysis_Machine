# Feature Specification: Repository Migration

**Feature**: `010-repository-migration`

**Created**: 2026-09-02

**Reconciled**: 2026-09-03

**Status**: Complete

## User Story 1 — Use one production distribution (Priority: P1)

As the machine owner, I install and import one `rdam` distribution whose seven production
techniques are subpackages and whose offline workbench is never shipped.

**Independent test**: Source-boundary, import, and artifact tests derive the distribution
identity from `pyproject.toml`, find exactly one wheel package root, and find no workbench
member or production import.

### Acceptance scenarios

1. `pyproject.toml` declares distribution and import identity `rdam` at version 6.0.0.
2. The wheel package list contains exactly root package `rdam`.
3. RST, PDTB, SDRT, Toulmin, Walton, Dung, and IBIS are production subpackages.
4. Repository-only ontology and `workbench/` files are absent from built artifacts.
5. Release tools derive name, version, package directory, filenames, and tag from one authority.

## User Story 2 — Preserve RST meaning across relocation (Priority: P2)

As an RST consumer, I receive analytically equivalent preparation and analysis records
after the repository/package relocation, while package-identity differences remain
explicitly classified rather than mistaken for analytical changes.

**Independent test**: The immutable 6.0.0 comparison covers the migration snapshot and
reports zero analytical differences; causal comparator tests prove that analytical
changes fail while only explicitly classified migration differences are accepted.

### Acceptance scenarios

1. Baseline records cover capabilities and preparation for text, EDUs, Markdown, Docling
   JSON, DocLang XML, and DocLang archive.
2. The historical migration record covers text and EDU analysis through the then-current
   public production API and is not presented as a current ModernBERT production run.
3. Differences are classified as execution, package identity, package source identity,
   derived digest, or analytical.
4. Any analytical difference fails comparison.
5. DocLang archive fixture bytes are reproducible for identical input.

## User Story 3 — Rebuild and install the migrated package reproducibly (Priority: P3)

As the machine owner, I can rebuild the exact source revision into a reproducible wheel
and sdist pair and validate a fresh installation outside the checkout without network
access or offline dependencies.

**Independent test**: Reproducible-build fixtures, artifact validators, and clean-install
acceptance prove derived identity, exact membership, provenance, canonical source forms,
and Python/CLI semantic parity.

### Acceptance scenarios

1. Two independent builds from one source archive produce byte-identical artifacts.
2. Wheel and sdist names derive from the declared project identity.
3. Packaged provenance identifies the exact source commit, tree, archive, and build input.
4. Clean installations resolve outside the source tree and contain no offline dependencies.
5. Core and formats installations advertise and execute only their installed capabilities.

## Requirements

- **FR-001**: The repository MUST expose exactly one production distribution and import root named `rdam`.
- **FR-002**: Every promoted technique MUST live beneath `rdam/`; `workbench/` MUST remain repository-only.
- **FR-003**: Distribution name, version, package directory, artifact names, and release tag MUST derive from `pyproject.toml`.
- **FR-004**: Public package identifiers MUST use `rdam`; immutable persisted contract identifiers MUST remain unchanged unless separately versioned.
- **FR-005**: Production code MUST NOT import offline packages or `workbench` directly or transitively.
- **FR-006**: Built artifacts MUST contain only production package members, declared metadata, licences, and required documentation.
- **FR-007**: Immutable 6.0.0 migration evidence MUST cover capabilities, all six source forms, and the historical model-backed text/EDU comparison.
- **FR-008**: Baseline comparison MUST reject every analytical difference and classify every accepted non-analytical difference.
- **FR-009**: Deterministic fixtures, including DocLang archives, MUST produce stable source bytes.
- **FR-010**: Production builds MUST start from one completely clean, exact Git revision.
- **FR-011**: Independent builds from the same source archive MUST be byte-identical.
- **FR-012**: Installed acceptance MUST run outside the checkout with external network disabled and offline distributions absent.
- **FR-013**: Core and formats installations MUST report truthful source-form capabilities and retain canonical serialization round trips.
- **FR-014**: Historical 6.0.0 release evidence MUST remain immutable; current verification MUST NOT masquerade as a new release.

## Success criteria

- **SC-001**: Boundary inspection reports zero ownership, import, dependency, and artifact violations.
- **SC-002**: Exactly one import root and one wheel package root are declared.
- **SC-003**: The historical 6.0.0 comparison reports zero analytical differences across every migration baseline record.
- **SC-004**: Reproducible-build tests observe identical wheel and sdist hashes across independent roots.
- **SC-005**: Clean-install acceptance imports zero modules from the source checkout.
- **SC-006**: Installed production environments contain zero offline-only distributions.
- **SC-007**: Applicable source, packaging, static, and complete test gates pass with observed evidence.

## Scope

This feature governs repository/package topology, migration preservation, derived release
identity, reproducible packaging, and installed acceptance. It does not change RST
inference mathematics, persisted contract names, model manifests, package version 6.0.0,
or publish artifacts to an external package index.

The original migration safety inventory remains at
[evidence/migration-safety-state.md](evidence/migration-safety-state.md). The immutable
pre-migration records remain under `evidence/baseline/`, and the historical 6.0.0 release
records remain under `evidence/release/`.

# Implementation Plan: Repository Migration

**Feature**: `010-repository-migration` | **Date**: 2026-09-03 | **Spec**: [spec.md](spec.md)

## Summary

Converge the historical migration record onto the live one-package `rdam` repository,
verify that all release identity is derived from `pyproject.toml`, validate the recorded
historical RST migration and its comparison logic, and certify source/artifact boundaries
without changing inference behaviour or manufacturing a new 6.0.0 release.

## Technical Context

**Language/Version**: Python 3.14

**Primary Dependencies**: Hatchling, `build`, Pydantic 2, RFC 8785, packaging, Pixi

**Storage**: Git-tracked canonical JSON baseline and historical release evidence; ignored build artifacts

**Testing**: pytest through Pixi, reproducible-build fixtures, baseline comparator, source/artifact boundary tools

**Target Platform**: One local macOS machine; clean consumer venvs for artifact acceptance

**Project Type**: One Python library/CLI distribution

**Performance Goals**: Boundary and identity checks remain linear in repository/artifact members

**Constraints**: No package-index publication; no 6.0.0 retagging; no contract identifier rename;
no trained-model or inference changes; production remains independent of offline dependencies

**Scale/Scope**: One package root, seven technique boundaries, six source forms, one wheel/sdist pair

## Constitution Check

- **Evidence before claims**: current topology and gates are inspected; historical release
  evidence is labelled historical and not projected onto the current commit.
- **One production quality bar**: changed Python, if any, must pass Ruff and strict Pyright
  without suppression.
- **Solo-local simplicity**: direct filesystem/Git/build tools remain; no registry,
  deployment service, or team release workflow is introduced.
- **Honest verification**: real internal build and comparator code is exercised; the
  removed ModernBERT production family and superseded format snapshots are claimed only
  from immutable historical migration evidence.
- **Canonical contracts**: `pyproject.toml`, production contracts, and immutable baseline
  records remain their single authorities.

Pre-design and post-design result: **PASS**, with no justified exceptions.

## Project Structure

```text
rdam/                              # only production package root
├── rst/
├── pdtb/
├── sdrt/
├── toulmin/
├── walton/
├── dung/
└── ibis/

workbench/                         # repository-only offline work
tools/production_boundary/         # identity, build, artifact, import, install checks
tests/production_boundary/         # migration and packaging contract tests
specs/010-repository-migration/    # immutable baseline plus current design/evidence
```

**Structure Decision**: Retain the live root `rdam` package and repository-only
`workbench`; no compatibility package or second distribution is created.

## Complexity Tracking

No constitution violation or additional subsystem is required.

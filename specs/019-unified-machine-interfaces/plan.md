# Implementation Plan: Unified Machine Interfaces

**Git branch**: `master` (unchanged) | **Date**: 2026-09-04
**Feature**: `019-unified-machine-interfaces` | **Spec**: [spec.md](spec.md)

**Status**: Implementation plan; no production implementation performed.
Spec Kit's BRANCH field identifies the feature, not a newly created Git branch.

## Summary

One configured Machine serves Python, the unified `rdam` CLI and optional local
HTTP. Shared contracts own source preparation, explicit technique selection,
versioned canonical output, completion, configuration and errors. Native results
remain distinct; interfaces do not implement analysis.

The owner's latest direction adds native integrity repairs as prerequisites:
complete Walton assessments, source-backed Toulmin warrant origin, typed
provider-selected evidence alignment, and honest historical/version/cache behavior.
The AI reading guide explains corrected results; it must not become a workaround
for defective data. See [native-integrity.md](contracts/native-integrity.md).

World-class is the floor for every planning, implementation, testing and delivery
artifact, not a late polishing phase. Use native regression tests, interface parity,
focused real-model checks and a cold-critic agent as specified in
[analytical-quality.md](contracts/analytical-quality.md). No annotation workflow or
bespoke evaluation framework blocks implementation.

## Technical Context

**Language/Version**: Python >=3.14; existing strict typing and Pydantic contracts.
**Primary Dependencies**: Existing inference/serialization stack; stdlib argparse
for CLI; optional Starlette/Uvicorn ranges recorded in research.md, resolved and
tested through Pixi during implementation.
**Storage**: Explicit input/output files and existing optional result cache.
No database, server result store or job queue.
**Testing**: Existing pytest/Pixi tasks; new native-regression and installed
interface suites; real internal code, external-boundary model fixtures only.
Focused real-model cases and a cold critic check source support and analytical
meaning alongside executable contract tests.
**Target Platform**: Solo-local macOS, preserving supported CPU/MPS/CUDA behavior.
**Project Type**: One Python distribution with two primary interfaces and optional HTTP.
**Performance Goals**: One inventory pass per invocation; one projection per
distinct requirement; zero inference/model/network work for discovery, preparation
or saved-record views. No invented inference-latency or universal context-fit claim.
**Constraints**: Seven native boundaries, six source forms; no trained-architecture
changes, secrets in records, implicit retries, compatibility command or service
architecture. Preserve default/production Pixi environment separation.
**Scale/Scope**: One person, one machine, one process; one admitted HTTP POST at a
time, fixed configuration, explicit bounded request body handling.

## Constitution Check

| Principle | Pre-design / post-design disposition |
|---|---|
| Evidence before claims | Source observations and diagnostic output recorded in research.md/native-integrity.md; proposed behavior is not described as implemented. |
| One production quality bar | Every artifact must meet its intended purpose from its first version; known defects are repaired, not excused by aggregate scores or deferred polishing. |
| Solo-local simplicity and full scope | One package/machine; Python, CLI, HTTP and AI use all included; no deployment platform or release ceremony. |
| Honest verification | Real providers, installed subprocess/loopback tests, focused model cases and cold critique; report actual failures and fix them. |
| Canonical/current contracts | Models generate schemas; native/evidence version changes are explicit; historical identities remain historical; upstream format preflight precedes relevant source edits. |

No constitution exception is requested. Implementation must recheck these
conditions against the resulting code; a design check is not runtime certification.

## Design artifacts and authority

- [spec.md](spec.md): owner outcomes, FR-001–FR-038, SC-001–SC-013.
- [research.md](research.md): inspected baseline, alternatives and decisions D1–D13.
- [data-model.md](data-model.md): public record/configuration identities and invariants.
- [Python](contracts/python-api.md), [CLI](contracts/cli.md),
  [HTTP](contracts/http.md): transport and public-operation contracts.
- [AI usage](contracts/ai-usage.md): inline interpretation and loss-declared selection.
- [Native integrity](contracts/native-integrity.md): mandatory producing-boundary fixes.
- [Analytical quality](contracts/analytical-quality.md): focused semantic tests, cold critique
  and defect correction.
- [Acceptance matrix](contracts/acceptance-matrix.md): scenarios and expected evidence.
- [quickstart.md](quickstart.md): proposed installed validation workflow.
- [tasks.md](tasks.md): ordered implementation work; all tasks start unchecked.

Runtime models remain the implementation authority. Documentation specifies the
change; generated schema/public-surface artifacts must be regenerated, not
hand-edited into a second authority.

## Implementation sequence

| Step | Files affected during implementation | Checkable success criterion |
|---|---|---|
| 1. Baseline and format preflight | Existing native tests; tests/interfaces/fixtures/; applicable source-format fixtures only if current checks require corrections | Reproduce all three defects; preserve historical fixtures; record current Docling/DocLang conformance before source-contract edits. |
| 2. Versioned contracts and configuration | rdam/contracts.py, rdam/configuration.py (new), rdam/historical.py (new), rdam/serialization.py, rdam/ingest/contracts/evidence.py (new), rdam/ingest/contracts/source.py | Strict version dispatch; binary request round trips; historical digest stability; invalid current evidence rejected. |
| 3. Shared machine operations | rdam/machine.py, rdam/composition.py, rdam/_execution.py, rdam/_result_cache.py, all seven provider.py modules | Exact requested scope/status, eRST boundary lookup, public complete preparation, effective configuration and version-safe cache keys. |
| 4. Native integrity fixes | rdam/walton/schemes.py, rdam/walton/provider.py, rdam/toulmin/argument.py, rdam/toulmin/provider.py, rdam/ingest/alignment.py, rdam/pdtb/provider.py, rdam/sdrt/provider.py | NI-01–NI-04 regression matrix passes; no omitted CQ defaulting, evidence-role invention or invalid origin claims accepted. |
| 5. AI-ready records and views | rdam/interpretation.py (new), native descriptor modules, rdam/contracts.py, rdam/summary.py (new), `rdam/__init__.py` | All present pointers resolve; guide uses corrected semantics; selected native bytes/context preserved; no inference during viewing. |
| 6. Unified CLI | rdam/cli.py (new), `rdam/__main__.py` (new), rdam/_output.py (new), rdam/rst/cli.py (remove obsolete transport), pyproject.toml | Installed entry point is rdam only; grammar/output/exit and atomic file-safety matrix passes. |
| 7. Optional HTTP parity | rdam/http.py (new), pyproject.toml (including tool.pixi tables), Pixi-generated lock | Real loopback route/framing/admission/error and canonical parity tests pass; core import/CLI works without HTTP dependencies. |
| 8. Integration and documentation | tests/interfaces/, tools/production_boundary/{schemas,public_surface,installed_acceptance}.py, generated schemas/public surface, README.md, docs/ | All acceptance rows have actual results; generated artifacts agree with installed behavior; old active CLI/API examples removed; no publication action. |
| 8a. Analytical tests and cold critique | tests/interfaces/test_model_backed.py; affected native modules | Focused real-model cases checked against source; critic findings resolved with regression tests; actual failures reported. |

Step 4 is a prerequisite for claiming Step 5 or interface analytical readiness,
not a deferred follow-up. Step 3 may be developed with contract tests before the
native fixes, but final production parity requires the corrected real providers.

## Planned source layout

```text
rdam/
  configuration.py       # closed settings, resolution and safe loading
  contracts.py           # current request/result/declaration models
  historical.py          # explicit supported v1 models/digest semantics
  serialization.py       # one registry, strict codecs and schema exports
  machine.py             # generic orchestration and preparation
  composition.py         # lazy native provider assembly
  interpretation.py      # guide types/binding and pure AnalysisView selection
  summary.py             # deterministic human-readable saved-record summary
  cli.py, __main__.py    # one argparse grammar and entry point
  _output.py             # atomic publication and safe diagnostics
  http.py                # optional ASGI adapter/server lifecycle
  ingest/
    alignment.py         # typed selected-field mapping, no arbitrary string walk
    contracts/evidence.py
  <technique>/
    provider.py          # native execution, validation and declarations
    interpretation.py    # native-owned descriptors; no inference
tests/
  interfaces/            # new shared-contract, CLI, HTTP and installed parity tests
  machine/               # source/configuration/cache/outcome regression coverage
  walton/, toulmin/      # corrected native semantics and source validation
  pdtb/, sdrt/           # exact-span/evidence-policy coverage
```

Keep generic execution independent of technique imports. Pure presentation uses
descriptors supplied by declarations, not a second provider registry/orchestrator.
Public exports must not eagerly import optional HTTP or format dependencies.

## Verification and delivery boundary

Run focused native/contract suites first, then existing lint/type checks and
applicable full tests. Build/install the actual candidate wheel using existing
production tooling; exercise core, core+http, formats and formats+http dependency
sets. A clean editable import alone does not prove the wheel entry points work.

Run real local RST/eRST and opted-in live LLM cases separately from deterministic
and external-protocol fixture tests. Report unavailable prerequisites and exact
skips; never count those rows as passed. No new release receipt, tag, registry,
push or external publication is required by this plan.

Use the focused semantic cases in the analytical-quality contract and launch a
cold critic to inspect the changed code, tests and actual outputs. Fix concrete
findings and rerun affected tests. No owner annotation, frozen corpus, custom
scorer or certification workflow is required.

After code implementation, run the required Graphify incremental update for
navigation. Graph output is not evidence that code/tests/installations work.
Planning-only edits do not require a graph rebuild.

## Complexity Tracking

No unjustified complexity exception. Versioned historical readers are necessary
to preserve existing saved evidence; optional HTTP dependencies provide protocol
handling without adding another analysis engine. Inline guides and whole-technique
views address the explicit AI-consumption requirement without another formalism.

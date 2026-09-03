# Research: Toulmin Provider

**Feature**: 013 | **Date**: 2026-09-03

## D1 — Native analytical object

**Decision**: A result is an ordered collection of Toulmin layouts. Claim, grounds, and
warrant form the mandatory core; backing, qualifier, and rebuttal are optional and keep
their distinct functions.

**Rationale**: The warrant is the inference licence that distinguishes a Toulmin layout
from a premise/conclusion pair. Feature 006 FR-019 expressly forbids the latter from
being relabelled as complete Toulmin analysis.

**Alternatives rejected**: Generic argument graphs lose role semantics; requiring all
six elements fabricates optional material; making the warrant optional defeats the
theory's analytical value.

## D2 — Model-assisted interpretation with deterministic acceptance

**Decision**: A language model proposes `ToulminAnalysis`; the native contract accepts
or rejects it. Invalid proposals are never repaired, back-filled, or projected into a
partial result.

**Rationale**: Recovering implicit warrants is interpretive, while contract validity is
deterministic. Keeping those responsibilities separate preserves an honest boundary.

**Alternatives rejected**: Rule-only extraction cannot recover implicit warrants;
untyped text output cannot prove native validity; post-hoc repair invents analysis.

## D3 — Two explicit attempt budgets

**Decision**: Output-validation attempts and transient-transport attempts have separate
bounds and evidence. Provider-client implicit retries are disabled; the shared LLM
boundary owns retry classification, bounded exponential backoff with full jitter,
`Retry-After`, a total deadline, and attempt recording.

**Rationale**: Current Pydantic AI documentation distinguishes agent output retries from
HTTP transport retries, with transport configured below the model client. The existing
`StructuredAnalyst` stores a transport budget but does not apply it, and its run-usage
request count cannot see transparent HTTP retries. Explicit ownership is required by the
Feature 006 no-silent-retry contract.

**Alternatives rejected**: Relying on provider defaults hides attempts; treating invalid
output as transport failure conflates deterministic and transient work; unbounded retry
is unsafe and untestable.

## D4 — Capability and identity

**Decision**: Capability resolves configuration only. Provider identity includes the
exact model string; provenance includes package version, source digest, model identity,
and licence. No client is built until analysis.

**Rationale**: A capability query must be cheap, side-effect-free, and stable while a
model change must yield a new analytical identity.

## D5 — Scope

**Decision**: The provider analyses arguments. It does not generate stronger arguments,
score persuasiveness, judge truth, or answer rebuttals.

**Rationale**: Feature 006 makes the machine permanently analysis-only and preserves
theory-native output for downstream consumers.

# Research: Rhetorical Discourse Analysis Machine

**Feature**: 006 | **Reconciled**: 2026-09-03 | **Input**: [spec.md](spec.md)

This record replaces the 2026-09-01 pre-migration design. The repository migration and
all seven production providers now exist, so historical assumptions are recorded only
where they still explain a live contract.

## D1 — One distribution and package

**Decision**: `rdam` is the sole distribution and import package. Machine contracts live
at its root; every technique lives in one subpackage: `rdam.rst`, `rdam.pdtb`,
`rdam.sdrt`, `rdam.toulmin`, `rdam.walton`, `rdam.dung`, or `rdam.ibis`.

**Rationale**: The 2026-09-02 owner ruling and Feature 010 superseded the proposed
top-level `machine/`, `rst/`, and sibling directories. One wheel now preserves strong
technique boundaries without multiplying package authorities.

## D2 — RST identity and preservation

**Decision**: The RST provider is `rdam.rst`, its machine adapter is
`rdam.rst.provider.RstProvider`, and its command is `rdam-rst`. Historical
`isanlp_rst.*` strings remain only where immutable persisted contracts or model releases
use them as identifiers.

**Rationale**: Package compatibility aliases were explicitly rejected. Analytical
preservation is proved by the classified migration baseline rather than by retaining a
removed import name.

## D3 — Canonical framework identity

**Decision**: Every provider declaration references the packaged projection of
`coe:artifact/narrative/analytical_frameworks_taxonomy`. The projection is generated
from the vendored Central_Configs distribution; provider-native inventories remain
provider-owned.

**Rationale**: Central owns framework identity, while each discourse or argumentation
theory owns its result semantics. This prevents ontology binding from flattening native
contracts.

## D4 — Production/workbench boundary

**Decision**: `rdam/` is the complete production import root and `workbench/` is the
single experimental/training root. Production never imports workbench, and distributable
artifacts contain no workbench member.

**Rationale**: The production-boundary gate now checks the live package rather than a
proposed directory roster.

## D5 — Capability and explicit outcomes

**Decision**: Capability means the configured provider can run. Aggregate analysis
returns one explicit native result, unavailable outcome, or typed failure per requested
technique. The machine never fabricates a placeholder or merges formalisms.

**Rationale**: The owner removed the unrequested promotion-evidence gate on 2026-09-02.
Evaluation can inform model choice in workbench, but it is not a second meaning of
runtime availability.

## D6 — Supported production composition

**Decision**: `rdam.production_machine()` constructs exactly the seven production
providers in canonical technique order. RST model loading and all LLM clients remain
lazy; capability inspection performs no inference or network request.

**Rationale**: A supported composition makes SC-012 executable while retaining direct,
independent provider construction for specialist use.

## D7 — Model-assisted native providers

**Decision**: Toulmin, Walton, SDRT, and PDTB use the shared `StructuredAnalyst` boundary.
The model proposes; each technique's deterministic native contract accepts or refuses
the proposal. Structured-output and transport attempts are separately bounded and
reported, and provider SDK implicit retries are disabled.

**Rationale**: Interpretive techniques need model assistance, but model output is not
authority. One shared transport boundary prevents silent or inconsistent retries.

## D8 — Decision-closed provider authorities

**Decision**: Dung, IBIS, Toulmin, Walton, SDRT, and PDTB each have an implementation
feature defining their native result and proof surface. Feature 006 owns composition and
cross-provider invariants, not the internal semantics of those results.

**References**: Features 011–016 under `specs/`.

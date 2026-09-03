# Feature Specification: SDRT Provider

**Feature Branch**: `015-sdrt-provider`

**Created**: 2026-09-03

**Status**: Complete

**Input**: User description: "Complete Feature 006 with a decision-closed, independently callable SDRT provider that preserves SDRT's native graph semantics."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Recover an SDRS Graph (Priority: P1)

As an analyst, I can analyse text as an SDRT graph containing elementary and complex discourse units and explicitly classified discourse relations.

**Why this priority**: A tree or flat relation list would erase SDRT's defining graph structure and relation scope.

**Independent Test**: Analyse a passage requiring a non-adjacent attachment and a complex discourse unit; verify that both survive in the native result.

**Acceptance Scenarios**:

1. **Given** segmented discourse, **When** analysis succeeds, **Then** every EDU has exact source offsets and every relation names existing discourse units.
2. **Given** a relation whose argument is a CDU, **When** the result is serialized, **Then** the CDU and its membership remain explicit.
3. **Given** coordinating and subordinating attachments, **When** the graph is validated, **Then** their structural class remains distinct.

---

### User Story 2 - Refuse Invalid SDRSs (Priority: P2)

As a consumer, I receive either a structurally valid SDRS or an explicit typed failure, never a repaired or partially valid graph.

**Why this priority**: Reference, cycle, connectivity, scope, and right-frontier defects change the analysis rather than merely its formatting.

**Independent Test**: Submit malformed deterministic proposals covering dangling references, cycles, mixed structural classes, bad source spans, and right-frontier violations; verify that each is refused.

**Acceptance Scenarios**:

1. **Given** a dangling or self-referential edge, **When** validation runs, **Then** no native result is emitted.
2. **Given** cyclic CDU membership or a cyclic relation graph, **When** validation runs, **Then** the proposal is refused.
3. **Given** a new EDU attached outside the computed right frontier, **When** validation runs, **Then** the proposal is refused with a stable failure code.

---

### User Story 3 - Use SDRT Independently (Priority: P3)

As the machine owner, I can inspect and invoke SDRT without loading or changing another technique.

**Why this priority**: Feature 006 requires independent native providers and side-effect-free capability discovery.

**Independent Test**: Construct only the SDRT provider, inspect its declaration without client creation, and run it through the aggregate machine.

**Acceptance Scenarios**:

1. **Given** configured credentials, **When** capability is inspected, **Then** SDRT reports available without constructing a model client or making a request.
2. **Given** a successful analysis, **When** provenance is inspected, **Then** it identifies the exact model, provider source, package version, contract version, and licence.

### Edge Cases

- Empty and whitespace-only sources.
- A valid one-EDU graph with no relations.
- Non-contiguous CDU members and a relation scoped over a CDU.
- Multiple compatible relations between the same arguments.
- The same pair labelled once coordinating and once subordinating.
- Overlapping, reversed, or non-matching EDU offsets.
- Output-validation exhaustion and transient model-service failures.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The provider MUST return a separately versioned native SDRT result rather than an RST tree or generic graph.
- **FR-002**: Every EDU MUST have a unique identity, non-empty text, ordered exact source offsets, and a stable textual order.
- **FR-003**: CDUs MUST have unique identities, at least two members, valid member references, and acyclic membership.
- **FR-004**: Relations MUST be directed, binary, non-self-referential, and explicitly classified as coordinating or subordinating.
- **FR-005**: Relation endpoints MUST resolve to EDUs or CDUs and the relation graph MUST be acyclic.
- **FR-006**: Every multi-unit graph MUST be connected when relation and membership edges are considered together.
- **FR-007**: A pair of discourse units MUST NOT carry both coordinating and subordinating relations.
- **FR-008**: Each EDU after the first MUST have an attachment from the right frontier computed from the already introduced graph; non-adjacent and CDU attachments MUST remain representable.
- **FR-009**: Model proposals MUST pass the native SDRT contract and exact-source validation without repair before becoming results.
- **FR-010**: Capability reporting MUST be side-effect-free and expose a stable reason when the configured model is unavailable.
- **FR-011**: Invalid input, undeclared formalism, model unavailability, invalid structured output, and service failures MUST become typed outcomes with mandatory retryability and attempt evidence.
- **FR-012**: SDRT invocation or withholding MUST NOT alter another provider's declaration, result, or capability bytes.

### Key Entities

- **EDU**: An elementary discourse unit anchored exactly to source text.
- **CDU**: A named complex discourse unit whose members are EDUs or nested CDUs.
- **SDRT Relation**: A labelled directed edge with a coordinating or subordinating structural class.
- **SDRS Graph**: The validated native graph containing discourse units, relations, and computed structural evidence.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of returned EDUs satisfy `text == source[start:end]` and have non-overlapping ordered spans.
- **SC-002**: 100% of returned references resolve; zero returned membership or relation graphs contain a cycle.
- **SC-003**: 100% of returned post-initial EDUs have a verified right-frontier attachment.
- **SC-004**: Deterministic tests refuse every required invalid graph class with zero partial results.
- **SC-005**: Capability inspection performs zero model requests and constructs zero model clients.
- **SC-006**: Every success and exhausted failure exposes exact independent output and transport attempt counts.
- **SC-007**: Withholding SDRT changes zero serialized capability bytes for unrelated providers.

## Assumptions

- SDRT relation inventories vary by annotation project; the native contract therefore preserves a non-empty relation label plus the theory-defining coordinating/subordinating class instead of inventing a closed universal inventory.
- Right-frontier validation is computed over textual EDU introduction order, reverse subordinating ancestry, and completed CDUs; it is structural validation, not a claim that an LLM has supplied formal dynamic semantics.
- Model-assisted interpretation proposes graphs; deterministic native validation remains authoritative.

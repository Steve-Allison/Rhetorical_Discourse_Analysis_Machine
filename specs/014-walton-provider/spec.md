# Feature Specification: Walton Provider

**Feature Branch**: `014-walton-provider`

**Created**: 2026-09-03

**Status**: Complete

**Input**: User description: "Make the existing Walton argumentation-scheme analysis a
decision-closed production provider that satisfies Feature 006 and preserves native
scheme roles and critical questions."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Identify Native Scheme Instances (Priority: P1)

As an analyst, I can submit argumentative text and receive each recognized argument as a
native Walton scheme instance with exactly that scheme's premise roles.

**Why this priority**: A scheme label without its role structure is a classification,
not a Walton analysis.

**Independent Test**: For every supported scheme, validate a fully populated instance;
then remove or add one role and verify the malformed instance is refused.

**Acceptance Scenarios**:

1. **Given** an argument matching a supported scheme, **When** it is analysed, **Then** the result names that scheme, its conclusion, and exactly its required premise roles.
2. **Given** an argument matching no supported scheme, **When** it is analysed, **Then** no scheme is forced onto it.
3. **Given** a proposal with missing or unknown premise roles, **When** it is validated, **Then** no native result is emitted.

---

### User Story 2 - See the Critical Questions Left Open (Priority: P2)

As an analyst, I can see which critical questions the passage itself addresses and which
remain open, without the provider inventing answers.

**Why this priority**: Critical questions are the evaluative substance of Walton's
presumptive schemes; silently answering them would fabricate evidence.

**Independent Test**: For every supported scheme, mark none, one, and all critical
questions addressed; verify the open set is the exact complement and every addressed
question cites how the source addresses it.

**Acceptance Scenarios**:

1. **Given** an unreported critical question, **When** a result is returned, **Then** that question is explicitly open.
2. **Given** a question marked addressed, **When** it is validated, **Then** a non-empty source-grounded note is required.
3. **Given** an out-of-range or duplicate question index, **When** it is validated, **Then** the proposal is refused.

---

### User Story 3 - Receive an Independent, Evidenced Provider Outcome (Priority: P3)

As a downstream consumer, I receive either a validated native Walton result or one
explicit typed outcome with model, attempt, and provider provenance.

**Why this priority**: Model interpretation must stay independently callable, bounded,
and auditable without changing another technique.

**Independent Test**: Exercise success, empty analysis, invalid output, unavailable
model, transport exhaustion, and provider withholding through the aggregate machine.

**Acceptance Scenarios**:

1. **Given** configured credentials, **When** capability is inspected, **Then** Walton reports available without building a client or making a request.
2. **Given** a successful result, **When** it is inspected, **Then** it names the scheme-set version, exact model, instruction identity, attempt evidence, provider source, contract version, and licence.
3. **Given** exhausted output or transient-transport attempts, **When** analysis ends, **Then** one typed failure reports its class, retryability, and observed attempts with no partial result.

### Edge Cases

- Empty or whitespace-only text.
- Several arguments instancing different schemes.
- A valid argument outside the supported scheme set.
- Missing, additional, or blank premise-role values.
- Negative, duplicate, or out-of-range critical-question indices.
- An addressed question without source-grounded explanation.
- Authentication rejection, rate limiting, server failure, and malformed model output.
- A request for an undeclared formalism.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The provider MUST accept source text and return a separately versioned native Walton result.
- **FR-002**: The supported scheme catalogue MUST give every scheme a stable identifier, name, non-empty unique premise-role set, and non-empty critical-question set.
- **FR-003**: A scheme instance MUST contain exactly its declared premise roles, a non-empty conclusion, and no unknown role.
- **FR-004**: Every reported critical question MUST reference a real question in the selected scheme and MUST appear at most once.
- **FR-005**: Unreported critical questions MUST be returned as open; addressed questions MUST retain a non-empty source-grounded note; the provider MUST NOT answer open questions.
- **FR-006**: Text containing no recognized scheme instance MUST return an empty native analysis rather than a forced match.
- **FR-007**: Model proposals MUST pass the native Walton contract without repair or coercion before becoming results.
- **FR-008**: Capability reporting MUST be side-effect-free and MUST report a stable unavailable reason when the configured model cannot be called.
- **FR-009**: Provider identity and provenance MUST include the exact model, provider source, package and contract versions, licence, and scheme-set identity.
- **FR-010**: Invalid input, undeclared formalism, model unavailability, invalid structured output, and model-service failures MUST become typed outcomes with mandatory retryability.
- **FR-011**: Structured-output and transient-transport attempts MUST be independently bounded and expose observed counts without silent retries.
- **FR-012**: Walton invocation and withholding MUST NOT change another technique's contract, capability, or result.

### Key Entities

- **Scheme**: Stable scheme identity, display name, premise-role vocabulary, and ordered
  critical questions.
- **Scheme Instance**: One argument's selected scheme, conclusion, exact role values,
  and per-question source status.
- **Walton Analysis**: The ordered collection of recognized scheme instances, including
  the valid empty collection, plus a scheme-set identity.
- **Extraction Evidence**: Model, instruction, output-attempt, and transport-attempt
  identities for the proposal sequence.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of supported scheme identifiers have a name, at least one unique premise role, and at least one critical question.
- **SC-002**: Across every supported scheme, 100% of valid exact-role instances pass and 100% of missing-role, unknown-role, and blank-role instances fail.
- **SC-003**: For every result, the reported open questions equal the scheme catalogue minus the uniquely addressed questions.
- **SC-004**: Zero open questions receive provider-authored answers and every addressed question has a source-grounded note.
- **SC-005**: Every invalid, unavailable, and service-failure scenario produces one typed outcome and zero partial scheme instances.
- **SC-006**: Capability inspection performs zero model requests and constructs zero model clients.
- **SC-007**: Successful results expose complete model, attempt, source, contract, licence, and scheme-set provenance.
- **SC-008**: Withholding Walton changes zero serialized capability bytes for every unrelated registered provider.

## Assumptions

- The initial catalogue is an explicitly versioned, production-supported subset of the
  Walton, Reed, and Macagno scheme family; unsupported schemes are not forced into the
  nearest available label.
- The provider analyses scheme use and open critical questions. It does not decide
  argument truth, answer open questions, or generate stronger arguments.
- Model proposals are interpretive candidates; the native catalogue and validator are
  the acceptance authority.
- The shared machine LLM boundary owns bounded attempt behaviour; Walton owns its scheme
  catalogue, prompt, native result, and semantic validation.

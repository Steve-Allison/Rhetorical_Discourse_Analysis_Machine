# Feature Specification: Toulmin Provider

**Feature Branch**: `013-toulmin-provider`

**Created**: 2026-09-03

**Status**: Complete

**Input**: User description: "Make the existing Toulmin analysis a decision-closed,
production provider that satisfies Feature 006 and preserves Toulmin's native theory."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Recover Complete Argument Layouts (Priority: P1)

As an analyst, I can submit argumentative text and receive each argument as a native
Toulmin layout so that the reasoning licence connecting evidence to claim is explicit.

**Why this priority**: A result without grounds, claim, and warrant is not a Toulmin
analysis and would falsely relabel ordinary claim extraction.

**Independent Test**: Analyse a passage containing a claim, stated evidence, and an
implicit inference licence; verify that at least one result contains a distinct claim,
one or more grounds, and a non-restating warrant.

**Acceptance Scenarios**:

1. **Given** a passage containing an argument, **When** it is analysed, **Then** every returned layout contains a claim, at least one ground, and a warrant that is distinct from both.
2. **Given** backing, a qualifier, or rebuttal conditions in the passage, **When** a layout is returned, **Then** those elements qualify the correct part of the layout rather than becoming generic premises.
3. **Given** text that asserts but does not argue, **When** it is analysed, **Then** the native result contains zero layouts rather than an invented argument.

---

### User Story 2 - Receive Only Validated Native Results (Priority: P2)

As a downstream consumer, I receive either a complete native Toulmin result or an
explicit typed outcome, never a malformed or silently repaired model proposal.

**Why this priority**: Model output is evidence only after the technique's own rules
accept it; otherwise the machine would fabricate analytical certainty.

**Independent Test**: Exercise valid, structurally invalid, unavailable-model, empty,
and wrong-formalism cases; verify that only the valid proposal becomes a result and every
other case has the specified explicit outcome.

**Acceptance Scenarios**:

1. **Given** a proposal whose warrant repeats the claim or a ground, **When** it is validated, **Then** it is refused and no native result is emitted.
2. **Given** an unavailable configured model, **When** capability or analysis is requested, **Then** capability reports a stable unavailability reason and analysis performs no model request.
3. **Given** a transient or invalid-output failure, **When** the bounded attempt budget is exhausted, **Then** the failure reports its class, retryability, and actual attempt count.

---

### User Story 3 - Use Toulmin Independently (Priority: P3)

As the machine owner, I can inspect capability and invoke Toulmin without loading or
changing any unrelated provider.

**Why this priority**: Feature 006 requires independently callable native techniques and
side-effect-free capability reporting.

**Independent Test**: Construct only the Toulmin provider, inspect its declaration, and
run it through the aggregate machine while all unrelated techniques remain untouched.

**Acceptance Scenarios**:

1. **Given** configured credentials, **When** capability is inspected, **Then** Toulmin reports available without constructing a model client or making a network request.
2. **Given** a native result, **When** its provenance is inspected, **Then** it names the provider contract, exact model identity, source revision, package version, and licence.

### Edge Cases

- Whitespace-only input or a request without text.
- Multiple independent arguments in one passage.
- A warrant that differs only in case or surrounding whitespace from the claim or ground.
- Backing supplied without a valid warrant.
- A model proposal containing unknown fields or incomplete nested rebuttals.
- Output-validation exhaustion, authentication rejection, rate limiting, server failure,
  and an unexpected model-client failure.
- A caller requests a formalism other than the declared Toulmin layout.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The provider MUST accept source text and return a separately versioned native Toulmin result.
- **FR-002**: Every returned layout MUST contain a non-empty claim, one or more non-empty grounds, and a non-empty warrant.
- **FR-003**: A warrant MUST NOT be accepted when it repeats the claim or any ground after whitespace and case normalization.
- **FR-004**: Backing MUST qualify the warrant, a qualifier MUST express the force of the claim, and rebuttals MUST state defeating conditions; absent optional elements MUST remain absent rather than fabricated.
- **FR-005**: Non-argumentative text MUST produce an empty native analysis rather than a forced layout.
- **FR-006**: Model proposals MUST pass the native Toulmin contract without repair or coercion before becoming results.
- **FR-007**: Capability reporting MUST be side-effect-free and MUST report a stable unavailable reason when the configured model cannot be called.
- **FR-008**: The provider MUST expose the canonical Toulmin framework identity, one formalism, its contract version, whether structured input is required, and complete provider provenance.
- **FR-009**: The configured model identity MUST be part of provider identity and result provenance.
- **FR-010**: Invalid input, undeclared formalism, model unavailability, invalid structured output, and model-service failures MUST become typed outcomes with mandatory retryability classification.
- **FR-011**: Structured-output and transient-transport attempts MUST be independently bounded, and success or exhaustion MUST expose the actual attempt count without silent retries.
- **FR-012**: Toulmin invocation and withholding MUST NOT change another technique's contract, capability, or result.

### Key Entities

- **Toulmin Layout**: One argument's claim, grounds, warrant, and optional backing,
  qualifier, and rebuttals.
- **Toulmin Analysis**: The ordered collection of layouts found in one source, including
  the valid empty collection.
- **Extraction Evidence**: Model identity, instruction identity, and observed attempt
  counts for the accepted or failed proposal sequence.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of returned layouts contain the core claim-ground-warrant triad and zero accepted warrants restate a claim or ground.
- **SC-002**: 100% of optional elements round-trip without being renamed, reassigned, or fabricated.
- **SC-003**: Every invalid, unavailable, and service-failure scenario produces one explicit typed outcome and zero partial results.
- **SC-004**: Capability inspection performs zero model requests and constructs zero model clients.
- **SC-005**: 100% of successful results identify the exact model, provider source, package version, contract version, and licence.
- **SC-006**: Tests demonstrate the configured maximum for structured-output attempts and transport attempts, and the reported count equals the attempts observed.
- **SC-007**: Withholding Toulmin changes zero serialized capability bytes for every unrelated registered provider.

## Assumptions

- The machine analyses text; it does not generate arguments or recommend how to persuade.
- Recovering an implicit warrant requires model-assisted interpretation, but model output
  is never authoritative until the native contract accepts it.
- The shared machine LLM boundary owns transport and structured-output attempt policy;
  the Toulmin provider owns the prompt, native model, and semantic validation.
- Evaluation of interpretive quality beyond contract validity is a separate workbench
  concern and cannot gate whether correctly configured production code is callable.

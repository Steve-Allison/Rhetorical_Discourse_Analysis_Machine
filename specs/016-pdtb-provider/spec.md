# Feature Specification: PDTB Provider

**Feature Branch**: `016-pdtb-provider`

**Created**: 2026-09-03

**Status**: Complete

**Input**: User description: "Complete Feature 006 with a decision-closed, independently callable provider that preserves the Penn Discourse Treebank 3.0 contract."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Recover PDTB-3 Relations (Priority: P1)

As an analyst, I can receive binary Arg1/Arg2 discourse relations whose relation type, connective evidence, and senses retain PDTB-3 meaning.

**Why this priority**: Flattening relation types or the three-level sense hierarchy would not be a PDTB-3 analysis.

**Independent Test**: Analyse deterministic examples for all seven PDTB-3 relation types and verify their exact native fields.

**Acceptance Scenarios**:

1. **Given** an explicit connective, **When** analysis succeeds, **Then** its source span, both argument spans, and one or more canonical PDTB-3 senses are retained.
2. **Given** an implicit relation, **When** analysis succeeds, **Then** the inferred connective and senses remain distinct from explicit source evidence.
3. **Given** AltLex, AltLexC, EntRel, Hypophora, and NoRel cases, **When** results are serialized, **Then** each retains its own PDTB-3 relation type and required/forbidden evidence fields.

---

### User Story 2 - Receive Only Exact Native Relations (Priority: P2)

As a consumer, I receive exact source-grounded and schema-valid PDTB relations or a typed failure, never corrected model output.

**Why this priority**: Argument direction, source anchoring, and sense labels are analytical claims.

**Independent Test**: Exercise mismatched spans, overlaps, missing evidence, forbidden senses, unknown senses, duplicate IDs, and malformed model proposals; verify refusal without partial results.

**Acceptance Scenarios**:

1. **Given** any argument or evidence quote that differs from its source slice, **When** validation runs, **Then** the proposal is refused.
2. **Given** an EntRel, Hypophora, or NoRel carrying a discourse sense, **When** validation runs, **Then** it is refused.
3. **Given** a sense-bearing type without a canonical sense or required signal, **When** validation runs, **Then** it is refused.

---

### User Story 3 - Use PDTB Independently (Priority: P3)

As the machine owner, I can inspect and invoke PDTB without loading or changing another technique.

**Why this priority**: Feature 006 requires independent native providers and side-effect-free capability reporting.

**Independent Test**: Construct only the PDTB provider, inspect capability without model construction, and run it through the machine.

**Acceptance Scenarios**:

1. **Given** configured credentials, **When** capability is inspected, **Then** PDTB reports available without a model client or request.
2. **Given** a successful result, **When** provenance is inspected, **Then** it names the exact model, source revision, package version, contract version, and licence.

### Edge Cases

- Empty and whitespace-only sources.
- Discontinuous argument or connective spans.
- Multiple canonical senses on one relation.
- Intra-sentential subordinate structures where Arg2 precedes Arg1 in the source.
- No relation tokens in a paragraph.
- Overlapping Arg1 and Arg2 spans.
- Output-validation exhaustion and transient model-service failures.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The provider MUST return a separately versioned native PDTB-3 result.
- **FR-002**: Each relation MUST contain unique identity and binary Arg1/Arg2 arguments composed of one or more exact source spans.
- **FR-003**: The relation type MUST be exactly one of Explicit, Implicit, AltLex, AltLexC, EntRel, Hypophora, or NoRel.
- **FR-004**: Sense-bearing relations MUST contain one or more unique leaves from the PDTB-3 sense hierarchy and MUST preserve multiple senses.
- **FR-005**: EntRel, Hypophora, and NoRel MUST carry no discourse sense or connective evidence.
- **FR-006**: Explicit relations MUST carry explicit source connective spans; Implicit relations MUST carry one or more inferred connectives and no explicit spans.
- **FR-007**: AltLex and AltLexC MUST carry exact lexical or constructional evidence spans and no inferred connective.
- **FR-008**: Arg1 and Arg2 spans MUST each be internally ordered and non-overlapping, and the two arguments MUST NOT overlap.
- **FR-009**: The provider MUST preserve PDTB-3 argument labels without assuming that Arg1 always precedes Arg2.
- **FR-010**: Every quoted span MUST equal the exact zero-based half-open source slice.
- **FR-011**: Model proposals MUST pass native validation without repair before becoming results.
- **FR-012**: Capability reporting and failure/attempt evidence MUST obey the shared Feature 006 provider contract.
- **FR-013**: PDTB invocation or withholding MUST NOT alter another provider's contract, capability, or result.

### Key Entities

- **Text Span**: One exact, half-open source segment.
- **Argument**: Ordered one-or-more spans forming Arg1 or Arg2.
- **PDTB Relation**: A typed binary relation with type-specific evidence and canonical senses where applicable.
- **PDTB Analysis**: An ordered collection of valid relations, including the valid empty collection.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of returned quotes equal their source slices and zero returned argument spans overlap.
- **SC-002**: Deterministic tests cover all seven relation types and every leaf in the shipped PDTB-3 sense enum is an exact manual label.
- **SC-003**: 100% of sense-bearing relations contain canonical senses; 100% of EntRel, Hypophora, and NoRel contain none.
- **SC-004**: Every invalid native/model proposal produces one typed failure and zero partial results.
- **SC-005**: Capability inspection performs zero model requests and constructs zero clients.
- **SC-006**: Every success and exhausted failure exposes exact independent output and transport attempt counts.
- **SC-007**: Withholding PDTB changes zero serialized capability bytes for unrelated providers.

## Assumptions

- PDTB-3 annotation is shallow and binary; the provider does not invent an RST/SDRT hierarchy.
- Character offsets are Python Unicode code-point offsets into the exact submitted source, even though the distributed corpus format uses byte-indexed stand-off data.
- The official PDTB-3 annotation manual is the semantic authority; model output is only a proposal.

# Feature Specification: RST Provider Adapter

**Feature**: `009-rst-provider-adapter`

**Created**: 2026-09-02

**Reconciled**: 2026-09-03

**Status**: Complete

## User Story 1 — Inspect truthful RST capability (Priority: P1)

As the machine owner, I can inspect a published or local RST configuration and learn
whether it can run without constructing a parser or touching a model service.

**Independent test**: Known published versions and valid tiny local releases report
available; missing, unsafe, malformed, incompatible, partial, and corrupt releases report
`model_unavailable`; no case constructs a parser.

### Acceptance scenarios

1. The default provider declares the canonical published `gumrrg` model.
2. A valid immutable local release is fully validated once and reports its exact licence.
3. An invalid local release never reports available merely because a manifest exists.
4. Repeated declarations do not repeat local release validation.
5. RST and eRST formalisms retain separate canonical identities and capability states.

## User Story 2 — Receive the exact native RST result (Priority: P2)

As an analyst, I receive the canonical `rdam.rst` production outcome inside the aggregate
without adapter-owned schema changes or hidden failure reinterpretation.

**Independent test**: Deterministic guards and the available real parser smoke prove that
the adapter selects the requested formalism, invokes canonical ingest, preserves the
serialized outcome, and maps only expected failures.

### Acceptance scenarios

1. Text/formalism/capability guards run before parser construction.
2. The payload is exactly the serialized canonical production-ingest outcome.
3. `ProductionIngestError` preserves code, retryability, stage, and category.
4. A local release changed after declaration becomes non-retryable `model_release_invalid`.
5. Unexpected internal exceptions propagate rather than becoming provider failures.

## User Story 3 — Use RST independently in the machine (Priority: P3)

As the machine owner, I can register, withhold, or invoke RST without loading or changing
any unrelated technique.

**Independent test**: Machine construction and capability inspection remain model-free;
withholding RST changes zero serialized capability bytes for the other six boundaries.

## Requirements

- **FR-001**: The adapter MUST be `rdam.rst.provider.RstProvider` inside the single `rdam` distribution.
- **FR-002**: The adapter MUST use `Parser`, `ProductionIngestor`, and production serialization as canonical authorities.
- **FR-003**: Published and local model configuration MUST be mutually exclusive and local configuration MUST be complete.
- **FR-004**: A known published parser version MUST declare availability without a network request or parser construction.
- **FR-005**: A local release MUST declare availability only after safe identity, manifest, compatibility, membership, size, and hash validation.
- **FR-006**: Local release validation MUST be cached per provider while parser construction remains lazy.
- **FR-007**: Valid local provenance MUST report the validated release licence; invalid local provenance MUST NOT claim the published-model licence.
- **FR-008**: `rst_tree` and `erst_graph` MUST retain distinct canonical identities and capability states.
- **FR-009**: Text, capability, and formalism refusal MUST happen before model construction.
- **FR-010**: The native payload MUST equal the canonical serialized production-ingest outcome without adapter reinterpretation.
- **FR-011**: Production-ingest failures MUST preserve code, retryability, stage, and category.
- **FR-012**: Expected local release load failures MUST become non-retryable typed provider failures; unexpected exceptions MUST propagate.
- **FR-013**: RST registration, withholding, capability, and execution MUST NOT alter an unrelated provider's declaration or outcome.

## Success criteria

- **SC-001**: 100% of valid local release fixtures report available and 100% of required invalid classes report unavailable without parser construction.
- **SC-002**: Repeated declaration reads perform exactly one immutable-release validation.
- **SC-003**: 100% of accepted local results use a fully revalidated release at load time.
- **SC-004**: Every expected adapter failure has one typed outcome and zero partial result.
- **SC-005**: The adapter adds, removes, and renames zero fields in the native RST outcome.
- **SC-006**: Withholding RST changes zero capability bytes for all unrelated boundaries.
- **SC-007**: Applicable RST, aggregate, production API, static, and boundary gates pass with observed evidence.

## Scope

The adapter owns machine declaration, configuration validation, formalism selection,
failure translation, and aggregate envelope construction. RST parsing mathematics,
ingest, schemas, source anchors, persistence, and model-release validation semantics stay
owned by their canonical `rdam.rst` modules.

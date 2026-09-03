# RST Adapter Contract

## Configuration and capability

- Published and local model configuration are mutually exclusive.
- A partial local configuration is rejected at construction.
- Known published versions declare availability without client/model construction.
- A local release declares availability only after complete immutable-release validation.
- Invalid, incompatible, corrupt, missing, or unsafe local releases declare
  `model_unavailable` without leaking parser/load exceptions.
- Repeated declaration reads do not repeat local release hashing.

## Formalisms

- `rst_tree` is the default RST formalism.
- `erst_graph` has its own canonical eRST identity and is available only with a validated
  completion bundle.
- Unknown or unavailable formalism requests are refused before model construction.

## Analysis

- Text is required and bound to the aggregate source identity.
- Parser construction is lazy and occurs only after capability/formalism/input guards.
- The adapter calls the canonical `ProductionIngestor` and retains
  `serialize_contract(outcome)` as its opaque native payload.
- The returned aggregate envelope agrees exactly with the provider declaration.

## Failures and provenance

- Local release validation/load failure is `model_release_invalid`, non-retryable.
- `ProductionIngestError` preserves code, retryability, stage, and category.
- Unexpected internal exceptions propagate.
- Valid local licence comes from the validated release; invalid local configuration does
  not inherit the published-model licence.

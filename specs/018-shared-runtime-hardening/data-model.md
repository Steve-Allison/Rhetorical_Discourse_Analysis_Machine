# Data Model: Shared Runtime Hardening

## ExecutionPolicy

Frozen process-local configuration:

- `max_workers: int = 4`, inclusive range `1..7`.
- `cache_directory: Path | None = None`; `None` performs no persistent cache I/O.

## Frozen JSON

`FrozenJsonObject` and `FrozenJsonArray` recursively own validated copies. They retain native mapping/list value and wire semantics but every mutator raises `TypeError`. Scalars remain unchanged. Contract serializers emit ordinary JSON objects/arrays.

## ModelIdentity

Frozen pair of supported provider and non-empty model name. Its canonical string is `<provider>:<model>`. A bare input supplies `openai`; malformed and unsupported inputs never become model clients.

## ProviderProvenance

The persisted fields and wire shape are unchanged. `source_revision` remains nullable only so historical native results load. `ProviderDeclaration` requires it when capability is available.

## Cache Entry

The entry is exactly one serialized `NativeTechniqueResult`, named by SHA-256 over source identity, technique, formalism, structured input, derivation reference, provider identity/contract, complete provenance, and model identity. No cache envelope or contract version is introduced.

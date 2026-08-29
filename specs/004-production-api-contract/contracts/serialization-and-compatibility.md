# Contract: Serialization, Identity, and Compatibility

**Contract family**: `isanlp_rst.production`  
**Write version**: 2.0.0  
**JSON dialect**: I-JSON canonicalized with RFC 8785  
**Schema dialect**: JSON Schema Draft 2020-12

## Canonical envelope

Every public top-level record serializes as a closed object:

```json
{
  "contract": "isanlp_rst.production",
  "contract_version": "2.0.0",
  "kind": "preparation_outcome",
  "semantic": {},
  "execution": {},
  "semantic_digest": {
    "algorithm": "sha256",
    "hex_digest": "0000000000000000000000000000000000000000000000000000000000000000"
  }
}
```

`kind` dispatches to an exact tagged model before payload validation. Unknown
top-level or nested fields fail validation.

## Canonical byte contract

`serialize_contract(value)` returns UTF-8 RFC 8785 canonical JSON bytes with no
byte-order mark or trailing newline. Human-readable pretty JSON may exist as a
diagnostic projection but is never the persistence, digest, or cache authority.

Serialization rejects:

- duplicate object keys;
- invalid Unicode and lone surrogates;
- NaN, positive infinity, and negative infinity;
- integers or numeric values outside the contract's exact validated range;
- unordered persisted containers;
- values not declared by the exact tagged schema.

`model_dump_json()` and `json.dumps(sort_keys=True)` do not define canonical
identity.

## Semantic digest

For a top-level value `record`, the semantic input is exactly:

```json
{
  "contract": "<record.contract>",
  "contract_version": "<record.contract_version>",
  "kind": "<record.kind>",
  "semantic": "<record.semantic>"
}
```

The digest is:

```text
SHA-256(RFC8785(semantic input))
```

The following never participate:

- `semantic_digest` itself;
- execution identifiers and timestamps;
- duration, host, device, accelerator, and process facts;
- cache-hit/miss status or local cache path;
- local diagnostic detail;
- receipt verification timestamps.

Nested semantic values are included as complete values, not replaced by only
their digests. A nested preparation outcome's execution evidence remains
exposed but is removed by the analysis semantic projection.

## Request, result, and cache identity

The contract distinguishes:

1. source identity;
2. preparation semantic identity;
3. analysis plan identity;
4. model identity;
5. analysis request identity;
6. validated analysis result identity;
7. cache entry identity.

The request identity contains source identity, source contract, preparation and
planning policies, prepared discourse, plan, immutable model identity, parser
capacity, complete resolved analysis policy, exact analysed-document substrate,
composite identities for every participating primary, segmenter, refinement,
eRST, decoder, calibration, relation, and ontology component, analysis pipeline
version, exact loaded-component receipts, and result contract write version.

The result identity adds validated RST/eRST analysis, primary/eRST decision
evidence, both-endpoint and signal anchors, refinement records, recombination
receipt, and validation receipt. The cache entry identity binds request and
result identities. A cache load succeeds only when all three independently
recompute and agree with the current request.

Mutable, unidentified, or absent model identities are explicitly ineligible
for durable semantic caching. The service may still analyse with a mutable
parser if policy permits, but execution evidence records cache bypass and its
reason.

## Exact semantic quantities

Semantic coverage uses integer numerators and denominators. Token, character,
segment, item, and anchor counts are integers. Confidence or calibrated score
values produced by the scientific model remain the model's defined values, but
their serialization must be finite and use the validated representation of the
existing analysis contract. Feature 004 does not change their mathematics.

Every score additionally carries its declared confidence kind, range,
producing component, and calibration identity or explicit uncalibrated state.
Normalized distributions use ordered labelled finite values and validate their
sum within the contract tolerance. Raw tensors and unrestricted parsing charts
are not serializable public contract values.

## Loader sequence

`load_contract(data)` performs these operations in order:

1. decode UTF-8 strictly;
2. parse JSON while rejecting duplicate keys and invalid I-JSON values;
3. read only `contract`, `contract_version`, and `kind` from the closed outer
   object;
4. reject unknown contract families;
5. resolve the exact version through the compatibility registry;
6. reject unsupported versions before interpreting their payload;
7. validate the exact tagged model recursively;
8. recompute and compare the semantic digest in constant-time-safe equality;
9. run all cross-field and graph invariants;
10. return the immutable typed value.

A failure at any step returns no partially loaded value and raises a typed
serialization or compatibility `ProductionIngestError`.

## Compatibility registry

The registry is explicit data packaged with the runtime:

| Runtime package | Write version | Read versions | Behaviour |
|---|---|---|---|
| 5.0.0 | 2.0.0 | 2.0.0 | Exact validation; no migration |

Contract 1.x is not automatically readable because it lacks complete inventory,
retained values, preparation outcome, model identity, and typed failure
evidence. A migration may be added only for a concrete 1.x kind whose complete
2.x meaning can be produced without invented values. Migration creates a new
2.x record and new semantic digest and reports the source contract version in
execution provenance.

Unknown future versions and unsupported old major versions fail closed. A
same-major version is not assumed compatible until it appears in the explicit
read table.

## Versioning rules

### Package version

- Major: any incompatible supported Python import, signature, behaviour,
  exception, status, or serialized-contract change.
- Minor: backward-compatible public addition or declared deprecation.
- Patch: correction that preserves documented public meaning.

Released version contents are immutable. Rebuilt bytes require a new release
version or a formally distinct build number governed by the release policy;
they never overwrite an existing tracked artifact.

### Serialized contract version

Major changes include:

- removing or renaming a field;
- changing a field's type, default, requiredness, or meaning;
- changing the semantic projection or digest meaning;
- adding a required field;
- adding or changing a discriminator in a way an existing reader cannot
  interpret;
- weakening unknown-field rejection;
- changing failure evidence semantics.

Minor changes are allowed only when an older reader can preserve full meaning
under the declared schema and registry. Patch changes correct documentation or
validation without changing valid serialized meaning.

## JSON Schema projections

The runtime Pydantic models are the type and field authority. Implementation
generates serialization-mode schemas with:

- `$schema` set to Draft 2020-12;
- stable versioned `$id` values;
- closed objects at every level;
- `oneOf` plus exact `const` discriminators;
- shared definitions under `$defs`;
- explicit finite/exact numeric constraints;
- descriptions sufficient to state provider-owned field meaning.

Generated schemas are committed under `isanlp_rst/ingest/schemas/`, included in
wheel and sdist, loaded through `importlib.resources`, and compared byte for
byte with freshly generated canonical schema bytes. Editing a committed schema
by hand is forbidden.

Required schemas include:

- preparation outcome;
- parser analysis result;
- production analysis outcome union;
- analysis policy and resolved request;
- analysed document and substrate transformations;
- primary inference and eRST completion evidence;
- composite analysis identity;
- recombination and validation receipts;
- production capability description;
- safe production failure union;
- explicitly opted-in diagnostic production failure union;
- public-surface inventory;

The distribution receipt uses its separate
`isanlp_rst.release_receipt` contract and schema in the production-boundary
tooling; it is not a runtime ingest outcome.

## Determinism tests

The conformance suite must prove:

1. two independently constructed equivalent values serialize to identical
   bytes;
2. serialize-load-serialize produces identical bytes;
3. cached and uncached outcomes have identical semantic bytes and digest;
4. execution-only mutations leave semantic bytes unchanged;
5. every semantic input named in FR-041 changes its relevant identity;
6. tuple order changes identity where order is meaningful;
7. semantically unordered inputs normalize before model construction and then
   serialize identically;
8. duplicate keys, unknown fields, invalid values, corrupt digests, and
   unsupported versions fail before use;
9. generated schemas and packaged schemas are byte-identical;
10. output-formalism and evidence-detail changes alter request/cache identity
    whenever returned semantic evidence changes;
11. analysed-token/EDU/boundary/mapping/fidelity changes alter request and
    result identity;
12. primary/eRST decision, refinement, decoder, composite-component,
    recombination, and validation receipt changes alter result identity;
13. removing any required handoff evidence causes validation or reload to fail;
14. receipt timings and other execution-only values leave semantic bytes
    unchanged.
15. equivalent Python, CLI, and retained local-HTTP requests serialize to
    identical canonical semantic bytes and none defines another JSON schema.

## Failure serialization

An in-memory `ProductionFailure` may contain the full preparation outcome or
other completed private evidence. Default `serialize_contract()` first creates
a `SafeProductionFailureRecord`: private representation values are replaced by
typed redactions that preserve kind, length, digest, anchors, structure,
relationships, and disposition. The safe record then uses the same envelope
and digest rules. Safe human messages are selected from stable templates with
typed parameters. The serialized cause chain contains only allowlisted
type/category facts. It never contains:

- raw `str(cause)` or `repr(cause)`;
- traceback text, frames, or locals;
- raw source/prepared text;
- prompts or fragments;
- environment variables;
- unrestricted paths or mappings.

Completed-stage evidence is a tagged union. The failed stage validator rejects
evidence from the failed or any later stage.

Explicit `DiagnosticPolicy(include_private_content=True)` produces a separately
tagged `DiagnosticProductionFailureRecord` whose schema permits complete
private completed evidence. It is never the default and remains closed against
arbitrary traceback, environment, or exception data. Safe and diagnostic
failure records each round-trip deterministically within their own kind.

## Cache persistence

Cache writes use atomic temporary-file replacement in the cache directory. The
payload is canonical contract bytes. A success entry is written only after full
outcome validation. Failure payloads and partial unit results are never written
to the success cache.

Cache retrieval validates outer envelope, contract compatibility, request
identity, result digest, all semantic identities, and domain invariants. Any
failure becomes a typed `cache_retrieval` failure and leaves the corrupt entry
unused. Automatic deletion is a separate recoverable cache policy, not a side
effect of loading.

# Phase 0 Research: World-Class Production API Contract

**Feature**: `004-production-api-contract`  
**Research date**: 2026-08-29  
**Scope**: The installed, production-facing `isanlp_rst` provider contract only

## Executive decision

Feature 004 is a breaking public-contract redesign. It will therefore ship as
`isanlp_rst` **5.0.0**, with serialized production contract
`isanlp_rst.production` **2.0.0**. Calling the release 4.0.1 would misrepresent
the compatibility change: [Semantic Versioning 2.0.0](https://semver.org/)
requires a new major version when a declared public API changes incompatibly.

The design remains one local Python library. It does not introduce a service,
a consumer-specific schema, a second preparation authority, or any change to
trained architecture or inference mathematics.

## Evidence base

The comparison used current primary sources and direct inspection of the
repository at `ad853825535649fc55fe2ab12e83654bb213097d` after the
ModernBERT production upgrades completed:

- Python 3.14 installed-distribution metadata, exception chaining, import
  resources, signatures, and public-interface semantics;
- Pydantic 2.13 strict models, discriminated unions, serialization-mode JSON
  Schema, and explicit serialization;
- JSON Schema Draft 2020-12;
- RFC 8785 canonical JSON, RFC 7493 I-JSON, and SHA-256;
- Python packaging metadata, wheel and source-distribution specifications,
  isolated build reports, and pip inspection;
- SemVer compatibility and W3C PROV concepts.

“State of the art” in this feature means that the production API applies the
strongest relevant current practices listed above. It does not claim that
`isanlp_rst` defines a general industry standard.

## Current implementation baseline

The current implementation already has strong foundations:

- all six source forms enter through `SourceArtifact`;
- preparation inventories content and records dispositions internally;
- exact-commit builds use `git archive` rather than mutable checkout bytes;
- model releases can carry immutable byte-level identities;
- cache writes are atomic and validate stored result identities;
- strict, frozen Pydantic models and RFC 8785 hashing are already dependencies.

The central defect is not parsing capability. The public API discards or
reduces provider-owned evidence that the implementation already creates.
`ProductionIngestor.prepare()` returns only the prepared document; analysis
reduces the source contract, policy, plan, inventory, and model identity to
partial receipts or digests; retained content is reachable only by identifier;
and failures are neither versioned nor able to carry typed completed-stage
evidence. Capability discovery and a machine-readable public-surface inventory
do not exist. The current wheel and sdist are ignored rather than durable
repository content.

## Dated production-practice comparison

| Practice | Current production practice, checked 2026-08-29 | Current `isanlp_rst` gap | Feature 004 disposition |
|---|---|---|---|
| Strict typed values | Pydantic supports strict, frozen, closed models and explicit tagged unions ([configuration](https://docs.pydantic.dev/latest/api/config/), [unions](https://docs.pydantic.dev/latest/concepts/unions/)) | Models are frozen and closed, but state-dependent optional fields and incomplete nested strictness still permit weak states | Use one shared strict base and explicit discriminated success and failure variants |
| Complete provider evidence | Typed domain contracts expose decision inputs and results, not only fingerprints | Inventory, policy, plan, source contract, retained values, and model identity are dropped or digest-only | Return complete `PreparationOutcome`; embed it in analysis outcomes; retain full typed representations |
| Decision-complete inference | Explainable production contracts preserve the selected decision, confidence meaning, uncertainty, and stable links to the returned structure | Primary split/relation/nuclearity scores, segmentation boundary scores, and entropy can be reduced to the final tree; marker refinement can overwrite the original decision | Add typed primary decision and refinement evidence, with decision-complete default and explicit distribution detail |
| Lossless backend handoff | A public adapter must preserve the semantic output of the backend it wraps and disclose any lossy input transformation | A backend can compute a full decoded structure while an adapter returns only a projection; capping, truncation, or approximate token allocation can be hidden | Add exact `AnalysedDocument`, fail-closed loss policy, and deliberate evidence-removal conformance tests for every backend/handoff |
| Composite analysis identity | Reproducible composite inference identifies every learned, calibrated, decoded, rule-based, inventory, and ontology component that affects a result | A primary release identity does not identify marker refinement, eRST scorer/decoder/calibration, relation inventory, or ontology mapping | Add one composite identity whose participating components are explicit and semantic |
| Decision and validation receipts | Constraint decoders, graph recombination, and validation should return inspectable typed evidence of the decisions and checks they performed | eRST decode receipts and stitching inputs/mappings can be discarded; validation currently returns only pass/fail behaviour | Expose eRST decode, recombination, and validation receipts with stable check/decision identifiers and recomputable digests |
| Deterministic identity | RFC 8785 defines invariant I-JSON bytes suitable for hashing ([RFC 8785](https://www.rfc-editor.org/rfc/rfc8785.html)) | Semantic hashing uses RFC 8785 in places, but public JSON persistence and digest projection are not one documented contract | Canonicalize every top-level persisted record; document the exact semantic projection; separate semantic and execution evidence |
| Published schemas | Pydantic can generate serialization-mode JSON Schema; Draft 2020-12 is the current JSON Schema dialect ([Pydantic JSON Schema](https://docs.pydantic.dev/latest/concepts/json_schema/), [Draft 2020-12](https://json-schema.org/draft/2020-12)) | No committed public schemas or byte-parity gate | Generate, package, commit, and parity-test schemas from runtime models |
| Compatibility | SemVer requires a precise public API and a major bump for incompatible changes ([SemVer](https://semver.org/)) | Package remains 4.0.0 despite the proposed breaking contract; loaders have no compatibility registry | Release package 5.0.0 and contract 2.0.0; one write version, explicit readable versions, fail-closed dispatch |
| Installed identity | `importlib.metadata` provides installed version, requirements, and file hashes from distribution metadata ([Python 3.14](https://docs.python.org/3.14/library/importlib.metadata.html)) | Package version is duplicated in `pyproject.toml` and `_version.py` | Use installed distribution metadata at runtime and retain the build version only in package metadata |
| Public API authority | Python public interfaces use explicit exports; typing and metadata distinguish public imports ([PEP 8](https://peps.python.org/pep-0008/#public-and-internal-interfaces), [Core Metadata](https://packaging.python.org/en/latest/specifications/core-metadata/)) | `__all__` exists but no inventory reconciles exports, schemas, statuses, errors, and docs | Add one declarative public-surface inventory and reconcile it with runtime-derived signatures and generated projections |
| Typed failures | Python exceptions support structured attributes and explicit causal chaining ([Python exceptions](https://docs.python.org/3.14/tutorial/errors.html#exception-chaining)) | `ProductionIngestError` has free text, no retryability or safe cause chain, and no completed-stage evidence | Exception hierarchy wraps immutable, serializable failure records; stage-specific types constrain completed evidence |
| Capability discovery | Installed metadata and optional extras can be inspected without importing expensive providers | No model-free capability contract; missing format extras leak `ModuleNotFoundError` | Add offline discovery that reports all forms, availability, required extras, parser identity state, and cache eligibility |
| Artifact integrity | Wheel `RECORD` hashes files inside a wheel; it does not prove the external artifact or source revision ([wheel specification](https://packaging.python.org/en/latest/specifications/binary-distribution-format/)) | Build receipt is stdout-only; `dist/` is ignored; local artifacts identify an older revision | Track versioned wheel, sdist, canonical receipt, and receipt digest under `dist/5.0.0/` |
| Reproducible build | Isolated build reports and `SOURCE_DATE_EPOCH` support independently comparable artifacts ([PyPA build](https://build.pypa.io/en/latest/reference/cli.html), [SOURCE_DATE_EPOCH](https://reproducible-builds.org/specs/source-date-epoch/)) | Exact-commit build is strong but not double-built or receipt-governed | Build twice from the named source commit, require identical artifact hashes, and persist the combined report |
| Clean installed proof | `pip check` and stable `pip inspect` JSON verify installed dependency state ([pip check](https://pip.pypa.io/en/stable/cli/pip_check/), [pip inspect](https://pip.pypa.io/en/stable/reference/inspect-report/)) | Existing clean-install proof can inherit system packages and does not exercise Feature 004 | Test exact tracked wheel in isolated core and formats environments with checkout-path exclusion and networking disabled during acceptance |
| Provenance | W3C PROV distinguishes entities, activities, agents, and plans ([PROV-DM](https://www.w3.org/TR/prov-dm/)) | Evidence exists but lifecycle provenance is incomplete or digest-only | Apply the concepts to typed source, preparation, inference, validation, and distribution evidence without exposing a generic PROV graph |

Every material comparison gap has a disposition. No open decision remains for
planning.

## Provider-value retention audit for this revision

The revision inspected the production contract and every active ModernBERT
analysis handoff, not merely the final `RstAnalysis` shape. The inspected
checkout was clean and matched `origin/master`; these observations establish
the implementation baseline but do not certify a future 5.0.0 release:

- the ModernBERT primary decoder now preserves the complete decoded span set
  through recursive tree construction; Feature 004 therefore treats full tree
  depth as a verified baseline and a protected non-regression, not as a current
  missing feature;
- the active primary pipeline computes segmentation logits, split choices,
  relation/nuclearity logits and selected CKY decisions, but the public parser
  result retains only the graph and an aggregate tree score rather than the
  decision-linked evidence;
- paragraph segmentation silently tokenizes with a 512-token maximum and
  truncation, then extends the final EDU over the unanalysed suffix; the parser
  separately tokenizes with an 8,192-token maximum, caps the document at 128
  EDUs, and allocates EDU token spans uniformly rather than from tokenizer
  offsets;
- when decoded spans or source alignment are missing, the parser facade can
  synthesize midpoint splits, `elaboration`/`NS` decisions, and sequential
  character offsets, producing apparently analysed structure for content that
  did not reach the model;
- a validated local `model_dir` is passed to `PredictorModernBERT` but is not
  retained or used there; the predictor loads its fixed Hugging Face model ID
  and revision instead, so reported release identity can differ from the bytes
  actually executed;
- the parser facade advertises archived DMRST and UniRST family/version names
  even though construction rejects them; capability discovery must describe
  only executable production capabilities;
- relation-marker refinement can replace model relation, concept, nuclearity,
  or confidence without preserving the original decision and trigger;
- eRST scoring and decoding create signal-gated candidates, edge probability,
  relation probability, joint ordering score, calibration context, and an
  `ErstDecodeReceipt`, while the completion path retains only a subset;
- signal identities can become disconnected from accepted secondary edges, and
  the canonical prepared document does not yet guarantee the complete token
  substrate required by signal detection;
- hierarchical stitching can discard local result identities, local-to-global
  maps, nuclear-spine inputs, warnings, and timings;
- analysis validation has no typed receipt even though a successful return
  depends on its checks;
- relation labels and confidence values do not consistently declare scheme,
  confidence kind, calibration, and ontology-mapping provenance;
- `ProductionIngestor` consumes the graph-only `parse_document()` projection,
  creates relation anchors from only the parent/source endpoint, and hashes a
  model identity without proving that it names the loaded runtime bytes;
- hierarchical stitching preserves the recombined graph but drops local result
  identities, complete local-to-global evidence, nuclear-spine inputs, local
  warnings, and component timings;
- eRST candidate generation now streams every signal-sufficient candidate
  without the former membership cap, so Feature 004 protects complete
  candidate membership rather than describing candidate truncation as a
  current gap.
- the newly installed `isanlp-rst` CLI is another public production boundary,
  but its parse command currently runs inference twice, ignores its detected
  structured-input format, emits an independent partial JSON schema labelled
  `1.0`, and omits most provider evidence; its local HTTP adapter returns only
  counts and serializes raw exception strings. Both must project the canonical
  Python contracts rather than become independent semantic authorities.

These are provider-owned values because `isanlp_rst` creates or uses them to
select, refine, validate, or assemble its own result. The revision does not
require evidence that exists only in a downstream workflow.

## Decision 1: Success and failure algebra

### Selected outcome algebra

Use separate, closed contract families:

- `PreparationOutcome` is the successful, intentional preparation-only result.
  Calling `prepare()` is the explicit intentional-non-analysis path.
- `ProductionAnalysisOutcome` is a discriminated union of
  `AnalysedOutcome` and `EmptyPrimaryAnalysisOutcome`.
- `ProductionFailure` is a discriminated hierarchy that includes provider
  unavailability and processing failures by lifecycle stage.
- `ProductionIngestError` wraps one `ProductionFailure` and uses Python
  exception chaining for the in-process cause.

This makes every documented analysis status reachable without treating an
invalid or unavailable analysis as success. Failure records remain
deterministically serializable even though the Python API raises them.

### Rejected outcome alternatives

- One result with many optional fields: invalid combinations remain
  representable.
- A five-variant success result containing failures: conflicts with idiomatic
  Python errors and risks caching failed work as a result.
- Exceptions without payloads: cannot be persisted or compared reliably.
- Treating missing parser configuration as “not analysed”: conflates an
  intentional `prepare()` call with provider unavailability during
  `analyse()`.

## Decision 2: Contract model discipline

### Selected model discipline

All persisted nested models use the same Pydantic configuration:

```python
ConfigDict(
    strict=True,
    extra="forbid",
    frozen=True,
    validate_default=True,
    revalidate_instances="always",
    allow_inf_nan=False,
    ser_json_bytes="base64",
    val_json_bytes="base64",
)
```

Persist tuples and frozen nested values, not mutable containers or unordered
sets. Use `Literal` discriminator fields and explicit discriminated unions.
Represent semantic ratios exactly as integer counts plus a derived display
ratio; binary floating-point values do not define semantic identity.

### Rejected modelling alternatives

- Frozen standard-library dataclasses alone: no strict recursive validation,
  discriminated serialization, or schema generation.
- Pydantic smart unions: selection is heuristic and may change between minor
  releases.
- Arbitrary extension dictionaries: future readers could silently discard or
  misinterpret semantic evidence.

## Decision 3: Complete preparation evidence

### Selected preparation evidence

`PreparationOutcome` contains the complete provider-owned preparation account:
source artifact summary and contract, explicit policy and planning policy, full
inventory, one final disposition per item, duplicate links, explicit
transformation records, typed content representations, prepared discourse,
source mapping, structural boundaries, exact coverage, warnings, optional
subdivision plan, and semantic identity.

The canonical disposition is embedded once in its inventory item. A public
computed disposition view may be provided, but serialization must not maintain
two independently editable copies.

Typed representations preserve the source semantics `isanlp_rst` actually
harvests: text, table, list, metadata, note/caption, media reference, structural
container, and cross-reference. This feature exposes those values; it does not
change Docling or DocLang interpretation. If implementation later touches
harvesting or format semantics, the mandatory current upstream-spec check is
triggered before that edit.

## Decision 4: Validation and atomicity

### Selected validation boundary

Validate before returning success or writing the cache:

- every valid discovered item has exactly one final disposition;
- primary plus retained coverage is complete and unexplained coverage is zero;
- mappings and anchors are in bounds and reconstruct analysed text;
- the primary RST structure is connected, acyclic, and single-rooted;
- secondary edges meet eRST DAG constraints;
- every analysis unit is present exactly once in deterministic recombination;
- model, request, plan, and result identities agree.

Multi-unit inference may hold internal partial unit evidence during execution,
but it never returns or stores partial success as a complete outcome.

## Decision 5: Canonical persistence and compatibility

### Selected persistence contract

Every top-level persisted record uses this envelope:

```json
{
  "contract": "isanlp_rst.production",
  "contract_version": "2.0.0",
  "kind": "preparation_outcome",
  "semantic": {},
  "execution": {},
  "semantic_digest": {
    "algorithm": "sha256",
    "hex_digest": "..."
  }
}
```

The exact digest input is RFC 8785 canonical bytes for `contract`,
`contract_version`, `kind`, and `semantic`. The digest field and all execution
evidence are excluded. Duplicate JSON keys, invalid Unicode, NaN/Infinity,
unknown fields, and unsupported versions fail before semantic use.

Runtime models are the field/type authority. Serialization-mode Draft 2020-12
schemas are deterministic committed projections and must byte-match generated
output. The loader uses an explicit compatibility registry: one write version,
named readable versions, explicit migrations only, and fail-closed rejection
of unsupported future or old major versions.

## Decision 6: Public surface and capability discovery

### Selected discovery authority

Add one machine-readable public-surface manifest for membership,
classification, public import path, kind, introduced/deprecated versions,
schema membership, documentation anchor, and compatibility guarantee. Runtime
signatures and model schemas remain code-derived facts; reconciliation tests
join both sources and fail on drift. Generated schema and documentation tables
are projections, not competing authorities.

Expose `describe_capabilities(parser=None)` and
`ProductionIngestor.capabilities()`. Discovery reports package and contract
versions, lifecycle operations, every source form and availability, missing
optional distributions and install extra, persistence guarantees, parser
capacity, model-identity state, and semantic-cache eligibility. It must not
load an adapter or model, resolve weights, access research code, or use a
network.

## Decision 7: Distribution and release receipt

### Selected release contract

Use `dist/5.0.0/` as durable, version-controlled release content:

```text
dist/5.0.0/
├── isanlp_rst-5.0.0-py3-none-any.whl
├── isanlp_rst-5.0.0.tar.gz
├── release-receipt.json
└── release-receipt.sha256
```

Remove the blanket `dist/` ignore. Build scratch directories remain outside
the repository, so `dist/` contains only promoted artifacts. Build twice from
the same verified source commit with `SOURCE_DATE_EPOCH` set from that commit;
require identical wheel and sdist hashes. Build the wheel through the sdist to
prove source completeness.

The canonical release receipt records package and contract versions, exact
source revision and source state, Python/build frontend/backend/platform/lock
identity, artifact names/kinds/sizes/SHA-256 hashes/tags, and named verification
results with evidence digests. A detached SHA-256 covers the receipt. Wheel
`RECORD` remains the authority for files inside the wheel; the release receipt
covers the external artifacts and source/build relationship.

The release sequence is intentionally staged: a clean source release commit is
built; its immutable wheel and sdist are added in an untagged candidate commit;
the second machine verifies those exact committed artifact bytes; and the final
receipt and detached digest are added in a certification commit. The release
tag points to the certification commit while the receipt identifies the source
commit whose bytes were built and the unchanged artifact digests verified on
both machines. The second machine then verifies the tagged receipt and unchanged
artifact bytes, and that proof is added in a post-certification evidence commit
that neither moves the release tag nor changes any certified byte. Candidate
verification is an input to the receipt; final receipt verification cannot be
an input to the receipt it verifies.

## Decision 8: Clean-install and conformance proof

### Selected installation proof

Use two genuine isolated environments:

1. core wheel only;
2. wheel plus `isanlp_rst[formats]` dependencies.

Install the exact tracked wheel by path, run acceptance with networking
disabled, execute Python with `-I` from a temporary directory, and prove no
module was imported from the checkout. Verify receipt hashes, package/contract
versions, packaged provenance, public-surface reconciliation, capability
discovery, optional-dependency reporting, serialization/reload, all lifecycle
failures, `pip check`, and retained `pip inspect` environment evidence.

The second development machine installs and verifies the tracked wheel; it does
not rebuild the sdist.

## Decision 9: Typed analysis policy and exact analysed substrate

### Selected policy contract

`analyse()` accepts a closed `AnalysisPolicy`. The resolved policy is embedded
in the semantic outcome and contains:

- `output_formalism`: `rst_tree` or `erst_graph`;
- `evidence_detail`: `decision_complete` or `normalized_distributions`;
- marker-refinement policy;
- validation policy and version;
- relation-interpretation and ontology-mapping policy;
- lossy-input policy, whose production default is `forbid`.

The outcome exposes an `AnalysedDocument` containing the exact tokens, EDUs,
sentence/paragraph boundaries, token-to-EDU mapping, source anchors, and
fidelity records actually supplied to inference. Context truncation, EDU caps,
or approximate token allocation cannot be hidden inside an adapter. They either
fail closed or require an explicit policy and fully anchored transformation.

### Rejected alternatives

- Free-form output strings: invalid or unsupported formalism remains
  representable and semantic identity is ambiguous.
- Backend defaults not returned in the outcome: a consumer cannot reproduce the
  request.
- Returning prepared segments as a proxy for analysed tokens/EDUs: preparation
  and the actual inference substrate are not necessarily identical.

## Decision 10: Bounded decision evidence

### Selected evidence boundary

The default is `decision_complete`. It retains selected segmentation, split,
relation, nuclearity, eRST, refinement, recombination, and validation decisions;
provider-computed confidence; uncertainty such as normalized split entropy;
and the stable evidence/receipt links required to explain the final graph.

`normalized_distributions` additionally retains the finite normalized split,
relation, nuclearity, and boundary distributions that the active backend
genuinely computes. The policy participates in semantic request and cache
identity because returned semantic evidence differs.

Raw tensors, embeddings, hidden activations, unrestricted cubic charts,
training-only gold labels, corpus records, and private workbench state remain
internal. The API does not fabricate a distribution for a backend that does not
produce one.

## Decision 11: Refinement and eRST provenance

Every post-model refinement is a before/after record linked to the original
decision, revised decision, trigger signal or rule, policy identity, algorithm
identity, and affected graph elements. Overwrite-without-trace is invalid.

Every eRST accepted edge retains its candidate identity, both endpoints,
supporting signal identities, edge probability, selected relation and relation
probability, joint selection score, calibration identity, decoder policy, and
decoder receipt. Rejected candidates are retained at the selected evidence
level. Signals and decisions are linked in both directions so returned signals
cannot be orphaned.

## Decision 12: Composite identity, recombination, and validation

The semantic result contains one `CompositeAnalysisIdentity` whose components
cover every participating primary parser, segmenter, marker refiner, eRST
detector/scorer, decoder, calibration, relation inventory, and ontology mapping.
Absent components are explicitly `not_used`, not omitted ambiguously.

Multi-unit analysis returns a compact `RecombinationReceipt`: local result
identities, complete local-to-global mappings, boundary/nuclear-spine inputs,
deterministic stitching decisions, warnings, timings, and digest. It does not
duplicate complete local graphs unless a future evidence policy explicitly
requests them.

Every success returns a `ValidationReceipt` containing the policy/version,
stable check identifiers, outcomes and counts, overall disposition, warnings,
and digest. A required failed check makes construction of a success outcome
impossible.

## Decision 13: Canonical public parser result and runtime-byte identity

The package-level parser facade exposes a canonical typed
`ParserAnalysisResult` for callers that already have an `RstDocument`. It
contains the exact analysed substrate, validated graph, primary/eRST evidence,
refinements, composite component identity, optional recombination receipt,
validation receipt, execution evidence, and semantic identity. The existing
graph-only `parse_document()` operation may remain as a documented convenience
projection, but production ingest consumes `ParserAnalysisResult` directly and
must not reconstruct provider evidence from `RstAnalysis`.

Immutable component identity is an execution invariant, not a manifest claim.
The runtime loader must reconstruct the primary parser, segmenter, eRST scorer,
tokenizers, decoder/calibration configuration, relation inventory, rules, and
ontology mapping from the exact validated byte inventories reported in the
composite identity. Path or revision substitution, including validating a
local release and then loading a fixed remote model identifier, is a typed
failure. Capability discovery reports only families and evidence levels that
can execute through this canonical result path.

## Decision 14: Installed CLI and local HTTP projections

The installed `isanlp-rst` command is a supported projection of the same
provider contract. Structured files enter through `SourceArtifact` and
`ProductionIngestor`; already-constructed document requests use
`ParserAnalysisResult`. One invocation performs inference once. JSON output is
the canonical serialized contract, while tree, statistics, and RS3 output are
explicit presentation projections with no compatibility claim beyond their
declared view contract.

If the loopback HTTP adapter remains installed, it uses the same typed request,
canonical success/failure records, safe serialization, and capability
description. It does not define a second JSON result, expose raw exception
strings, or represent counts as a complete analysis. No hosted deployment or
multi-user infrastructure is introduced by Feature 004.

## Rejected scope

| Candidate | Disposition |
|---|---|
| Consumer-specific fields or statuses | Rejected: downstream translation is downstream authority |
| Restored `parse_markdown`, `parse_docling`, or `parse_doclang` APIs | Rejected: shared source inventory remains the only public path |
| Durable caching for mutable/unidentified model instances | Rejected: no immutable model-byte identity exists |
| Full generic W3C PROV graph | Rejected: typed provider evidence is simpler and sufficient for one local library |
| Hosted signing, transparency log, or index attestation | Rejected for this local release; evaluate PEP 740 only if publication to a package index is requested |
| Mandatory format dependencies in the core wheel | Rejected: violates the explicit optional boundary |
| Model architecture or inference changes | Rejected: outside this feature and prohibited by FR-029 |

## Research closure

All Feature 004 unknowns are resolved. The plan contains no unresolved marker.
Implementation must re-open research only if it
changes source-format interpretation, adopts hosted publication, or discovers
that a planned contract value is not genuinely created or used by
`isanlp_rst`.

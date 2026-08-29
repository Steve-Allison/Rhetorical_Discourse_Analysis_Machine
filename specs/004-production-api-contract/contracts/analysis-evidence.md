# Contract: Decision-Complete Analysis Evidence

**Package release**: `isanlp_rst` 5.0.0  
**Serialized contract**: `isanlp_rst.production` 2.0.0  
**Scope**: Provider-owned evidence created or used by production inference,
refinement, secondary-edge completion, recombination, and validation

## Contract objective

A final discourse graph is not the complete provider result. The production
contract preserves enough stable evidence to identify the exact analysed
substrate, explain every returned decision, distinguish model output from later
refinement, reproduce deterministic assembly and validation, and detect loss at
every backend handoff.

This contract does not expose scientific implementation state merely because it
exists in memory. Raw tensors, embeddings, activations, unrestricted parsing
charts, training-only gold labels, corpus records, and private workbench state
remain internal.

## Analysis policy

`AnalysisPolicy` is a strict closed semantic value with these required fields:

| Field | Allowed values | Default |
|---|---|---|
| `output_formalism` | `rst_tree`, `erst_graph` | `rst_tree` |
| `evidence_detail` | `decision_complete`, `normalized_distributions` | `decision_complete` |
| `marker_refinement` | closed versioned provider policy | production default |
| `validation` | closed `ValidationPolicy` | production strict |
| `relation_interpretation` | closed relation/ontology policy | production default |
| `lossy_input` | `forbid` or an explicitly authorized closed policy | `forbid` |
| `policy_version` | semantic version | current contract value |
| `semantic_digest` | recomputable SHA-256 identity | derived |

The complete resolved policy is embedded in `AnalysisRequest` and the result.
No backend default remains implicit. Any policy change that alters returned
semantic evidence changes semantic request, result, and cache identity.

## Exact analysed document

`AnalysedDocument` is the exact semantic substrate supplied to inference. It
contains:

- ordered analysed tokens with exact text, analysed-text offsets, source
  anchors, sentence/paragraph membership, and transformation links;
- ordered EDUs with exact text, token membership, prepared segment links,
  sentence/paragraph membership, and source anchors;
- complete token-to-EDU, sentence, paragraph, and structural-boundary mappings;
- prepared-to-analysed mapping and exact coverage;
- every authorized substrate transformation and its fidelity classification;
- a recomputable semantic digest.

The following are invalid when hidden:

- tokenizer context-window truncation;
- fixed EDU caps;
- silent segment or token dropping;
- uniform or approximate token ranges allocated after inference;
- inferred source anchors that cannot reconstruct the analysed text.

With `lossy_input=forbid`, any lossy transformation is a typed preparation or
inference failure. A future explicit lossy policy must identify affected
content, exact transformation, source anchors, coverage deficit, and semantic
identity; it may not convert loss into an unexplained warning.

## Primary inference evidence

### Segmentation

Each `SegmentationDecisionEvidence` records:

- stable decision and boundary identities;
- analysed token boundary and source anchors;
- selected boundary/non-boundary value;
- provider-computed confidence with declared `confidence_kind`;
- normalized boundary distribution when requested and genuinely produced;
- resulting EDU identifiers;
- segmenter component identity.

If the provider receives presegmented EDUs and performs no segmentation, the
component state and evidence state are explicitly `not_used`.

### Structure, relation, and nuclearity

Each `PrimaryStructureDecisionEvidence` records:

- stable decision identity and analysed span;
- selected split or attachment;
- resulting node and primary-edge identifiers;
- selected nuclearity;
- selected relation as `RelationInterpretation`;
- provider confidence values and their meaning;
- normalized split entropy when the backend computes it;
- requested split, relation, and nuclearity distributions when genuinely
  produced;
- producing component identity.

Every final primary node and edge must link to its creating decision. Every
decision must resolve to final graph elements or a typed rejection/supersession
record. A parser adapter may not return only a root or shallow projection when
the backend decoded a deeper tree.

### Scores and distributions

Every public score uses `ScoreValue` and declares:

- value and finite range;
- `confidence_kind`, such as calibrated probability, uncalibrated probability,
  logit-derived margin, entropy, or deterministic rule confidence;
- producing component;
- calibration identity or explicit `not_calibrated` state.

`NormalizedDistribution` is permitted only at
`evidence_detail=normalized_distributions`. Entries are labelled, ordered by a
declared semantic rule, finite, in range, and normalized within the contract
tolerance. The contract never fabricates a distribution from the selected
label alone.

## Refinement provenance

Any marker, rule, relation primer, ontology adapter, or other post-model step
that changes a selected value emits one `RefinementRecord` with:

- original complete decision value;
- revised complete decision value;
- trigger signal/rule identities and anchors;
- refinement policy and algorithm identities;
- affected decision, node, and edge identifiers;
- stable explanation code;
- semantic digest.

The original model relation, concept, nuclearity, or confidence remains
inspectable. A component may affirm an unchanged value without creating a
refinement; it may not overwrite a changed value without a record.

## Relation interpretation

Every primary or secondary relation uses `RelationInterpretation`:

- raw label;
- declared relation scheme and inventory identity;
- selected ontology concept when genuinely mapped;
- mapping status: `mapped`, `identity_only`, `not_mapped`, or `not_available`;
- mapping algorithm/version and ontology version/digest when applicable;
- confidence and calibration semantics.

Copying a raw label into a concept field is `identity_only`; it is not evidence
that ontology mapping occurred.

## eRST completion evidence

Every signal has a stable identity, kind, analysed/source anchors, detector
identity, and back-links to the candidate or accepted edge decisions it
supports.

Every `ErstCandidateDecision` records:

- candidate identity and both endpoint node identifiers;
- supporting signal identities;
- edge probability;
- selected relation interpretation and relation probability;
- joint selection score used for deterministic ordering;
- scorer and calibration identities;
- decoder order;
- accepted secondary-edge identifier or stable rejection reason.

`ErstDecodeReceipt` preserves the provider decoder's complete stable account:
policy/version, ordered candidate decision identities, input/accepted/rejected
counts, constraint check counts, rejection-reason counts, deterministic order
identity, warnings, and digest. A successful empty accepted-edge set still has a
receipt proving decoding completed.

`ErstCompletionEvidence` contains signals, candidate decisions at the selected
evidence level, the exact decode receipt, scorer/calibration identity, relation
inventory identity, and digest. Accepted edges link to both endpoints and every
supporting signal. No returned signal may be orphaned.

## Composite component identity

`CompositeAnalysisIdentity` explicitly identifies every participating:

- primary parser;
- segmenter;
- marker refiner;
- eRST detector;
- eRST scorer and checkpoint;
- eRST decoder and policy;
- calibration parameters;
- relation inventory;
- ontology mapping.

Non-participating components are `not_used`. Participating components are
`immutable_release`, `mutable_instance`, or `unidentified`. Durable semantic
caching requires immutable identity for every participating component, not
only the primary parser.

## Recombination receipt

For subdivided analysis, `RecombinationReceipt` contains:

- ordered analysis-unit and local result identities;
- complete local-to-global segment, node, primary-edge, and secondary-edge
  mappings;
- boundary and nuclear-spine inputs used by stitching;
- deterministic stitching decisions and stable rationale codes;
- warnings and execution timings;
- recombination policy/version and semantic digest.

Every local semantic element maps exactly once or has a typed rejection record.
The default contract does not duplicate full local graphs because their stable
identities and complete mappings are sufficient to explain the final graph.

## Validation receipt

Every successful result contains `ValidationReceipt` with:

- validation policy/version;
- ordered stable check identifiers;
- required/advisory classification;
- per-check outcome, counts, and affected identifiers;
- graph, anchor, evidence, and mapping coverage totals;
- stable warnings;
- overall `passed` disposition;
- recomputable semantic digest.

Required checks cover source/substrate identity, primary tree, eRST DAG,
decision-to-graph links, refinements, both-endpoint anchors, signals/candidates,
composite identity, recombination, semantic identities, and cache agreement. A
required failed check makes a success outcome unconstructable.

## Backend handoff conformance

Every production backend and handoff must pass loss-audit fixtures:

1. backend output to parser facade;
2. parser facade to production ingest;
3. segmentation to analysed document;
4. primary inference to relation refinement;
5. primary result to eRST candidate generation/scoring/decoding;
6. analysis units to hierarchical recombination;
7. assembled outcome to validation;
8. validation to serialization and cache reload.

Tests deliberately remove one decoded span, score, boundary, refinement,
signal link, decoder receipt, local mapping, or validation check and require the
handoff or final validator to fail. A backend that cannot produce a required
value reports the capability as unavailable; an adapter cannot invent it.

## Semantic and execution boundary

The analysed document, resolved policy, decisions, refinement records,
candidate decisions, decoder receipt, composite identity, relation
interpretation, recombination decisions/mappings, validation checks, and their
digests are semantic.

Wall-clock timings, device, host-independent execution identifiers, cache
hit/miss status, and local diagnostic values are execution evidence. Receipt
timings remain exposed but are excluded from semantic digest projections.

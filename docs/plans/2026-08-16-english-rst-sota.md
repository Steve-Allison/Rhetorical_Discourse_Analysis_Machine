# English RST Capability Platform — 2026 world-class plan

**Status:** Capability architecture and delivery proposal (not started)
**Date:** 2026-08-16
**Driver:** Steve Allison
**Purpose:** Give Steve's projects one dependable, semantically governed English RST capability: classical RST trees, eRST graphs, lossless label mappings, confidence, provenance, document-format integration, and practical local inference.
**Scope:** English. Raw text, provided EDUs, and document-native inputs. RST-DT trees and GUM eRST are quality and interoperability reference points, not the product itself.
**Out of scope:** Multilingual SOTA as a release gate; a mandatory 70B runtime; a second local ontology authority; redistribution of licensed corpora or incompatible code.

---

## Product statement

This is not an implementation-grade research programme. It is a plan for a
world-class RST capability that other projects can call and trust.

Research benchmarks answer, “How do we know the capability is good?” They do
not answer, “Why does the capability exist?” A consumer should be able to submit
a document and receive a stable, typed, ontology-aligned representation of its
discourse structure without knowing which corpus, parser family, spelling,
model class index, or file format produced it.

The north-star call is:

```python
document = RstDocument.from_text(text, source=source_ref)
analysis = rst.analyse(document, output="erst_graph")
```

The returned analysis must serve downstream retrieval, knowledge-graph,
content, learning, document-understanding, and generation systems—not merely an
evaluation script.

## What “world-class” means

| Dimension | Required capability |
|---|---|
| Semantic | Classical RST tree plus eRST secondary edges and anchored signals; no flattening to an unlabeled tree |
| Interoperable | Canonical Central_Configs ontology release; complete mappings for corpus labels, enums, aliases, structural pseudo-labels, and model encodings |
| Reliable | Typed results and failures, confidence and calibration, deterministic serialization, provenance, and no silent unmapped labels |
| Document-aware | Original text, token and EDU offsets, sentence/paragraph boundaries, table sub-analyses, source references, and format-native projections |
| Operational | Encoder-scale default; CPU, MPS, and CUDA paths; bounded long-document behaviour; batch and cache support; optional enhanced models |
| Proven | Reproducible scorer parity, corpus/version manifests, genre and long-document evaluation, benchmark quality, and regression evidence |

The ambition remains 2026 SOTA. Model results do not compensate for an
incomplete capability contract, and a polished API does not compensate for weak
discourse analysis.

---

## Authority and ownership

### One ontology authority

Central_Configs is the sole upstream ontology authority. This project must not
copy its authored ontology, create a compatibility ontology, or mint competing
identifiers.

The RST work therefore requires a **Central_Configs RST/eRST ontology module**
and an immutable Central release. `isanlp_rst` consumes that release by version
and digest and owns only operational behaviour.

| Central_Configs owns | `isanlp_rst` owns |
|---|---|
| Canonical identifiers and definitions | Parsing, segmentation, tree construction, graph completion, and scoring |
| RST/eRST concepts, schemes, enums, aliases, and semantic mappings | Corpus readers and writers, including RS4 |
| Corpus, model-family, metric, scorer, and provenance vocabulary | Model class-index encodings and checked runtime adapters |
| LinkML authority and generated release projections | Public Python API and dependency-light runtime models |
| Deprecation, replacement, versioning, and release digest | Pinned ontology lock and consumer conformance tests |

**Verified 2026-08-16:** Central declares
`ontology/schema/coe.linkml.yaml` as its canonical import closure,
`ontology/data/release.yaml` as an `OntologyRelease`, generated projections in
`dist/ontology/<version>/`, and `release_status: working` for 4.0.0. This plan
must not describe 4.0.0 as an immutable released dependency. The RST module must
enter the next approved Central release; its version is a Central stewardship
decision.

### Proposed Central extension

```text
Central_Configs/
  ontology/schema/modules/discourse.linkml.yaml
  ontology/data/domains/language/discourse/rst_ontology.yaml
  ontology/data/domains/language/discourse/rst_mappings.yaml
  ontology/data/domains/language/discourse/rst_quality.yaml
  ontology/data/release.yaml                         # include the bundle
  ontology/data/stewardship/consumer-registry.yaml  # register isanlp_rst
```

These paths are proposed, not yet authoritative. Reconcile them with Central's
domain registry before creation. Extend the existing `coe` namespace,
`IdentifiedThing`, terminology/sense model, relation model, governance model,
and release pipeline; do not build a separate `rst:` authority beside it.

`isanlp_rst` should add only a lock and generated/operational consumers:

```text
config/ontology/central.lock.yaml
isanlp_rst/ontology/    # release loader + checked adapters
isanlp_rst/contracts/   # dependency-light public result types
isanlp_rst/eval/        # pure scorers
isanlp_rst/erst/        # RS4 I/O + graph completion
```

Generated artifacts are never hand-edited. Central authors LinkML and data,
uses official LinkML generation/validation, publishes the manifest and digest,
and this repository proves it consumes that exact release offline.

---

## Normative ontology profile

This is the required semantic content of the Central extension. Names below are
**proposed semantic keys**, not permission for this repository to mint final
`coe:` identifiers. Central must assign and release the canonical IDs.

### Core classes

| Class | Required meaning and fields |
|---|---|
| `DiscourseFormalism` | RST tree or eRST graph; identifier, version, specification source |
| `AnnotationScheme` | Corpus/model vocabulary; scheme ID, version, formalism, authority, licence, source |
| `RelationConcept` | Stable concept; canonical label, definition, arity, structure, broader/narrower concepts |
| `RelationLabel` | Exact scheme-bound value; case-sensitive literal, scheme, concept, relation type |
| `MappingAssertion` | Source, target, mapping kind, lossiness, constraints, evidence, version |
| `SignalTypeConcept` | eRST signal type and definition |
| `SignalSubtypeConcept` | Signal subtype, parent type, definition |
| `CorpusRelease` | Corpus ID, version/tag, split manifest, scheme, licence, digest |
| `ModelArtifact` | Model ID, revision/digest, family, training corpora, scheme, weights licence |
| `ScorerDefinition` | Scorer ID, version/commit, formalism, metric definitions, counting policy |
| `QualityMetric` | Metric concept, unit, direction, required input mode, scorer |
| `RstDocument` | Text, tokens, EDUs, boundaries, source reference, language, provenance |
| `DocumentToken` | Token ID, text, character offsets, sentence/paragraph membership |
| `Edu` | EDU ID, token IDs, character offsets, text, source anchors |
| `RstNode` | Node ID, node kind, EDU yield, character span, confidence |
| `PrimaryRelationEdge` | Edge ID, endpoints, relation, nuclearity pattern, confidence |
| `SecondaryRelationEdge` | Edge ID, endpoints, relation, confidence; no nuclearity |
| `DiscourseSignal` | Signal ID, edge ID, type/subtype, ordered token IDs, status, confidence |
| `RstAnalysis` | Input fingerprint, ontology/model/scorer provenance, graph/tree, timings, warnings |
| `ProvenanceRecord` | Producer, revisions/digests, source, timestamp, derivation, software version |

Primary and secondary edges are separate classes. One loose edge class would
permit invalid secondary-edge nuclearity. Signals use ordered token IDs, not a
single contiguous span: RS4 signals can be discontinuous, distant, or unanchored.

### Required enums

| Enum | Permissible values |
|---|---|
| `OutputFormalismEnum` | `rst_tree`, `erst_graph` |
| `InputModeEnum` | `raw_text`, `text_with_edus`, `text_with_tokens_and_edus`, `document_native` |
| `InputFidelityEnum` | `lossless`, `aligned`, `reconstructed`, `unknown` |
| `NodeKindEnum` | `edu`, `span`, `multinuclear_group`, `root` |
| `EdgeKindEnum` | `primary`, `secondary` |
| `NuclearityPatternEnum` | `NS`, `SN`, `NN` |
| `NuclearityRoleEnum` | `nucleus`, `satellite` |
| `RelationStructureEnum` | `mononuclear`, `multinuclear`, `structural_pseudo` |
| `RelationSchemeEnum` | `rst_dt_fine`, `rst_dt_coarse_18`, `gum_erst_fine`, `gum_erst_coarse`, `dmrst_rstdt_model_42`, `dmrst_gum_model_27`, `rs4_structural` |
| `MappingKindEnum` | `exact`, `alias`, `broader_projection`, `narrower_projection`, `model_encoding`, `structural`, `deprecated`, `unsupported` |
| `AnnotationStatusEnum` | `gold`, `silver`, `predicted`, `derived`, `imported`, `unknown` |
| `ConfidenceKindEnum` | `probability`, `calibrated_probability`, `margin`, `not_available` |
| `DeviceEnum` | `auto`, `cpu`, `mps`, `cuda` |
| `CapabilityStatusEnum` | `declared`, `implemented`, `verified`, `released`, `deprecated` |
| `FailureCodeEnum` | `invalid_input`, `alignment_failed`, `unsupported_scheme`, `unmapped_label`, `model_unavailable`, `resource_limit`, `scorer_mismatch`, `ontology_mismatch` |

Enum values are serialized keys. Display titles, corpus literals, aliases, and
ontology meanings are separate fields. Importers must retain the original
literal and must not silently lowercase, hyphen-normalize, or title-case it.

### RST-DT coarse 18 and fine-label mapping

Canonical coarse concepts:

```text
Attribution  Background  Cause  Comparison  Condition  Contrast
Elaboration  Enablement  Evaluation  Explanation  Joint  Manner-Means
Same-unit  Summary  Temporal  Textual-organization  Topic-Change
Topic-Comment
```

| Coarse concept | Fine labels |
|---|---|
| `Attribution` | `attribution`, `attribution-negative` |
| `Background` | `background`, `circumstance` |
| `Cause` | `cause`, `cause-result`, `consequence`, `result` |
| `Comparison` | `analogy`, `comparison`, `preference`, `proportion` |
| `Condition` | `condition`, `contingency`, `hypothetical`, `otherwise` |
| `Contrast` | `antithesis`, `concession`, `contrast` |
| `Elaboration` | `definition`, `elaboration-additional`, `elaboration-general-specific`, `elaboration-object-attribute`, `elaboration-part-whole`, `elaboration-process-step`, `elaboration-set-member`, `example` |
| `Enablement` | `enablement`, `purpose` |
| `Evaluation` | `comment`, `conclusion`, `evaluation`, `interpretation` |
| `Explanation` | `evidence`, `explanation-argumentative`, `reason` |
| `Joint` | `disjunction`, `list` |
| `Manner-Means` | `manner`, `means` |
| `Same-unit` | `same-unit` |
| `Summary` | `restatement`, `summary` |
| `Temporal` | `inverted-sequence`, `sequence`, `temporal-after`, `temporal-before`, `temporal-same-time` |
| `Textual-organization` | `textual-organization`, `textualorganization` |
| `Topic-Change` | `topic-drift`, `topic-shift` |
| `Topic-Comment` | `comment-topic`, `problem-solution`, `question-answer`, `rhetorical-question`, `statement-response`, `topic-comment` |

Fine-to-coarse projection is broader and lossy except where semantics are
identical. Retain the source literal. `textualorganization` is an alias spelling,
not a concept. Capitalization differences belong in scheme labels, not duplicate
concepts. Embedded-EDU variants (`-e`, e.g. `elaboration-additional-e`, `attribution-e`)
and nuclearity-tagged suffixes (`-s`, `-n`, e.g. `consequence-s-e`, `evaluation-s`)
frequently found in standard LDC `.dis` and `.rs3` sources are explicitly registered
in `rst_mappings.yaml` as alias mappings to canonical fine labels to guarantee
deterministic resolution without unmapped-label failures.

### GUM eRST fine labels and coarse projection

The GUM V12.1 RS4 header inspected on 2026-08-16 declares these 32 labels. The
release process must re-extract and compare the header from the pinned tag.

| Coarse family | Fine labels |
|---|---|
| `adversative` | `adversative-antithesis`, `adversative-concession`, `adversative-contrast` |
| `attribution` | `attribution-negative`, `attribution-positive` |
| `causal` | `causal-cause`, `causal-result` |
| `context` | `context-background`, `context-circumstance` |
| `contingency` | `contingency-condition` |
| `elaboration` | `elaboration-additional`, `elaboration-attribute` |
| `evaluation` | `evaluation-comment` |
| `explanation` | `explanation-evidence`, `explanation-justify`, `explanation-motivation` |
| `joint` | `joint-disjunction`, `joint-list`, `joint-other`, `joint-sequence` |
| `mode` | `mode-manner`, `mode-means` |
| `organization` | `organization-heading`, `organization-phatic`, `organization-preparation` |
| `purpose` | `purpose-attribute`, `purpose-goal` |
| `restatement` | `restatement-partial`, `restatement-repetition` |
| `same-unit` | `same-unit` |
| `topic` | `topic-question`, `topic-solutionhood` |

The 15 family projections are broader and lossy. The graph retains fine labels.
RST-DT and GUM are not flattened into one universal enum. Cross-scheme mappings
must be explicit and evidence-backed; lexical resemblance is not equivalence.

### Structural and nuclearity semantics

| Representation | Canonical interpretation |
|---|---|
| `NS` | left nucleus, right satellite |
| `SN` | left satellite, right nucleus |
| `NN` | both nuclei; permitted only for a multinuclear relation |
| child relation `span` | structural pseudo-label on the nucleus side; never a semantic concept |
| RS4 relation type `rst` | mononuclear semantic relation |
| RS4 relation type `multinuc` | multinuclear semantic relation |
| RS4 `secedge` | directed secondary relation; endpoints encode direction; no nuclearity |

Invalid combinations fail validation: `joint` with `NS`, a secondary edge with
nuclearity, `span` as a semantic prediction, or a mononuclear label with `NN`.

### Current model encodings

Model encodings are versioned adapter data, not concept IDs. Parse labels with
`rpartition("_")` so relation names remain intact.

GUM coarse model classes (27 values; the inherited comment incorrectly says 29):

```text
adversative_NN  adversative_NS  adversative_SN
attribution_NS  attribution_SN  causal_NS  causal_SN
context_NS  context_SN  contingency_NS  contingency_SN
elaboration_NS  evaluation_NS  evaluation_SN
explanation_NS  explanation_SN  joint_NN  mode_NS  mode_SN
organization_NS  organization_SN  purpose_NS  purpose_SN
restatement_NN  restatement_NS  same-unit_NN  topic_SN
```

RST-DT coarse model classes (42 values):

```text
Elaboration_NS  Attribution_SN  Joint_NN  same-unit_NN
Attribution_NS  Explanation_NS  Enablement_NS  Background_NS
Evaluation_NS  Cause_NS  Contrast_SN  Contrast_NN  Background_SN
Temporal_NN  Comparison_NN  Contrast_NS  Topic-Change_NN
Manner-Means_NS  textual-organization_NN  Temporal_NS  Condition_NS
Condition_SN  Cause_SN  Summary_NS  Topic-Comment_NN  Cause_NN
Summary_NN  Evaluation_SN  Temporal_SN  Explanation_SN  Enablement_SN
Topic-Comment_NS  Comparison_NS  Elaboration_SN  Manner-Means_SN
Comparison_SN  Summary_SN  Condition_NN  Topic-Comment_SN
Topic-Change_NS  Evaluation_NN  Explanation_NN
```

Every encoding record requires model artifact ID, class index, exact literal,
relation label/concept, nuclearity, validity constraints, and source revision.
Every live class maps exactly once.

UniRST multilingual inventory encodings (such as `eng.rst.rstdt` and `eng.erst.gum`
selected via `relinventory`) require matching versioned adapter records in the
Central ontology module alongside DMRST so multilingual models share the same
typed mapping, ontology resolution, and confidence extraction pipeline.

### Complete eRST signal inventory

| Signal type | Permitted subtypes |
|---|---|
| `dm` | `dm` |
| `graphical` | `colon`, `dash`, `items_in_sequence`, `layout`, `parentheses`, `question_mark`, `quotation_marks`, `semicolon` |
| `lexical` | `alternate_expression`, `indicative_phrase`, `indicative_word` |
| `morphological` | `mood`, `tense` |
| `numerical` | `same_count` |
| `orphan` | `orphan` |
| `reference` | `comparative_reference`, `demonstrative_reference`, `personal_reference`, `propositional_reference` |
| `semantic` | `antonymy`, `attribution_source`, `lexical_chain`, `meronymy`, `negation`, `repetition`, `synonymy` |
| `syntactic` | `causal_excess`, `infinitival_clause`, `interrupted_matrix_clause`, `modified_head`, `nominal_modifier`, `parallel_syntactic_construction`, `past_participial_clause`, `present_participial_clause`, `relative_clause`, `reported_speech`, `subject_auxiliary_inversion` |
| `unsure` | `unsure` |

A signal stores edge ID, exact type/subtype, ordered token IDs, and source status.
Empty token IDs are valid; discontinuous anchors remain discontinuous. Preserve
unknown source attributes in an extension bag, but reject unknown governed enum
values until an ontology release recognizes them.

### RS4 binding

| RS4 construct | Internal contract |
|---|---|
| `<segment id>` | `Edu`; preserve ID, text, parent, relation literal, token alignment |
| `<group type="span">` | `RstNode(kind=span)` |
| `<group type="multinuc">` | `RstNode(kind=multinuclear_group)` |
| node `relname="span"` | structural pseudo-label |
| node semantic `relname` | primary relation resolved through pinned scheme |
| `<secedge id source target relname>` | `SecondaryRelationEdge`; preserve edge ID |
| `<signal source type subtype tokens status>` | `DiscourseSignal`; source resolves to edge ID |
| header `<rel name type>` | relation inventory and constraint |
| header `<sig type subtypes>` | signal inventory |

Round-trip equality is semantic, not byte-identical XML: IDs, topology, exact
labels, token IDs, status, and extension attributes survive; attribute order and
insignificant whitespace need not.

### Quality and scorer vocabulary

```text
edu_segmentation_precision  edu_segmentation_recall  edu_segmentation_f1
span_precision  span_recall  span_f1
nuclearity_precision  nuclearity_recall  nuclearity_f1
relation_precision  relation_recall  relation_f1
full_precision  full_recall  full_f1
secondary_direction_f1  secondary_relation_f1  secondary_full_f1
signal_detection_f1  signal_type_f1  signal_anchoring_f1
tree_validity_rate  graph_validity_rate  exact_roundtrip_rate
relation_calibration_ece  secondary_calibration_ece
latency_ms  peak_memory_mb  throughput_documents_per_minute
```

Every score binds to corpus release/split digest, input mode, scorer and counting
policy, ontology release, model artifact, device/dtype, timestamp, and code
revision. “Full F1” without those qualifiers is not a reusable fact.

---

## Capability contracts

### Lossless document input

The canonical input is not `Sequence[str]`. Existing `Parser.from_edus(edus)`
reconstructs text by joining EDUs with single spaces, so it cannot preserve
original whitespace or token identity for anchored eRST signals.

```python
@dataclass(frozen=True, slots=True)
class RstDocument:
    document_id: str
    text: str
    tokens: tuple[DocumentToken, ...]
    edus: tuple[Edu, ...] | None
    sentence_boundaries: tuple[TextSpan, ...]
    paragraph_boundaries: tuple[TextSpan, ...]
    source: SourceReference | None
    provenance: ProvenanceRecord
```

Convenience constructors may infer fields but record `InputFidelityEnum`.
Anchored-signal evaluation and lossless RS4 export require original text plus
token and EDU alignment.

Coordinate and indexing conventions:
- Character offsets use standard Python 0-based half-open intervals `[start, end)`.
- Internal token IDs (`DocumentToken.token_id`, `Edu.token_ids`, `DiscourseSignal.token_ids`)
  are 0-based integer tuples. The RS4 serializer/deserializer translates between
  internal 0-based tuples and 1-based RS4 string identifiers at the format boundary.
- Contracts in `isanlp_rst/contracts/` are hand-crafted, slots-enabled Python 3.14
  dataclasses independent of LinkML code-generation artifacts to maintain a
  zero-dependency, deferred-evaluation runtime.

### Typed public results

```python
tree_result = parser.parse_document(document)
graph_result = erst_parser.parse_document(document)
```

Results carry ontology version/digest, model revision/digest/licence, input
fingerprint/fidelity, scheme literals and concepts, per-edge confidence, source
anchors, timings, warnings, failure codes, and derivation provenance.

Keep `Parser.__call__`, `Parser.parse_tree`, and `Parser.from_edus` backward
compatible. Add the typed API alongside them and document lossy calls. Prefer an
`ErstParser` class; do not overload a function object with `parse_erst.from_edus`.

Docling, DocLang, and Markdown entry points project the same contract while
retaining native source references and separate table analyses. They expose an
`output: Literal["rst_tree", "erst_graph"] = "rst_tree"` option and return a typed
format analysis (`DoclingRstAnalysis`, `DocLangRstAnalysis`, `MarkdownRstAnalysis`)
wrapping `RstAnalysis` alongside table analyses and node-to-XPath / node-to-self_ref
mappings, while preserving backward compatibility with existing `DiscourseUnit`
accessors. They never invent format-specific relation names. Before modifying
those routes, obey the hard rule to verify current upstream Docling and DocLang
specifications.

---

## Runtime architecture

```text
Central_Configs immutable ontology release
  ├── LinkML source + governed RST/eRST data
  ├── generated schema/code/linked-data projections
  └── manifest + digest
                  │ pinned by version and digest
                  ▼
RstDocument ──► alignment and validation
                  ├──► primary English RST parser
                  │       ├── segmentation when needed
                  │       └── tree + nuclearity + relation + confidence
                  └──► eRST graph completer
                          ├── secondary-edge candidates
                          ├── direction/relation
                          ├── signal detection/type
                          └── token anchoring
                                  ▼
                  ontology-resolved RstAnalysis
                    ├── typed Python and deterministic JSON
                    ├── RS4 import/export
                    └── format-native projections
```

Default inference remains encoder-scale and local. A heavier/LLM labeler may be
optional, never a core dependency. eRST completion builds on the primary tree;
it does not fork the existing parser architecture.

Production labelers belong in `isanlp_rst/english/`, not `eval/`. New packages
use Mode A and enter the strict Pyright include. Inherited parser-family modules
receive surgical changes only.

---

## Delivery plan

### Phase 0 — Freeze contracts and evidence

- Record current `rstdt`, `gumrrg`, and `unirst` behaviour for raw text and EDUs.
- Hand-prove Standard-Parseval on synthetic trees before published comparisons.
- Pin/digest GUM and extract RS4 relation/signal headers automatically.
- Record corpus/data licences and local-only paths.
- Refresh 2026 quality references and comparison qualifiers.
- Approve the Central extension path and release owner.
- Measure latency, memory, throughput, long documents, and calibration; then set
  budgets from evidence.

### Phase 1 — Release the ontology from Central_Configs

- Add the discourse LinkML module and governed inventories above.
- Reuse Central terminology, relation, provenance, and governance semantics;
  extend rather than duplicate.
- Add mapping assertions, lossiness, aliases, deprecations, and evidence.
- Generate official LinkML projections and run Central's aggregate gates.
- Publish a manifest/digest only after release status is legitimately `released`.
- Register and prove `isanlp_rst` as an offline, digest-pinned consumer.

No downstream code treats proposed keys as canonical before this release exists.

### Phase 2 — Ship the typed tree capability

- Implement lossless documents, typed results/errors, and deterministic JSON.
- Add `Parser.parse_document` while preserving existing APIs.
- Resolve every relation/nuclearity through the pinned ontology.
- Expose and calibrate confidence.
- Implement scorer parity tests and long-document policy with no silent loss.
- Improve structure/nuclearity/relation after baseline error analysis; preserve
  strong spans when a second-pass labeler is sufficient.

### Phase 3 — Ship faithful eRST graph I/O

- Implement separate primary/secondary edge types, stable IDs, and signals with
  discontinuous token IDs.
- Load/dump RS4 against the pinned GUM release and all header labels.
- Convert primary trees without inventing secondary edges/signals.
- Use synthetic redistributable fixtures and licence-safe local corpus tests.
- Wrap a compatible official scorer or independently implement and prove parity.

### Phase 4 — Predict complete eRST graphs

- Implement secondary-edge candidate generation with locality constraints
  (bounded token/EDU distance window, structural tree LCA height constraints,
  and cross-paragraph gating) to prevent $O(N^2)$ candidate explosion on long documents.
- Implement direction/relation classification, signal detection and typing,
  anchoring, graph constraints, and reported repairs.
- Train on the pinned GUM release with manifests.
- Use an oracle ladder to isolate primary-tree, candidate, classification,
  signal, and anchor errors.
- Calibrate secondary/signal confidence and improve the GUM primary-tree floor.

### Phase 5 — Integrate Steve's projects

- Project the contract through Docling, DocLang, and Markdown with native anchors.
- Add batch, cache, preloading, and bounded-resource controls.
- Provide JSON Schema contracts for non-Python consumers.
- Prove representative document → persisted analysis → downstream use flows.
- Every consumer pins the same Central release; none copy label enums.

### Phase 6 — World-class release gate

- Report capability as `implemented`, `verified`, or `released`; existence is not
  verification.
- Publish model cards, manifests, ontology digest, scorers, licences, device,
  dtype, and reproducible commands.
- Run unit, type, lint, serialization, ontology, scorer, model, format-native,
  long-document, and consumer proof gates.
- Publish exact RST-DT/GUM input, corpus, scheme, and scorer conditions.
- Demonstrate local CPU/MPS operation and CUDA where claimed.

---

## Quality evidence and 2026 SOTA targets

These are acceptance evidence, not the platform's purpose.

| Capability | Reference evidence | Release requirement |
|---|---|---|
| RST-DT gold-EDU tree | Maekawa et al. 2024 reports Standard-Parseval Full F1 58.1 | Refresh literature; match scorer/input/split; target verified improvement |
| Raw-text English tree | Current project plus comparable refreshed systems | Report segmentation and S/N/R/Full; never compare mismatched input modes |
| GUM primary tree | Pinned GUM, gold-EDU and raw-text modes | Reproducible baseline and genre/length slices |
| GUM eRST graph | Zeldes et al. 2025 V9 is historical context | Rebuild on pinned current GUM; target secondary/signal improvement |
| Ontology | All live corpus/model labels and RS4 headers | 100% mapped or explicitly unsupported; zero silent fallback |
| RS4 fidelity | Pinned files plus synthetic edge cases | 100% semantic round-trip for supported constructs |
| Confidence | Held-out English calibration | Publish ECE; uncalibrated scores are not called probabilities |
| Project utility | Representative real flows | One end-to-end proof per adopted consumer |

**Verified reference facts (2026-08-16):** Maekawa used gold EDUs and
Standard-Parseval and reported 58.1; NTT code/metrics are evaluation-licensed and
must not be copied. This repo publishes UniRST gold-segmentation 55.46 on
`eng.rst.rstdt`, but no gap is valid before scorer parity. Zeldes defines eRST as
primary tree plus secondary/tree-breaking edges and token-anchored signals; its
GUM V9 numbers are not a current-release target. GUM V12.1.0 was inspected for
this plan, but Phase 0 must pin/digest the actual artifact.

No “SOTA” claim ships without a dated literature refresh, comparable conditions,
reproducible evidence, and named capability scope. Useful capability tiers may
release earlier if status and limits are explicit.

---

## Mandatory conformance tests

### Ontology

- Every RST-DT fine label maps to one coarse-18 concept.
- Every pinned GUM relation and signal header value exists.
- Every model index maps once to a scheme label and valid nuclearity.
- Aliases preserve the original literal; lossy projections declare loss.
- Structural `span` cannot resolve as a semantic prediction.
- Digest mismatch, unmapped value, and invalid combinations fail closed.

### Data and I/O

- Token/EDU offsets reconstruct exact source slices.
- Discontinuous/empty signal anchors survive JSON and RS4 round-trip.
- Secondary edges reject nuclearity; stable IDs retain signal attachment.
- Serialization is deterministic and schema-versioned.
- Existing Parser, dtype-equivalence, and format-native tests do not regress.

### Scoring and models

- Identical synthetic trees score 1.0; hand-counted errors distinguish metrics.
- eRST cases test direction, relation, full, signal detection/type/anchoring.
- Gold-primary and predicted-primary eRST results are never conflated.
- Genre, length, calibration, device, and dtype slices remain in evidence.

---

## Licences and distribution

- Never commit LDC RST-DT. Use local paths and synthetic CI fixtures.
- Never copy NTT's evaluation-licensed parser/metrics into this MIT source.
- Record annotation and underlying-text licences for every GUM artifact. Prefer
  synthetic RS4 CI fixtures unless redistribution is verified.
- Existing weights are CC BY-NC 4.0. Commercial capability needs permissively
  licensed retraining/replacement weights.
- Every model and ontology artifact carries its own provenance and licence; MIT
  source licensing does not override them.

## Risks and controls

| Risk | Control |
|---|---|
| Central 4.0.0 is working, not released | Do not pin it as immutable; complete the approved Central gate first |
| Universal enum erases corpus semantics | Preserve scheme labels and typed, lossy mappings |
| Bare EDU strings destroy anchors | Require text/tokens/spans for lossless mode; mark reconstruction |
| Primary/secondary edges are conflated | Separate types; secondary has direction but no nuclearity |
| Incompatible scorers | Prove semantics; bind every score to full metadata |
| Graph type exists but predicts nothing | Release I/O and prediction as separate levels; score secondary/signals |
| Long documents silently truncate | Declare policy, surface provenance/warnings, test length slices |
| Ontology/runtime drift | Digest pin, generated artifacts, exhaustive mappings, fail closed |

## Non-goals

- Rewriting Central_Configs or duplicating its ontology here.
- Treating benchmark chasing, a paper, or a leaderboard as the product.
- Vendoring licensed corpora, NTT code, or an incompatible scorer.
- Making a huge decoder the default runtime.
- Flattening RST-DT and GUM/eRST into one misleading label list.
- Changing Docling/DocLang contracts without current upstream-spec evidence.
- Claiming multilingual SOTA as part of this English release.

## Intended outcome

Steve's projects have one governed RST vocabulary and one dependable analysis
contract. They can request a tree or complete eRST graph; trace every label to a
canonical concept and every prediction to its model, ontology, and source span;
move between corpus/model encodings without silent semantic loss; and run the
capability locally at practical scale.

That is the product. 2026 SOTA evidence is how the project proves the product is
excellent.

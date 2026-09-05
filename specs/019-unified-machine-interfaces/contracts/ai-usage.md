# Contract: Direct AI Consumption

**Status**: Normative Feature 019 design, not implemented behavior.

## Canonical analysis is the primary AI artifact

Aggregate v2 contains the complete native outcomes plus `reading_guide`.
An AI does not need a separate summary, repository source, schema download or
second model call to understand the record's basic meaning. Native structures
remain native: no common claim graph, quality score or combined verdict.

The guide is explanatory data, not a system prompt. Source text, quotations,
model-produced strings and metadata names remain untrusted content. They confer
no permission to execute tools, follow instructions or fetch referenced URLs.
The contract does not claim it can force every consuming model to obey this
boundary; consumers must keep their own instructions separate from evidence.

## Exact guide shape and ownership

`AnalysisReadingGuide` has:

- `guide_version: SemanticVersion`, initially `1.0.0`.
- `usage_notes: tuple[str,...]`: deterministic contract-authored notes explaining
  analytical status versus truth, untrusted source data, missing assessments and
  the absence of cross-technique consensus.
- `entries: tuple[ReadingGuideEntry,...]`: requested outcomes in order followed
  by retained upstream records in their persisted order, never mixed in counts.

`ReadingGuideEntry` has `scope: requested|retained`, `technique: Technique`,
`record_pointer: str` (RFC 6901 pointer into this aggregate),
`state: result|unavailable|failed`, `descriptor_status:
available|not_applicable|historical_unavailable`, and `descriptor: NativeInterpretationDescriptor
| null`. Non-result entries have null descriptor and point at their exact
outcome/reason with not_applicable status; retained entries are results. For successful requested entries,
the pointer targets the embedded NativeTechniqueResult, not its wrapper.

`NativeInterpretationDescriptor` has `descriptor_version: SemanticVersion`,
`identity: Sha256Identity`, `formalism_id: str`, `native_contract_version: str`,
`provider_contract_version: str`,
`purpose: str`, `input_basis: source_projection|caller_structure`,
`method: model_interpretation|deterministic_computation|mixed`,
`sections: tuple[NativeSectionDescription,...]`, `evidence_rules: tuple[str,...]`,
`validation_scope: tuple[str,...]`, `limitations: tuple[str,...]`, and
`empty_result_meaning: str`. Identity hashes every descriptor field except itself.
Formalism and both versions must equal the native record's declared values.

`NativeSectionDescription` has `pointer: str`, `meaning: str`,
`availability: present|not_recorded`. Pointers are relative to the native record;
present pointers must resolve. They identify meaningful containers, not invented
flattened findings. `meaning` explains the container's roles, directions and
special states. The implementation enumerates exact paths from the actual native
serialization and tests them; there is no wildcard-pointer dialect. Optional
sections not recorded by that native contract are explicitly marked, not filled
with synthetic empty data. No new quote-matching or confidence algorithm runs.

Each provider owns descriptors alongside its native contracts and declares them
for each supported formalism. RST/eRST have separate descriptions under the RST
boundary. Enum inventories, role names and critical questions derive from native
authorities, not a separately curated ontology. Generic Machine assembly binds
the compatible declaration to the actual outcome. The binding may set section
availability by pointer existence only; it cannot reinterpret payload values.
Binding creates a new immutable descriptor with the resolved section availability
and recomputes its identity over those actual fields. It never mutates a provider
declaration or carries a template's digest across changed descriptor fields.
Custom providers must supply their descriptor through the same public declaration
contract. Missing or mismatched descriptors are contract errors, not invented
generic explanations. Historical retained results use a version-matched
descriptor, or historical_unavailable with null descriptor if none exists;
never apply current semantics to an old payload. Descriptor types/imports
themselves load no provider.

## Required native meanings

| Boundary | Reading sections | Required guardrails |
|---|---|---|
| RST/eRST | Graph units, primary/secondary relations, signals, primary decisions, eRST candidates, refinements, validation and anchors | Nuclearity is rhetorical organization, not truth/strength. Preserve raw labels and mapping states; rejected candidates are not edges. Scores retain their kind, range and calibration identity. |
| PDTB | Relations, Arg1/Arg2 spans, relation types/senses and type-specific connective evidence | Declared spans are prepared-source slices; relation/sense choices are interpretations. Inferred connectives are not quotations. NoRel is a successful annotation; NoRel/EntRel/Hypophora legitimately lack senses. |
| SDRT | EDUs/spans, CDU membership, directed relations and structural validation | Labels and CDU organization are interpretations. Right-frontier validation establishes the implemented structural checks, not complete semantic correctness. Labels are not a closed ontology here. |
| Toulmin | Layout components, warrant_origin/evidence, qualified_layout_count and typed source alignments | Grounds are offered evidence, not verified facts. Warrant origin is an explicit model assessment backed by validated passages, not proof of entailment. Backing supports warrant. Qualification means qualifier-or-rebuttal. Legacy v1 lacks origin and retains its old count name. |
| Walton | Scheme/premise roles, conclusion, complete question assessments, validated passages and state counts | A scheme match is not validity. Addressed means taken up, not satisfactorily answered. Current contracts require every assessment; not_assessable is not open. Only legacy v1 can contain default-open omissions, explicitly identified as historical. |
| Dung | Supplied arguments/attacks, grounded/complete/preferred/stable extensions, algorithm/capacity and lineage | Acceptance is relative to this supplied graph, not factual truth. Preferred is a formal semantics name. No stable extensions differs from an empty extension. |
| IBIS | Typed nodes/links, deliberation map, unfilled issues/positions and lineage | Structures are caller supplied; no prose extraction or resolution is implied. No supplied support is not proof no real-world evidence exists. |

Evidence rules distinguish declared spans, literal alignment and interpretation.
Prepared offsets are Unicode character, half-open ranges in the identified
projection, not original-file byte offsets. Original-source anchors retain their
own coordinate type and provenance. All repeated literal matches remain present;
metadata labels are excluded by the provider's evidence-field policy. An eligible
literal occurrence never proves source assertion or upgrades warrant origin.

Absence is not zero confidence, false, abstention or negative evidence. Empty
finding lists mean no findings returned, not proof no arguments exist. Preserve
explicit native `empty_primary_discourse`, calibration/mapping/component states
and failures. Do not manufacture a universal assessment taxonomy. The corrections
in [native-integrity.md](native-integrity.md) happen in providers before output;
guides explain corrected native records. Historical guides identify old missing
assessments without inventing them. Presentation never rewrites a saved payload.

## Explicit whole-technique view

`select_analysis(analysis, techniques=...)` returns `rdam.analysis_view` v1.
`ViewRequest` is a closed record with contract/version, `analysis: AggregateAnalysis`
(v2 only) and `techniques: nonempty unique tuple[Technique,...]`.
Unknown, duplicate or unrequested boundaries fail; selection order follows the
original request, regardless of selector order. Failed/unavailable selections
remain failed/unavailable, never filtered out automatically.

`AnalysisView` fields are:

| Field | Type / rule |
|---|---|
| contract / contract_version | Literals `rdam.analysis_view` / `1.0.0` |
| analysis_identity | Original aggregate semantic digest |
| source | Unchanged SourceIdentity |
| requested_techniques | Full original ordered requested tuple |
| selected_techniques | Selected boundaries in original order |
| analysis_status | Original aggregate status; never recomputed for a subset |
| outcomes | Whole selected v2 outcomes, unchanged |
| excluded_outcomes | Ordered `{technique, state, original_pointer}` for every excluded outcome |
| upstream_results / lineage / configurations / preparation | Full unchanged original context; no evidence pruning |
| reading_guide | Guide for selected outcomes plus all retained results; pointers rebound into this view |
| omitted_content | Literal `unselected_outcomes_only`; no native field/item truncation |
| semantic_digest | Same semantic projection as aggregate v2, using native semantic identities rather than execution-sensitive native bytes |

Excluded pointers target the original aggregate identified by analysis_identity,
not the view. Selected guide pointers target this view. The original full record
must be kept by the consumer; identity is not a URL, server storage handle or
promise of automatic retrieval. The server keeps no result store.

For digest calculation only, replace selected success records and retained native
records with their version-correct native semantic identities; retain failure,
scope, configuration, preparation, guide and exclusion data. Full serialization
still preserves every native field and its artifact digest. This is the same
semantic-versus-artifact distinction as the aggregate, not permission to delete
execution fields from the delivered record.

Selecting all boundaries yields an explicitly typed view with no exclusions, not
a new analysis. Selection may reduce output but retains all shared preparation
context; no bound on token count or claim of fitting an arbitrary model window is
made. Users may choose fewer analysis techniques upstream. Pagination, automatic
ranking, token-budget packing and per-item filtering are not silently introduced.

Python, CLI `rdam view`, and HTTP `POST /v1/view` invoke this one pure operation.
The full aggregate is still the default output of every analysis interface.

## Acceptance

- All present pointers resolve; unavailable/failed/retained scopes are explicit.
- Same aggregate and equivalent selection produce identical canonical view bytes.
- Selected native bytes, candidate decisions, scores and alignments are identical
  to the originals; every excluded outcome is named exactly once.
- Original status cannot change because a failed outcome was excluded.
- Every guardrail in the native-meanings table has an adversarial fixture.
- Model constructions, source acquisition, network calls and inference counts
  remain zero for saved-record viewing and summarization.

These checks establish preservation and interpretation-contract behavior, not
native analytical correctness. The separate
[analytical-quality.md](analytical-quality.md) checks use focused real-model
cases and cold critique for findings, source support and assessment states.
No confidence or quality score is invented for the guide.

# Contract: Native Analysis Integrity Corrections

**Status**: Required implementation scope, authorized on 2026-09-04.

This contract supersedes the earlier blanket proposal to leave all native schemas
unchanged. Preserve native framework distinctions and trained inference maths;
correct the assessment and evidence representations at their producing boundary.
A warning in a reading guide is not an implementation of these fixes.

Integrity is necessary but not sufficient. Semantic support, finding coverage,
state accuracy and justified abstention must also meet
[analytical-quality.md](analytical-quality.md). Exact source coordinates cannot
prove that a passage supports the interpretation; a complete assessment list
cannot prove that its states or the detected argument are correct.

## Evidence baseline

The diagnostic executed against the existing code produced:

```text
Walton reported assessments: 0
Walton derived open questions: 2
Toulmin explicitness field: False
Alignment candidates for a status label: (('/status', 'open'),)
```

The main agent read `rdam/walton/schemes.py`, `rdam/toulmin/argument.py` and
`rdam/ingest/alignment.py` in full. These observations establish the current
contract gaps, not failure rates across a corpus. Regression tests must exercise
the real validators/providers, not replace them with internal mocks.

## NI-01 — Complete Walton assessments

Each scheme instance must supply exactly the indices `0..N-1`, each once, where
N derives from its existing `SCHEMES` entry. Reject missing, duplicate, unknown,
negative and non-integer indices. Persist questions in catalogue order. An empty
instance list remains valid; an instance with an empty assessment list does not.

Current `addressed` and `open` states remain. Add `not_assessable` with a required
`reason: insufficient_context|ambiguous_source`. No automatic substitution of
this state for missing model output. Use the provider's existing bounded output
retry path for invalid proposals; exhaustion produces a typed provider failure.

- `addressed`: require a nonempty explanatory note plus at least one validated
  SourceEvidenceSpan. The note is model interpretation; the quoted passage is
  source evidence. A nonempty note alone is insufficient.
- `open`: explicitly assessed as not addressed in the analysed projection;
  evidence and note are empty and reason is null. It does not mean refuted,
  false or a fallacy. The result identifies the analysed scope, not all possible
  external evidence.
- `not_assessable`: require its reason; optional validated spans may identify the
  ambiguous passage. It is neither addressed nor open. Note is optional and is
  never represented as a source quotation without span validation.

New question fields: existing `index`, `status`, `note`, plus
`evidence: tuple[SourceEvidenceSpan,...] = ()` and nullable `reason` above.
After complete coverage validates, `open_questions` derives exclusively from
explicit open assessments. Per instance emit `question_count`, `addressed_count`,
`open_question_count`, `not_assessable_count`; the three state counts sum to the
question count. Aggregate totals use the same derivation. Keep `scheme_set` and
its identity unchanged because this work does not change the scheme catalogue.

## NI-02 — Toulmin warrant origin and honest count names

Retain the six-element layout and existing warrant non-restatement checks. Add
required `warrant_origin: explicit|reconstructed|undetermined`,
`warrant_evidence: tuple[SourceEvidenceSpan,...]`, and nullable
`warrant_origin_reason: insufficient_context|ambiguous_source`.

- `explicit`: at least one validated passage must contain the stated licence;
  a model may paraphrase that passage in the warrant field. Origin remains a
  model assessment, not deterministic proof of semantic equivalence.
- `reconstructed`: a model-proposed licence connecting the offered grounds and
  claim. At least one validated supporting passage is required, but never turns the proposed
  licence into a quotation just because the same words occur elsewhere.
- `undetermined`: reason required; any supplied spans still validate. Do not
  force a confident origin classification to satisfy the schema.

For explicit/reconstructed, reason is null. An absent origin is invalid new
output, not a default. Missing evidence on explicit origin, fabricated quotes,
wrong offsets or evidence from another projection fail source validation.
Grounds remain evidence offered by the arguer, not independently verified facts.

Rename new payload `fully_qualified_count` to `qualified_layout_count`, retaining
the actual rule `qualifier is present OR rebuttals are nonempty`. No duplicate
compatibility field. Keep existing `is_qualified` and `elements_present` meanings;
historical v1 retains its old field name without claiming every optional element.

## NI-03 — Typed, provider-selected source alignment

Add immutable strict `SourceEvidenceSpan = {start: int >= 0, end: int > start,
text: nonempty str}`. These are Unicode character, half-open offsets into the
exact analysed text. Shared validation checks `text == analysed_text[start:end]`.
The same validation works for direct ProviderRequest text without a projection;
original-file anchors are additional evidence only when a projection exists.

Replace arbitrary recursive string walking with provider-owned field selection.
A provider selects exact payload JSON pointers and the relationship it asserts.
The shared aligner only validates/materializes those selections against the
prepared document. Unknown pointers, non-string field targets, out-of-bounds
ranges and incompatible field roles fail; do not repair offsets or pick a match.

`ResultSourceAlignment` v2 retains `payload_path`, `prepared_range`,
`contributing_item_ids`, `source_anchors`, and adds:

- `relationship: exact_quote|supporting_passage|literal_occurrence`.
- `projection_identity: Sha256Identity` of the actual provider projection.
- `quote: str`, copied from and checked against that projection's exact slice.

`exact_quote` requires the selected source-bearing payload string to equal the
quote. `supporting_passage` attaches a provider-declared passage to an
interpretation; it verifies the passage, not entailment. `literal_occurrence`
records a text match only and makes no supporting-evidence claim. All repeated
eligible matches are retained with their distinct ranges; no first-match guess.
Source anchors/contributors derive from the intersecting projection segments and
are checked, never supplied by a model as trusted filesystem coordinates.

Provider policy:

- PDTB: declared argument/explicit-connective/alternative-lexicalization spans;
  never inferred connectives, sense labels, ids or relation-type metadata.
- SDRT: declared EDU spans; never relation labels, ids or structural-class names.
- Toulmin: validated warrant/support passages and explicitly identified textual
  layout fields; automatic string matches are at most literal_occurrence.
- Walton: validated question evidence and explicitly identified premise/conclusion
  text; never scheme names, status labels or catalogue question wording.
- RST/eRST: retain existing native anchors, decisions and scores; any new outer
  alignment must follow the same rules, without changing predictor maths.
- Dung/IBIS: do not invent document evidence for caller-owned formal structures.
  Preserve their source identity and declared lineage.

No transport performs this field selection. Old `_strings`-style walking is
removed from the production evidence path, not retained behind a compatibility
mode. Direct-provider output with no projection can retain validated native spans
but cannot claim original-file alignments it cannot establish.

## NI-04 — Version, persistence, caches and historical truth

- Write `rdam.native_result` **2.0.0** for current providers, with the typed
  alignment contract. Keep an explicit v1 reader/model and its digest algorithm.
- Write Toulmin and Walton provider payload contracts **2.0.0**. Version their
  extraction/assessment algorithm identities and instruction identities with
  these changed requirements. Do not change the Walton catalogue identity.
- PDTB/SDRT provider contracts also advance to **2.0.0** for their changed emitted
  evidence semantics; their native relation/graph payload shapes stay unchanged.
  RST/Dung/IBIS provider payload versions remain unchanged where their payload
  semantics are unchanged, even though their envelope writes v2.
- Registry dispatch uses both outer and provider contract versions. Generated
  schemas include current provider payloads and explicitly named historical
  schemas; no shared constant bumps unrelated ingest formats.
- Old native cache records cannot satisfy current v2 provider execution. Cache
  keys bind envelope/provider/instruction/evidence-policy versions. A stale entry
  is a miss, not silently upgraded data. Do not delete unrelated cache entries.
- Effective provider configuration additionally binds the extraction-schema and
  evidence-selection-policy identities. Keep instruction hashes as hashes of
  actual instruction text; do not pretend they also cover independently changing
  schema descriptions. Cache validation requires these resolved identities.
- Aggregate v2 may retain historical upstream results exactly as supplied. It
  must label their historical interpretation limits; retained success still does
  not count as a newly requested success. Unsupported historical descriptors are
  explicitly unavailable rather than guessed from the current provider.
- No migration fills old missing questions, origin fields or evidence roles.
  Re-analysis under the new contract is a new result with a new identity.

Native payload validation remains provider-owned. A successful v2 provider result
must validate against its declared payload version before aggregation; a valid
outer JSON digest alone does not certify the inner analytical schema. Stored
reading may validate structure/identity without re-acquiring the source; only
source material already persisted in the record can support renewed span checks.

## Required regression cases

| Case | Expected result |
|---|---|
| Walton zero/partial/duplicate/out-of-range assessments | Rejected proposal; never fabricated open questions |
| Walton complete mixed addressed/open/not_assessable | All indices retained; counts reconcile exactly |
| Walton addressed note without valid quoted span | Rejected proposal |
| Toulmin explicit warrant with correct supporting passage | Origin retained as model assessment; exact source passage retained |
| Toulmin explicit origin without evidence or with wrong offsets | Rejected proposal |
| Reconstructed/undetermined warrant | Distinct truthful state; required reason enforced only for undetermined |
| Qualifier present but no backing/rebuttal | qualified_layout_count increments; no claim all optional elements exist |
| Source contains metadata words open/Implicit/Contrast | No metadata-label evidence alignment |
| Proposed warrant happens to match another passage | A literal occurrence never upgrades origin or establishes support |
| Repeated eligible quote | All valid matches retained, or exact declared offset preserved; no arbitrary choice |
| Wrong projection identity, Unicode offsets or forged anchors | Rejected alignment; no repaired coordinates |
| Old v1 Walton/Toulmin/native cache fixture | Historical read preserves bytes/identities; new execution cannot reuse it |
| Direct ProviderRequest without projection | Native text-span validation works; no fabricated source anchors |

External-model fixture tests prove validator/protocol behavior, not live model
quality. Separately run model-backed source-grounding cases and report their
actual results. A skipped model case is unverified, not a passed integrity gate.
Use the focused semantic cases and cold critique in
[analytical-quality.md](analytical-quality.md), not just model JSON validation.
Fix substantiated defects and rerun the affected tests.

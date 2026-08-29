# Contract: Production Python API 5.0.0

**Public import root**: `isanlp_rst.ingest`  
**Serialized contract**: `isanlp_rst.production` 2.0.0  
**Status**: Phase 1 design contract

## Boundary

`isanlp_rst.ingest` is the only supported production import root for source
preparation and analysis. Format adapters remain internal. This contract adds
no consumer-specific state and does not restore `parse_markdown`,
`parse_docling`, `parse_doclang`, or their former result envelopes.

The package-level `isanlp_rst.Parser` remains the supported parser facade. Its
production identity and capacity values are exposed through typed contracts
re-exported from `isanlp_rst.ingest` where lifecycle callers need them.

`Parser.analyse_document()` is the canonical parser operation for callers that
already have an `RstDocument`. `Parser.parse_document()` may remain as a
documented graph-only convenience projection, but production ingest must not
use that projection as its evidence authority.

## Required public operations

The signatures below are normative design targets. Exact annotations and
defaults must reconcile with the machine-readable public-surface inventory.

```python
class SourceArtifact:
    @classmethod
    def from_path(
        cls,
        path: Path,
        *,
        source_form: SourceForm | None = None,
        original_source: str | None = None,
        conversion_provenance: Sequence[ConversionActivity] = (),
    ) -> SourceArtifact: ...


class Parser:
    def analyse_document(
        self,
        document: RstDocument,
        *,
        analysis_policy: AnalysisPolicy | None = None,
    ) -> ParserAnalysisResult: ...

    def parse_document(
        self,
        document: RstDocument,
        output: OutputFormalism = OutputFormalism.RST_TREE,
    ) -> RstAnalysis: ...


def describe_capabilities(
    parser: AnalysisParser | None = None,
) -> ProductionCapabilities: ...


def serialize_contract(
    value: PublicProductionContract | ProductionFailure,
    *,
    diagnostic_policy: DiagnosticPolicy | None = None,
) -> bytes: ...


def load_contract(data: bytes | str) -> PublicProductionContract: ...


class ProductionIngestor:
    def __init__(
        self,
        *,
        parser: AnalysisParser | None = None,
    ) -> None: ...

    def capabilities(self) -> ProductionCapabilities: ...

    def prepare(
        self,
        source: SourceArtifact,
        *,
        policy: PreparationPolicy | None = None,
        planning_policy: PlanningPolicy | None = None,
        parser_capacity: ParserCapacity | None = None,
    ) -> PreparationOutcome: ...

    def analyse(
        self,
        source: SourceArtifact,
        *,
        policy: PreparationPolicy | None = None,
        planning_policy: PlanningPolicy | None = None,
        analysis_policy: AnalysisPolicy | None = None,
        cache_directory: Path | None = None,
        diagnostic_policy: DiagnosticPolicy | None = None,
    ) -> ProductionAnalysisOutcome: ...
```

The constructor arguments are keyword-only. A supplied parser provides its
capacity to preparation automatically during `analyse()`. A caller may supply
capacity explicitly to `prepare()` without loading a model. A `None` policy
selects the documented production default, and the resolved complete policy is
always returned in the outcome rather than remaining implicit.

The resolved `AnalysisPolicy` uses `output_formalism=rst_tree`,
`evidence_detail=decision_complete`, and `lossy_input=forbid` by default. It is
embedded in the result. Selecting `erst_graph` requests secondary-edge
completion; selecting `normalized_distributions` requests only distributions
the configured provider genuinely computes.

`ParserAnalysisResult` is the self-contained provider result for parser-only
use: exact analysed substrate, validated graph, decision evidence, refinements,
composite and loaded-component identities, optional recombination receipt,
validation receipt, execution evidence, and semantic identity. It deliberately
does not contain source-ingest inventory or preparation evidence.

## Return and raise contract

### `prepare()`

Returns `PreparationOutcome` when acquisition, inventory, preparation,
validation, and optional planning complete. This is the explicit
intentional-non-analysis lifecycle operation. An empty or retained-only source
still returns a successful preparation outcome with exact empty-primary
evidence.

Raises `ProductionIngestError` carrying a typed `ProductionFailure` when any
required stage fails. It never returns a partial tuple or bare prepared
document.

### `analyse()`

Returns exactly one of:

- `AnalysedOutcome`, with status `analysed` and a fully validated RST/eRST
  analysis; or
- `EmptyPrimaryAnalysisOutcome`, with status
  `empty_primary_discourse` and no fabricated analysis.

Raises `ProductionIngestError` for provider unavailability or failed
processing. No configured parser is provider unavailability, not intentional
non-analysis. An invalid parser graph, incomplete anchors, partial unit set, or
identity contradiction fails before return and before cache storage.

### Failure exception

```python
class ProductionIngestError(Exception):
    failure: ProductionFailure
```

`failure` is immutable and contains the complete typed evidence available in
the current process. `str(error)` and `repr(error)` are safe for normal logs.
The original runtime cause is linked with Python exception chaining but is not
automatically serialized. Default failure serialization produces a separate
typed safe projection so nested completed preparation evidence cannot leak raw
private content.

## Supported top-level records

| Kind | Python type | Produced by |
|---|---|---|
| `preparation_outcome` | `PreparationOutcome` | `prepare()` |
| `parser_analysis_result` | `ParserAnalysisResult` | `Parser.analyse_document()` |
| `analysed_outcome` | `AnalysedOutcome` | `analyse()` |
| `empty_primary_analysis_outcome` | `EmptyPrimaryAnalysisOutcome` | `analyse()` |
| `capabilities` | `ProductionCapabilities` | capability discovery |
| safe stage-specific failure kinds | `SafeProductionFailureRecord` variants | default serialization of `ProductionIngestError.failure` |

`PublicProductionContract` is the discriminated union of all persisted
top-level records accepted by `load_contract()`. `serialize_contract()` also
accepts an in-memory `ProductionFailure` and produces its safe persisted
projection by default.

## Success-state semantics

| Lifecycle choice or condition | Public representation | Analysis status |
|---|---|---|
| Caller asks only for preparation | `PreparationOutcome` | Not applicable; intentional non-analysis is explicit from operation and kind |
| Analysis requested and primary discourse exists | `AnalysedOutcome` | `analysed` |
| Analysis requested and primary discourse is empty | `EmptyPrimaryAnalysisOutcome` | `empty_primary_discourse` |
| Analysis requested but parser/extra/release unavailable | typed failure | Not a success status |
| Analysis processing fails | typed failure | Not a success status |

This table is the exhaustive public state algebra. Tests must produce every row.

## Complete preparation contract

`PreparationOutcome` must expose, as typed values:

- safe source summary and source-contract identity;
- complete selected preparation and planning policies;
- every valid inventoried item and its accessible typed representation;
- exactly one final disposition per item;
- duplicate and structural relationships;
- every applied transformation and its inputs/outputs;
- complete prepared primary discourse and source mapping;
- structural boundaries;
- exact inventory, primary, retained, mapping, and anchor coverage;
- stable warnings;
- explicit analysis plan state and complete units when capacity was supplied;
- semantic identity and execution evidence.

An identifier or digest is not a substitute for any decision input or evidence
value in this list.

## Complete analysis contract

Every analysis success variant embeds the complete `PreparationOutcome` and
adds:

- exclusive analysis status;
- complete resolved `AnalysisRequest` and `AnalysisPolicy`;
- exact `AnalysedDocument` tokens, EDUs, sentence/paragraph boundaries,
  mappings, anchors, and fidelity records actually supplied to inference;
- full composite analysis identity and parser capacity;
- validated `RstAnalysis` nodes, primary edges, and secondary edges where
  present;
- decision-complete primary inference evidence;
- eRST candidate, signal, score, calibration, decision, and decoder evidence
  when requested;
- complete both-endpoint analysis and supporting-signal anchors;
- marker before/after refinement records;
- deterministic recombination receipt for multi-unit analysis;
- typed check-by-check validation receipt;
- semantic request and result identities;
- execution receipt and cache provenance.

The empty-primary variant must not contain a dummy root, empty edge graph
presented as analysis, or fabricated anchors.

## Capability contract

Capability discovery must report all source forms, including unavailable ones.
For each source form it gives availability, required extra, and missing
distribution names. It also reports:

- installed package version;
- write and readable contract versions;
- lifecycle operations and top-level record kinds;
- persistence and canonicalization guarantees;
- parser capacity if declaratively available;
- model identity state: `immutable_release`, `mutable_instance`,
  `unidentified`, or `not_configured`;
- supported output formalisms and evidence-detail policies per configured
  backend;
- whether exact analysed-substrate, decision-complete primary evidence, marker
  refinement, eRST evidence, recombination receipt, and validation receipt are
  available;
- durable semantic-cache eligibility and stable reason.

Discovery must not import format adapters, instantiate a parser, resolve or
download model bytes, inspect the offline workbench, analyse a source, or access
a network.

## Parser protocol contract

`AnalysisParser` is a supported runtime-checkable protocol re-exported from
`isanlp_rst.ingest`. It requires:

```python
class AnalysisParser(Protocol):
    @property
    def analysis_capacity(self) -> ParserCapacity: ...

    @property
    def model_release_identity(self) -> ModelReleaseIdentity | None: ...

    def analyse_document(
        self,
        document: RstDocument,
        *,
        analysis_policy: AnalysisPolicy | None = None,
    ) -> ParserAnalysisResult: ...
```

This strengthens the current parser facade without inventing a downstream
adapter method. Production ingest receives the provider-owned rich result,
adds source preparation and source-level anchors, and performs any required
subdivision through the same typed path. A missing `model_release_identity`
means the parser is mutable or unidentified and therefore ineligible for
durable semantic caching. Parser output never becomes a public success value
before provider validation.

The protocol's semantic return includes the final `RstAnalysis` and the exact
analysed substrate and decision evidence defined in
[analysis-evidence.md](./analysis-evidence.md). A backend that cannot supply
required decision-complete evidence is reported unavailable for this production
contract; the service does not fabricate it from the final tree. Any claimed
immutable identity must match the exact loaded component receipts.

## Optional dependency behaviour

The base wheel must import and describe capabilities with no Docling, DocLang,
or Markdown format distribution installed. Corresponding source forms remain
visible with `available=false` and `install_extra="formats"`.

Attempting to prepare an unavailable form raises a typed provider-unavailable
failure naming only the missing distribution and supported extra. Raw
`ModuleNotFoundError` must not cross the public boundary.

## Installed command projections

The `isanlp-rst` console script is a supported installed projection of this
contract. Its structured-file inputs construct `SourceArtifact` values and use
`ProductionIngestor`; its parser-only path uses `ParserAnalysisResult`. One
request performs inference at most once.

`--format json` writes `serialize_contract()` bytes for the canonical result.
Tree, statistics, and RS3 formats are explicitly documented presentation views
derived from that same result and do not claim to preserve the complete
contract. The CLI does not define a separate schema version.

If `isanlp-rst serve` remains supported, its loopback endpoint accepts a typed
request and returns the same canonical success or safe failure record as the
Python API. Health/capability output is derived from
`describe_capabilities()`. It does not return count-only analysis as a complete
result or serialize arbitrary exception text.

## Validation contract

Before success, the provider validates:

1. source and contract identities;
2. inventory uniqueness, relationships, dispositions, and complete coverage;
3. transformations, prepared mappings, structural boundaries, and plan units;
4. parser/model identity and cache eligibility;
5. primary RST connectedness, acyclicity, root count, nuclearity and relation
   invariants;
6. eRST secondary-edge DAG constraints;
7. anchor completeness, bounds, uniqueness, and source reconstruction;
8. multi-unit completeness and deterministic recombination;
9. semantic request, result, and stored cache identity agreement.
10. output formalism, analysed-substrate fidelity, and evidence-detail policy
    agreement;
11. primary decision-to-node/edge completeness and refinement before/after
    provenance;
12. eRST candidate/signal/score/decoder links and non-orphaned signals;
13. both-endpoint relation/secondary-edge anchors;
14. recombination local-to-global completeness and validation-receipt
    consistency;
15. declared relation scheme, confidence kind, calibration, and ontology
    mapping provenance.
16. canonical parser-result completeness and equivalence of any graph-only
    convenience projection;
17. exact equality between reported immutable component identities and the
    tokenizer/configuration/weight/calibration/inventory/rules/ontology bytes
    loaded by the runtime;
18. absence of fabricated decisions for unanalysed content and absence of
    archived or unexecutable families from active capabilities.

Validation failure returns no success value. Cache persistence is invoked only
after the complete outcome passes all checks.

## Failure-stage contract

Stable failed stages are:

`acquisition`, `classification`, `preparation`, `planning`, `inference`,
`validation`, `assembly`, `persistence`, and `cache_retrieval`.

Every failure contains:

- stage-specific literal kind;
- stable category and code;
- retryability classification;
- safe message and typed allowlisted diagnostic context;
- sanitized causal chain;
- the strongest completed-evidence variant permitted by the failed stage.

Completed evidence must precede the failed stage. Inference-completed evidence
may report safe unit completion and output digests but must not present invalid
output as a validated analysis. A persistence failure may carry the fully
assembled outcome because assembly completed.

## Privacy contract

Default exception rendering and serialization exclude:

- raw submitted or prepared text;
- prompts or document fragments;
- arbitrary cause strings and exception representations;
- traceback frames and locals;
- environment variables;
- local private paths.

An explicit `DiagnosticPolicy` may permit additional in-memory diagnostics and
a distinct full diagnostic failure record. Default serialization replaces
private representation values inside completed evidence with typed redactions
that retain content kind, length, digest, anchors, structure, relationships,
and disposition. Full diagnostic serialization requires an explicit
`include_private_content` policy and uses a separately discriminated record so
it cannot be mistaken for the safe default. Persisted schemas remain closed;
diagnostic opt-in cannot turn arbitrary private values into contract fields.

## Removed and internal surfaces

The following remain unsupported public imports:

- format-specific parse functions and result envelopes;
- internal `prepare_source()` tuples;
- format adapter classes;
- unvalidated parser-output structures;
- cache implementation classes unless separately classified in the public
  inventory;
- research, training, evaluation, and promotion modules.

Negative-import conformance tests protect this boundary.

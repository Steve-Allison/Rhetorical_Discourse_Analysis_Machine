# Quickstart: Production Contract 5.0.0

**Status**: Phase 1 executable design; commands and imports become valid after
Feature 004 implementation and release promotion.

This quickstart is both the intended consumer workflow and a clean-install
acceptance script. It uses only supported installed exports.

## 1. Verify the tracked release

From the repository promotion commit:

```bash
shasum -a 256 -c dist/5.0.0/release-receipt.sha256
pixi run -e offline validate-production-artifacts
```

The validator must report:

- package version: `5.0.0`;
- write contract: `isanlp_rst.production` `2.0.0`;
- wheel and sdist digests: matched;
- source revision and tree: identified and clean;
- required verification checks: present and passed.

## 2. Install the exact wheel

Create a genuine isolated Python 3.14 environment and install the promoted
wheel. Do not rebuild the sdist.

```bash
python3.14 -m venv /tmp/isanlp-rst-5-core
/tmp/isanlp-rst-5-core/bin/python -m pip install \
  dist/5.0.0/isanlp_rst-5.0.0-py3-none-any.whl
/tmp/isanlp-rst-5-core/bin/python -m pip check
```

The repository's automated clean-install task must use a fresh temporary
directory rather than this illustrative fixed path.

## 3. Discover capability without a model

```python
from isanlp_rst.ingest import describe_capabilities

capabilities = describe_capabilities()

assert capabilities.semantic.package_version == "5.0.0"
assert capabilities.contract_version == "2.0.0"
assert capabilities.semantic.model_identity_state == "not_configured"
assert capabilities.semantic.semantic_cache_eligible is False

for source_form in capabilities.semantic.source_forms:
    print(
        source_form.source_form,
        source_form.available,
        source_form.install_extra,
        source_form.missing_distributions,
    )
```

This call must not load a parser, import optional adapters, resolve model
weights, access a network, or inspect the offline workbench.

## 4. Prepare and inspect complete evidence

```python
from pathlib import Path

from isanlp_rst.ingest import ProductionIngestor, SourceArtifact

source = SourceArtifact.from_path(
    Path("example.md"),
    original_source="urn:example:markdown",
)
ingestor = ProductionIngestor()
prepared = ingestor.prepare(source)

print(prepared.semantic.source_summary.byte_digest)
print(prepared.semantic.source_contract)
print(prepared.semantic.preparation_policy)
print(prepared.semantic.analysis_plan.status)

for item in prepared.semantic.inventory:
    print(
        item.item_id,
        item.classification,
        item.representation.kind,
        item.disposition.decision,
        item.disposition.reason,
    )

assert all(item.disposition is not None for item in prepared.semantic.inventory)
assert prepared.semantic.inventory_coverage.covered_units == (
    prepared.semantic.inventory_coverage.total_units
)
```

`prepare()` is the explicit intentional-non-analysis path. It returns retained
content as accessible typed values, not merely identifiers or digests.

If Markdown support is unavailable in the core environment, this call raises a
typed provider-unavailable error that names `isanlp_rst[formats]`; raw
`ModuleNotFoundError` does not cross the boundary.

## 5. Plan without loading a model

When a consumer knows the parser capacity declaratively, preparation can expose
the complete deterministic analysis plan without running inference:

```python
from isanlp_rst.ingest import ParserCapacity

capacity = ParserCapacity(
    capacity_kind="segments",
    maximum=384,
    estimator="prepared_segments",
    estimator_version="1.0.0",
)
planned = ingestor.prepare(source, parser_capacity=capacity)

assert planned.semantic.analysis_plan.status in {"single_unit", "subdivided"}
for unit in planned.semantic.analysis_plan.units:
    print(unit.unit_id, unit.segment_range, unit.boundary_reason)
```

## 6. Analyse with an immutable model release

```python
from isanlp_rst import Parser
from isanlp_rst.ingest import (
    AnalysisPolicy,
    EvidenceDetailPolicy,
    OutputFormalism,
    ProductionIngestor,
)

parser = Parser.from_model_release(
    Path("/models/isanlp_rst"),
    "modernbert-v5",
    family="modernbert",
)
ingestor = ProductionIngestor(parser=parser)
analysis_policy = AnalysisPolicy(
    output_formalism=OutputFormalism.RST_TREE,
    evidence_detail=EvidenceDetailPolicy.DECISION_COMPLETE,
)
result = ingestor.analyse(source, analysis_policy=analysis_policy)

print(result.status)
print(result.semantic.analysis_request.analysis_policy)
print(result.semantic.composite_analysis_identity.primary_parser.state)
print(result.semantic.preparation.semantic.source_contract)
print(result.semantic.semantic_request_identity)
print(result.semantic_digest)

if result.status == "analysed":
    analysed_document = result.semantic.analysed_document
    print(len(analysed_document.tokens), len(analysed_document.edus))
    print(len(result.semantic.analysis.nodes))
    print(len(result.semantic.analysis.primary_edges))
    print(len(result.semantic.analysis.secondary_edges))
    print(len(result.semantic.primary_inference.structure_decisions))
    print(result.semantic.validation_receipt.overall_disposition)
    assert result.semantic.analysis_anchors
    assert result.semantic.validation_receipt.overall_disposition == "passed"
else:
    assert result.status == "empty_primary_discourse"
```

For an already-constructed `RstDocument`, use the canonical parser result
directly rather than production ingest:

```python
from isanlp_rst import RstDocument

document = RstDocument.from_text("A claim. Because evidence supports it.")
parser_result = parser.analyse_document(
    document,
    analysis_policy=analysis_policy,
)

assert parser_result.analysis.document_id == document.document_id
assert parser_result.analysed_document.edus
assert parser_result.validation_receipt.overall_disposition == "passed"
assert parser_result.composite_analysis_identity.primary_parser.state == (
    "immutable_release"
)
assert parser_result.loaded_component_receipts
```

`parse_document()` is the supported graph-only convenience projection.
`ProductionIngestor.analyse()` consumes and embeds `ParserAnalysisResult`; it
does not reconstruct discarded evidence from that projection.

The result embeds the complete preparation outcome. A consumer does not rerun
preparation, import an adapter, or reconstruct a source contract or model
identity.

The default is decision-complete evidence. To request provider-computed
normalized split, relation, nuclearity, or segmentation distributions, select
`EvidenceDetailPolicy.NORMALIZED_DISTRIBUTIONS`. That choice is semantic and
therefore changes request/cache identity whenever the returned evidence differs.

For `OutputFormalism.ERST_GRAPH`, inspect accepted secondary-edge evidence
without reconstructing decoder state:

```python
erst_result = ingestor.analyse(
    source,
    analysis_policy=AnalysisPolicy(
        output_formalism=OutputFormalism.ERST_GRAPH,
        evidence_detail=EvidenceDetailPolicy.DECISION_COMPLETE,
    ),
)

for decision in erst_result.semantic.erst_completion.candidate_decisions:
    if decision.decision == "accepted":
        print(
            decision.source_node_id,
            decision.target_node_id,
            decision.supporting_signal_ids,
            decision.edge_probability,
            decision.relation_probability,
            decision.joint_selection_score,
        )

print(erst_result.semantic.erst_completion.decode_receipt)
```

Every relation declares its scheme, confidence kind, calibration state, and
ontology-mapping provenance. Every marker refinement preserves the before and
after decision. Subdivided results additionally expose a complete compact
`recombination_receipt`.

## 7. Persist and reload canonically

```python
from isanlp_rst.ingest import load_contract, serialize_contract

encoded = serialize_contract(result)
reloaded = load_contract(encoded)

assert serialize_contract(reloaded) == encoded
assert reloaded.semantic_digest == result.semantic_digest
```

The bytes are RFC 8785 canonical JSON. Pretty JSON and Pydantic's ordinary JSON
rendering are not cache or digest authorities.

## 8. Handle typed completed-stage failure

```python
from isanlp_rst.ingest import ProductionIngestError, serialize_contract

try:
    ingestor.analyse(source)
except ProductionIngestError as error:
    failure = error.failure
    print(failure.semantic.failed_stage)
    print(failure.semantic.category)
    print(failure.semantic.retryability)
    print(failure.semantic.completed_evidence.kind)

    safe_bytes = serialize_contract(failure)
    # The conformance fixture contains this exact private marker.
    assert "PRIVATE_CONFORMANCE_MARKER" not in safe_bytes.decode("utf-8")
```

If preparation completed and inference failed, completed evidence contains the
full in-memory `PreparationOutcome` and no claimed analysis. Default
serialization emits the separately typed safe projection with private content
redacted. If acquisition failed, no later-stage evidence is representable.

## 9. Verify a consumer uses only the public contract

A representative adapter conformance fixture must import exclusively from:

```python
from isanlp_rst import Parser
from isanlp_rst.ingest import (
    ProductionIngestError,
    ProductionIngestor,
    AnalysisPolicy,
    EvidenceDetailPolicy,
    OutputFormalism,
    SourceArtifact,
    describe_capabilities,
    load_contract,
    serialize_contract,
)
```

The fixture fails if it imports `isanlp_rst.ingest._*`, format adapters,
`prepare_source`, cache internals, research modules, or unexported contract
modules. It must answer the following solely from one outcome or completed-stage
failure:

- what source was received;
- what was inventoried and retained;
- what was transformed, analysed, excluded, or duplicated and why;
- what model and policy determined the result;
- what exact tokens and EDUs were analysed;
- which primary/eRST decisions, scores, signals, refinements, and component
  identities produced the graph;
- how local units were recombined and which validation checks passed;
- whether the result is semantically cacheable;
- what failed and which earlier stages completed.

## 10. Verify installed command parity

The CLI routes structured inputs through the same `SourceArtifact` boundary and
emits the canonical contract for JSON:

```bash
isanlp-rst parse example.md --format json --output /tmp/isanlp-result.json
```

For the equivalent Python request:

```python
cli_bytes = Path("/tmp/isanlp-result.json").read_bytes()
assert cli_bytes == serialize_contract(result)
```

Instrumentation in conformance tests must prove one primary inference execution
per request. `tree`, `stats`, and `rs3` are declared lossy presentation views of
that same typed result. If `isanlp-rst serve` remains installed, its loopback
endpoint returns the same canonical success or safe failure bytes and derives
health/capability output from `describe_capabilities()`; it never returns raw
exception text or a count-only substitute for the result.

## 11. Run the full implementation gates

```bash
pixi run -e offline lint
pixi run -e offline typecheck
pixi run -e offline mdlint
pixi run -e offline production-api-contract
pixi run -e offline production-ingest-determinism
pixi run -e offline production-ingest-performance
pixi run -e offline build-production
pixi run -e offline validate-production-artifacts
pixi run -e offline production-ingest-clean-install
pixi run -e production production-boundary
pixi run -e production production-clean-install
```

Completion requires observed passing output from every gate, the four tracked
`dist/5.0.0/` files, and successful installation of that exact wheel on the
second supported development machine. Source-checkout tests alone are
insufficient.

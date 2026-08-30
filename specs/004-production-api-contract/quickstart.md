# Quickstart: Production Contract 5.0.0

This is the consumer workflow and installed-wheel acceptance authority. Source
examples are executable before release selection. Steps that require committed
artifacts, the promoted ModernBERT release, or another machine are explicitly
release-gated.

## 1. Verify the tracked release

After certification:

```bash
shasum -a 256 -c dist/5.0.0/release-receipt.sha256
pixi run -e default validate-production-artifacts
```

The validator requires the exact four-file release directory, canonical receipt
and detached digest, matching artifact hashes and sizes, verified wheel
`RECORD`, package/provenance/receipt version agreement, the named source commit
and tree, and every required passed evidence digest.

## 2. Install the exact wheel

After deterministic artifact selection:

```bash
python3.14 -m venv /tmp/isanlp-rst-5-core
/tmp/isanlp-rst-5-core/bin/python -m pip install \
  dist/5.0.0/isanlp_rst-5.0.0-py3-none-any.whl
/tmp/isanlp-rst-5-core/bin/python -m pip check
```

Install the same wheel with `[formats]` for Markdown, Docling, DocLang XML, and
DocLang archive sources. Do not rebuild the sdist on a consuming machine.

## 3. Discover capability without a model

```python
from isanlp_rst.ingest import (
    Availability,
    ModelIdentityState,
    describe_capabilities,
)

capabilities = describe_capabilities()

assert capabilities.semantic.package_version == "5.0.0"
assert capabilities.contract_version == "2.0.0"
assert capabilities.semantic.parser_identity_state is ModelIdentityState.NOT_CONFIGURED
assert capabilities.semantic.cache_eligibility.state.value == "ineligible"

for source_capability in capabilities.semantic.source_forms:
    print(
        source_capability.source_form,
        source_capability.availability,
        source_capability.required_extra,
        source_capability.missing_distributions,
    )
    assert isinstance(source_capability.availability, Availability)
```

This call does not import adapters, instantiate a parser, resolve/download model
bytes, access a network, or inspect `workbench`.

## 4. Prepare and inspect complete evidence

```python
from isanlp_rst.ingest import ProductionIngestor, SourceArtifact

source = SourceArtifact.from_text(
    "A claim. Because evidence supports it.",
    source_name="example.txt",
)
ingestor = ProductionIngestor()
prepared = ingestor.prepare(source)

print(prepared.semantic.source.byte_identity)
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

assert prepared.semantic.inventory_coverage.covered_units == (
    prepared.semantic.inventory_coverage.total_units
)
assert prepared.semantic.mapping_coverage.covered_units == (
    prepared.semantic.mapping_coverage.total_units
)
```

`prepare()` is the explicit intentional-non-analysis operation. Valid retained
content remains accessible as typed values, not only identifiers or digests.

## 5. Plan without loading a model

```python
from isanlp_rst.ingest import CapacityUnit, ParserCapacity, SemanticVersion

capacity = ParserCapacity(
    unit=CapacityUnit.TOKEN_COUNT,
    maximum=8192,
    estimation_algorithm="provider_declared",
    estimation_version=SemanticVersion(root="2.0.0"),
    source="consumer_known_capacity",
)
planned = ingestor.prepare(source, parser_capacity=capacity)

assert planned.semantic.analysis_plan.status.value in {"single_unit", "subdivided"}
for unit in planned.semantic.analysis_plan.units:
    print(
        unit.unit_id,
        unit.first_segment_order,
        unit.last_segment_order,
        unit.boundary_reason,
    )
```

## 6. Analyse with an immutable model release

This section runs after the promoted active ModernBERT release exists in the
local model store.

```python
from pathlib import Path

from isanlp_rst import Parser, RstDocument
from isanlp_rst.ingest import AnalysedOutcome, ProductionIngestor

parser = Parser.from_model_release(
    Path("/absolute/model-releases"),
    "the-promoted-modernbert-release-id",
    family="modernbert",
    device="auto",
)
ingestor = ProductionIngestor(parser=parser)
result = ingestor.analyse(source)

assert isinstance(result, AnalysedOutcome)
assert result.semantic.status.value == "analysed"
assert result.semantic.analysed_document is not None
assert result.semantic.analysis is not None
assert result.semantic.primary_inference is not None
assert result.semantic.parser_result is not None
assert result.semantic.validation is not None and result.semantic.validation.passed
assert result.semantic.anchors
assert result.semantic.parser_result.semantic.loaded_components

document = RstDocument.from_text(
    "A claim. Because evidence supports it.",
    document_id="parser-only",
)
parser_result = parser.analyse_document(document)

assert parser_result.semantic.analysis.document_id == document.document_id
assert parser_result.semantic.analysed_document.edus
assert parser_result.semantic.validation.passed
assert parser_result.semantic.loaded_components
graph_projection = parser.parse_document(document)
assert graph_projection.nodes == parser_result.semantic.analysis.nodes
assert graph_projection.primary_edges == parser_result.semantic.analysis.primary_edges
assert graph_projection.secondary_edges == parser_result.semantic.analysis.secondary_edges
```

`ParserAnalysisResult` is the provider-owned source for the graph, exact
analysed substrate, primary/eRST decisions, refinement, component identities,
loaded-component receipts, recombination, validation, execution, and semantic
identity. Production ingest embeds it; it does not reconstruct evidence from a
graph-only projection.

For eRST, derive a complete policy from the returned resolved default so no
policy field remains implicit:

```python
from isanlp_rst.ingest import AnalysisPolicy, OutputFormalism

erst_policy = AnalysisPolicy.model_validate(
    {
        **result.semantic.policy.model_dump(exclude={"semantic_digest"}),
        "output_formalism": OutputFormalism.ERST_GRAPH,
    }
)
erst_result = ingestor.analyse(source, analysis_policy=erst_policy)

assert erst_result.semantic.erst_completion is not None
for decision in erst_result.semantic.erst_completion.candidate_decisions:
    print(
        decision.candidate_id,
        decision.decision,
        decision.supporting_signal_ids,
        decision.joint_selection_score,
    )
print(erst_result.semantic.erst_completion.decode_receipt)
```

## 7. Persist and reload canonically

```python
from isanlp_rst.ingest import load_contract, serialize_contract

encoded = serialize_contract(prepared)
reloaded = load_contract(encoded)

assert serialize_contract(reloaded) == encoded
assert reloaded.semantic_digest == prepared.semantic_digest
```

The exact same assertions apply to parser results, analysed outcomes, empty
outcomes, capabilities, and failure records.

## 8. Handle typed completed-stage failure

```python
from isanlp_rst.ingest import ProductionIngestError, ProductionIngestor, serialize_contract

try:
    ProductionIngestor().analyse(source)
except ProductionIngestError as error:
    failure = error.failure
    print(failure.failed_stage)
    print(failure.category)
    print(failure.retryability)
    print(failure.completed.kind)

    safe_bytes = serialize_contract(failure)
    assert b"A claim" not in safe_bytes
```

Default rendering and persistence never include raw source/prepared text,
arbitrary exception strings, traceback frames, locals, environment values, or
private paths.

## 9. Verify a consumer uses only the public contract

```python
from isanlp_rst import Parser
from isanlp_rst.ingest import (
    AnalysisPolicy,
    EvidenceDetailPolicy,
    OutputFormalism,
    ProductionIngestError,
    ProductionIngestor,
    SourceArtifact,
    describe_capabilities,
    load_contract,
    serialize_contract,
)
```

A consumer must not import `isanlp_rst.ingest._*`, contract submodules, format
adapters, cache internals, `prepare_source`, or `workbench`. One outcome or
completed-stage failure answers what was received, inventoried, retained,
transformed, analysed, excluded, duplicated, modelled, recombined, validated,
and cached.

## 10. Verify installed command parity

After the promoted model release exists:

```bash
isanlp-rst parse --text "A claim. Because evidence supports it." \
  --source-name example.txt \
  --model-store /absolute/model-releases \
  --release-id the-promoted-modernbert-release-id \
  --output-formalism rst_tree \
  --evidence-detail decision_complete \
  --format canonical-json \
  --output /tmp/isanlp-result.json
```

```python
cli_result = load_contract(Path("/tmp/isanlp-result.json").read_bytes())
assert cli_result.semantic_digest == result.semantic_digest
```

Execution timing may differ; semantic identity must not. `POST /analyse` and
`GET /capabilities` use the same canonical records. `GET /health` is a labelled
presentation projection derived from capability identity. All endpoints are
loopback-only.

## 11. Run the implementation and release gates

```bash
pixi run -e default lint
pixi run -e default typecheck
pixi run -e default mdlint
pixi run -e default production-api-contract
pixi run -e default production-ingest-determinism
pixi run -e default production-ingest-performance
```

After the clean source release commit exists:

```bash
pixi run -e default build-production
pixi run -e default validate-production-artifacts
pixi run -e default production-ingest-clean-install
pixi run -e production production-boundary
pixi run -e production production-clean-install
```

Final certification additionally requires the exact committed artifacts to be
verified without rebuilding on the second supported development machine. That
artifact-, receipt-, model-release-, commit-, tag-, remote-, and second-machine
evidence cannot be truthfully produced from the current dirty source worktree.

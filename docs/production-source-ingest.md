# Production source ingest

`isanlp_rst.ingest` is the production boundary for source acquisition,
inventory, policy, reversible preparation, deterministic planning, parser
analysis, source anchoring, validation, canonical persistence, and the optional
local cache.

Format adapters remain private. `parse_markdown`, `parse_docling`,
`parse_doclang`, their historical result envelopes, and format-owned caches are
not public aliases.

## Source forms and optional packages

| Form | Construction | Provider evidence |
|---|---|---|
| `text` | `SourceArtifact.from_text()` or explicit bytes/path | exact UTF-8 text and source spans |
| `edus` | `SourceArtifact.from_edus()` | exact indivisible EDU sequence |
| `markdown` | path or bytes, `formats` extra | GFM blocks, hierarchy, lists, tables, HTML, metadata, images, and source paths |
| `docling_json` | explicit/inferred `.docling.json`, `formats` extra | validated items, layers, groups, tables, pages, boxes, captions, provenance, and provider attributes |
| `doclang_xml` | `.dclg` path or bytes, `formats` extra | current element heads, layers, tables, lists, notes, captions, metadata, links, paths, and locations |
| `doclang_archive` | `.dclx` path or bytes, `formats` extra | validated OPC members, document XML, asset identities, and archive-member anchors |

Core import and capability discovery do not import the optional adapters.
Attempting an unavailable form produces `source_adapter_distribution_unavailable`
with the required `formats` extra, never a raw `ModuleNotFoundError`.

## Prepare without inference

```python
from pathlib import Path

from isanlp_rst.ingest import ProductionIngestor, SourceArtifact

source = SourceArtifact.from_path(
    Path("example.md"),
    original_source="urn:example:markdown",
)
prepared = ProductionIngestor().prepare(source)

assert prepared.semantic.inventory_coverage.covered_units == (
    prepared.semantic.inventory_coverage.total_units
)
assert prepared.semantic.mapping_coverage.covered_units == (
    prepared.semantic.mapping_coverage.total_units
)
for item in prepared.semantic.inventory:
    print(item.item_id, item.representation.kind, item.disposition.decision)
```

`PreparationOutcome.semantic` contains the source summary, accepted source
contract, resolved preparation/planning policies, complete inventory,
relationships, dispositions, transformations, prepared document, structural
boundaries, plan, exact coverage, and warnings. `execution` contains only
observed adapter and timing facts. The semantic digest excludes execution
variation.

Every valid inventory item has exactly one final disposition:

- `primary` contributes source text to analysis;
- `retained` remains accessible as a typed value;
- `excluded` records a stable reason without pretending the item vanished;
- `duplicate` links to exactly one canonical item.

Representations are closed typed variants for text, tables and cells, lists,
metadata, annotations, media references, structure, cross-references, and
redacted content. A digest is never substituted for a representation the
provider actually has.

## Plan declaratively

```python
from isanlp_rst.ingest import CapacityUnit, ParserCapacity, SemanticVersion

capacity = ParserCapacity(
    unit=CapacityUnit.TOKEN_COUNT,
    maximum=8192,
    estimation_algorithm="provider_declared",
    estimation_version=SemanticVersion(root="2.0.0"),
    source="release_manifest",
)
planned = ProductionIngestor().prepare(source, parser_capacity=capacity)
print(planned.semantic.analysis_plan.status)
```

No capacity gives `not_planned`. A fitting source gives `single_unit`; otherwise
the source is subdivided at complete prepared-segment boundaries. No unit may
truncate a segment or an EDU. A segment larger than usable capacity is a typed
planning failure.

## Analyse with the provider result

```python
from rdam.rst import Parser
from rdam.rst.ingest import ProductionIngestor

parser = Parser.from_model_release(
    Path("/absolute/model-releases"),
    "gumrrg-eb1d5745f3a1",
    device="auto",
)
result = ProductionIngestor(parser=parser).analyse(source)

print(result.semantic.status)
print(result.semantic.composite_identity.primary_parser.state)
print(result.semantic.validation.passed if result.semantic.validation else None)
```

An active release is valid only when its manifest names participating runtime
configuration, weights, and relation inventory files. The runtime loads the complete
parser state, rehashes all loaded files, and refuses an immutable identity claim if
runtime bytes differ.

The neural segmenter and parser never truncate silently. Context overflow,
unaligned tokenizer offsets, boundary-crossing tokens, capped EDUs, or a
dropped suffix fail closed. Contract offsets trim tokenizer-reported leading or
trailing whitespace only; non-whitespace coverage remains exact.

For subdivided analysis, every unit must complete before recombination. The
recombination receipt gives local result identities, node/edge mappings,
boundary inputs, stitching decisions, warnings, and timings. If eRST is
requested, secondary completion runs once over the globally recombined primary
tree, not independently inside units.

## Empty primary discourse

Empty, whitespace-only, or retained-only input is a successful preparation.
Analysis returns `EmptyPrimaryAnalysisOutcome` with status
`empty_primary_discourse`, the complete preparation outcome, an explicit
not-used component identity, and no fabricated root, graph, anchors, or parser
result.

## Cache

`cache_directory` enables an atomic content-addressed cache only when every
participating component has an immutable exact runtime identity. Its request
identity covers source, complete preparation, analysis plan, capacity, resolved
policy, and composite component identity.

Only a fully validated canonical outcome is stored. Retrieval verifies record
schema, semantic digest, request binding, result binding, parser result, graph,
anchors, and validation receipt. Corruption and persistence failures are typed;
they are never silently treated as a cache miss.

## Canonical persistence

```python
from isanlp_rst.ingest import load_contract, serialize_contract

payload = serialize_contract(result)
reloaded = load_contract(payload)
assert serialize_contract(reloaded) == payload
assert reloaded.semantic_digest == result.semantic_digest
```

Canonical bytes are strict UTF-8 I-JSON under RFC 8785. Duplicate object keys,
non-finite numbers, unsafe integers, unpaired surrogates, unknown fields,
unsupported versions, unknown discriminators, and semantic-digest
contradictions are rejected.

## Failures

```python
from isanlp_rst.ingest import ProductionIngestError, serialize_contract

try:
    ProductionIngestor(parser=parser).analyse(source)
except ProductionIngestError as error:
    print(error.failure.failed_stage, error.failure.code)
    safe_payload = serialize_contract(error.failure)
```

Completed evidence is monotonic: acquisition, inventory, preparation,
inference, validation, and assembly variants may be carried only when that
stage genuinely completed before the failure. The default serialized projection
retains identities and counts while redacting private representation values.

## Verification

```bash
pixi run -e default production-api-contract
pixi run -e default production-ingest-determinism
pixi run -e default production-ingest-performance
pixi run -e default lint
pixi run -e default typecheck
pixi run -e default mdlint
```

These source checks do not certify a wheel. Distribution certification also
requires deterministic exact-commit artifacts, local clean installs, exact
loaded-model evidence, and second-machine verification of the committed wheel.

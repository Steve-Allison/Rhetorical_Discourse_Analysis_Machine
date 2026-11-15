# Production source ingest

`rdam.ingest` is the production boundary for source acquisition,
inventory, policy, reversible preparation, deterministic planning, parser
analysis, source anchoring, validation, canonical persistence, and the optional
local cache.

Format adapters remain private. `parse_markdown`, `parse_docling`,
`parse_doclang`, their historical result envelopes, and format-owned caches are
not public aliases.

## Source forms and core dependencies

| Form | Construction | Provider evidence |
|---|---|---|
| `text` | `SourceArtifact.from_text()` or `.txt` / `.text` path/bytes | synthesized into namespaced `<doclang>` XML; exact UTF-8 text and source spans |
| `edus` | `SourceArtifact.from_edus()` | exact indivisible EDU sequence |
| `doclang_xml` | `.dclg` / `.dclg.xml` path or bytes | `dclq` `LoadedDocument` XPath/page/section indexing + `doclang` XSD/Schematron-validated elements, layers, tables, lists, notes, captions, descriptions, `<track>` turns, metadata, links, and locations |
| `doclang_archive` | `.dclx` path or bytes | validated OPC members, `document.xml`, asset identities, and archive-member anchors |

`dclq` (`>=2.107.0,<3`) and `doclang[schematron-saxon]` ship in core
`[project.dependencies]` (`pyproject.toml:44-45`); raw `DoclingDocument` JSON and
Markdown ingestion (`_inventory_docling`, `rdam.rst.markdown`, and the separate
`formats` extra) were retired in `rdam` `6.1.0` (`rdam/ingest/contracts/source.py:17-21`).

DocLang tracks upstream `main` by immutable commit: `pyproject.toml:45` and
`tests/fixtures/doclang/upstream-manifest.json` both pin
`ae8ad5490b9b03b344e3e49dcb0f6f2209795de6` (`v0.9.0`, 62 valid specimens and 78
invalid specimens), and the source contract records `upstream_version`
(`0.9.0+git.ae8ad5490b9b03b344e3e49dcb0f6f2209795de6` at `rdam/ingest/_doclang.py:74-80`).
`dclq` tracks its latest `2.x` release (`>=2.107.0,<3`). Status verified on
2026-11-15. Do not equate locked compatibility with latest-upstream conformance.

Only non-content `furniture`, decorative picture wrappers (`logo`, `icon`,
`qr_code`, `barcode`, `stamp`, `signature`, `decorative` at
`rdam/ingest/_doclang.py:54-56`), and operational provenance are pruned from
substantive projections. Centering and all ten LLM-capable providers consume one
unified XPath-anchored stream (`SUBSTANTIVE_CLASSES` at
`rdam/ingest/requirements.py:10-24`) admitting titles, headings, paragraphs,
list items, turns, captions, VLM `<description>` blocks (`picture_description`),
speaker `<notes>`, code, formulas, tables, cells, and fields, enriched by the
shared `LinguisticSubstrate` (`rdam/ingest/substrate.py:330-346`). Neural
`RstProvider` uses `AUTHORED_PROSE_V1` so trained prose segmenters and tree
decoders receive prose, headings, list items, and turns while retaining tables,
notes, code, formulas, and visual descriptions as receipted side channels.

A DocLang `<track>` (a time-aligned media transcript) decodes into speaker turns:
each turn's text is primary `turn` content, attributed to its `<voice>` speaker or
explicitly unresolved, with its cue block's inclusive start and end milliseconds in
`cue_start_ms` / `cue_end_ms`. A `<chapter>` is a heading placed before its cue's
text; `<cover>`, `<frame>`, and `<audio>` are retained media with their source
references (`rdam/ingest/_doclang.py:147-160,310-336`).
The normative upstream authority is the
[DocLang specification](https://github.com/doclang-project/doclang/blob/main/spec.md).
Fixture schemas and RDAM's own v3 envelope are independently versioned.

## Prepare without inference

```python
from pathlib import Path

from rdam.ingest import ProductionIngestor, SourceArtifact

source = SourceArtifact.from_path(
    Path("tests/fixtures/doclang/real_world/change-of-tenancy.dclg"),
    original_source="urn:example:doclang",
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

Every valid inventory item has a typed `DispositionDecision`
(`rdam/ingest/contracts/source.py:64-70`):

- `primary` contributes source text to analysis;
- `retained` remains accessible as a typed non-primary value;
- `transformed` records normalized or linearised representations;
- `duplicate` links to exactly one primary item;
- `rejected_invalid` records an invalid source item.

Representations are closed typed variants for text, tables and cells, lists,
metadata, annotations, media references, structure, cross-references, and
redacted content. A digest is never substituted for a representation the
provider actually has.

## Plan declaratively

```python
from rdam.ingest import CapacityUnit, AnalysisCapacity, SemanticVersion

capacity = AnalysisCapacity(
    unit=CapacityUnit.TOKEN_COUNT,
    maximum=8192,
    estimation_algorithm="whitespace_token_count",
    estimation_version=SemanticVersion(root="1.0.0"),
    source="application_input_budget",
)
planned = ProductionIngestor().prepare(source, capacity=capacity)
print(planned.semantic.analysis_plan.status)
```

The numerical value above is an explicitly supplied application budget, not a
trained parser limit. Provider capacities are derived from their declared evidence;
`maximum=None` means no established numerical limit, not unlimited capacity.
No capacity gives `not_planned`. A fitting source gives `single_unit`; otherwise
the source is subdivided at complete prepared-segment boundaries. No unit may
truncate a segment or an EDU. A segment larger than usable capacity is a typed
planning failure.

## Analyse with the provider result

```python
from rdam.rst import Parser
from rdam.ingest import ProductionIngestor

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
unaligned tokenizer offsets, capped EDUs, or a
dropped suffix fail closed. Contract offsets trim tokenizer-reported leading or
trailing whitespace only; non-whitespace coverage remains exact. A token that
overlaps multiple EDUs retains every exact overlap, rather than being discarded.

For subdivided analysis, every unit must complete before recombination. The
recombination receipt gives local result identities, node/edge mappings,
boundary inputs, stitching decisions, warnings, and timings. Production ingest
supports primary RST only. Experimental eRST completion is available separately
in `workbench/erst/`, including completion of a supplied recombined primary result.

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
from rdam.ingest import load_contract, serialize_contract

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
from rdam.ingest import ProductionIngestError, serialize_contract

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

These source checks do not certify a wheel. When a release is requested, verify
the built artifacts and a clean local installation using the repository's
existing build and installation commands. No second-machine ceremony is required.

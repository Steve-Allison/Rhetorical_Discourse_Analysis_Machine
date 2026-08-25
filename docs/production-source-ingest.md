# Production source ingest

`isanlp_rst.ingest` is the only production API for turning real-world source
material into an RST analysis. It owns source validation, complete inventory,
relevance policy, reversible preparation, structural subdivision, analysis,
source anchoring, deterministic serialization, and the optional local cache.

The removed `parse_markdown`, `parse_docling`, and `parse_doclang` functions are
not deprecated aliases. They no longer exist, and their separate result
envelopes and caches are not supported.

## Supported source forms

| `SourceForm` | Construction | Validation and addressing |
|---|---|---|
| `PLAIN_TEXT` | `SourceArtifact.from_text()` | Exact Unicode characters and source ranges |
| `PRESEGMENTED_EDUS` | `SourceArtifact.from_edus()` | Exact EDU sequence; supplied boundaries are indivisible |
| `MARKDOWN` | `SourceArtifact.from_path()` or `from_bytes()` | CommonMark/GFM tokens, source lines, parsed HTML nodes |
| `DOCLING_JSON` | `from_path(..., source_form=...)` or `from_bytes()` | Current `docling-core` validation, JSON pointers, layers, groups, pages, tables and provenance |
| `DOCLANG_XML` | `SourceArtifact.from_path()` or `from_bytes()` | Current DocLang XSD and Schematron validation, canonical local-name XML paths |
| `DOCLANG_ARCHIVE` | `SourceArtifact.from_path()` or `from_bytes()` | Bounded in-memory `.dclx` OPC validation, required content types/root relationship, validated `document.xml`, page bounds and asset identities |

Ambiguous JSON, XML, text, extensionless, and byte inputs require an explicit
`SourceForm`. Identification never substitutes for validation.

Current DocLang `.dclx` input is an Open Packaging Conventions ZIP package. It
must contain `[Content_Types].xml`, `_rels/.rels`, and `document.xml`; the
content-types part must declare the DocLang document media type, and the root
relationships part must identify `document.xml` with the current DocLang
relationship URI. Relative `<src>` assets must resolve to package parts, and
page-image numbers cannot exceed the page count expressed by top-level
`<page_break/>` elements. The former bare ZIP containing only `document.xml`
is rejected rather than treated as a compatibility format.

## Analyse a source

```python
from pathlib import Path

from isanlp_rst import Parser
from isanlp_rst.ingest import (
    AUTHORED_PROSE_V1,
    ProductionIngestor,
    SourceArtifact,
)

parser = Parser.from_model_release(
    Path("/absolute/path/to/model-releases"),
    "gumrrg-eb1d5745f3a1",
    family="dmrst",
    device="auto",
)
ingestor = ProductionIngestor(parser=parser)

artifact = SourceArtifact.from_path(
    Path("/absolute/path/to/source.md"),
    original_source="local:source.md",
)
result = ingestor.analyse(
    artifact,
    policy=AUTHORED_PROSE_V1,
    cache_dir=Path("/absolute/path/to/cache"),
)
```

Construct a plain-text or exact-EDU artifact without a file:

```python
text_artifact = SourceArtifact.from_text(
    "The context is clear. Therefore, the decision follows.",
    source_name="decision.txt",
)

edu_artifact = SourceArtifact.from_edus(
    ("The context is clear.", "Therefore, the decision follows."),
    source_name="decision.edus",
)
```

`analyse_source()` is the functional convenience form of the same service. It
does not create a second pipeline.

## What the default policy analyses

`AUTHORED_PROSE_V1` inventories the entire valid source before deciding what
enters primary RST analysis.

| Disposition | Default material |
|---|---|
| Primary | Authored titles, headings, paragraphs, meaningful list items and authored turns |
| Retained side channel | Captions, tables and cells, code, formulas, raw markup, pictures, metadata, groups, fields, assets and unknown valid content |
| Excluded from primary but retained in receipt | Machine-generated picture descriptions, notes, navigation, furniture, backgrounds and invisible content |

Every inventory item receives exactly one disposition. Exact duplicates are
reported but authored repetition is not silently removed. There are no
format-specific booleans that can widen the production default.

## Preparation and provenance

`ProductionIngestor.prepare()` runs validation, inventory, policy,
transformation, structure planning and coverage verification without model
inference or a durable analysis-cache write.

The resulting `PreparedRstDocument` contains:

- the exact prepared text;
- source-derived and explicit synthetic segments;
- reversible prepared/source ranges and native anchors;
- structure nodes used for subdivision;
- primary and retained side-channel item identities;
- a deterministic semantic digest.

Source text is preserved by default. Any required line-ending, whitespace or
format transformation must be explicit and mapped. An unresolved native
reference, inventory gap, overlap, duplicate mapping or unreceipted
transformation fails closed.

## Result acceptance

`ProductionAnalysisResult` contains the source summary, prepared document,
preparation and execution receipts, optional coherent `RstAnalysis`, analysis
anchors, cache fingerprint and semantic digest.

Require complete accounting before consuming an analysis:

```python
receipt = result.preparation_receipt
assert receipt.inventory_coverage == 1.0
assert receipt.primary_source_coverage == 1.0
assert receipt.prepared_text_coverage == 1.0
assert receipt.analysis_anchor_coverage == 1.0
```

When no authored primary discourse exists, the result uses
`empty_primary_discourse`, retains the full inventory and dispositions, and
contains no fabricated tree.

## Long documents

The service derives safe unit capacity from the loaded parser. It partitions at
source structure first, recursively subdivides only when necessary, analyses
local and macro units with the unchanged released model, and stitches one
coherent tree. Pre-segmented EDUs are indivisible. No route truncates the source
or uses a format-specific character ceiling.

## Cache behavior

The optional cache is local, content-addressed and analytical. Its identity
covers:

- raw source and declared/accepted source contract;
- validator and adapter behavior;
- preparation policy and implementation;
- immutable released-model files and parser capability;
- result schema and semantic payload.

Validation and preparation identity are established before cache lookup. A
changed identity is a normal miss. A corrupt, stale or contradictory entry is
an actionable failure, never a silent hit or silent miss. Injected parsers
without an immutable released-model identity may analyse but cannot write or
reuse the durable cache.

## Serialization

The canonical envelope is `isanlp_rst_ingest` version `1.0.0`.
`model_dump_json()` emits strict UTF-8 JSON. Semantic content and the execution
receipt are separate: timestamps, timings, peak RSS and cache-hit observations
remain truthful evidence without changing analytical equality.

## Runtime boundary

The installed production wheel contains the ingest service and its private
format helpers. It contains and imports no training corpus, corpus compiler,
trainer, evaluator, Gold Set, benchmark, research harness or repository tool.
Gold Set comparison and Parseval scoring consume serialized production results
from the repository-only side; production never imports them.

Build and verify the exact wheel:

```bash
pixi run -e offline build-production
pixi run -e offline production-ingest-public-api
pixi run -e offline production-ingest-conformance
pixi run -e offline production-ingest-clean-install
pixi run -e production production-boundary
```

The built-wheel clean-install test runs all five source families outside the
repository with offline/training/evaluation packages unavailable.

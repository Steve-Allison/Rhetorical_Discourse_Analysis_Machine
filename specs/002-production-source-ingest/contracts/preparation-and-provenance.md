# Contract: Preparation, Structure, and Provenance

## Required stage order

Every production source follows this exact semantic order:

1. materialize immutable source bytes or EDU array;
2. identify the declared source form;
3. validate against the current source contract;
4. inventory all validator-visible content and structure;
5. reconcile inventory completeness;
6. apply one immutable named relevance policy;
7. prepare text and reversible mappings;
8. derive structure-aware analysis units;
9. prove source and prepared-text coverage;
10. compute analytical identity and inspect the cache;
11. analyse local units and recursive macro structure;
12. anchor every final analysis object;
13. verify the complete result and persist it atomically.

Validation and complete inventory occur before cache lookup or relevance
filtering. No stage may silently repair a source so that a later validator sees
something different from what the caller submitted.

## Source-specific validation and inventory

### Plain text and presegmented EDUs

- Preserve submitted Unicode characters and line endings in the immutable
  artifact.
- Inventory the document, lines/paragraphs, and supplied EDU boundaries.
- Reject invalid encodings, empty EDU entries, and boundary contradictions.
- Treat caller-supplied EDU segmentation as data, not as training labels.

### Markdown

- Parse CommonMark/GFM structure; never decide relevance by regex-stripping.
- Inventory headings, paragraphs, lists/items, block quotes, code, tables, raw
  HTML, thematic/structural nodes, links, and source spans.
- Parse raw HTML with the installed hardened lxml parser. Never execute scripts,
  expand entities, retrieve resources, or render a browser DOM.
- Preserve Markdown and HTML-native anchors and DOM ancestry.

### Docling JSON

- Capture raw `schema_name` and `version` before loading.
- Validate using current `DoclingDocument.load_from_json` semantics.
- Record both the raw declaration and normalized accepted document contract.
- Traverse all current content layers with groups and pictures enabled, then
  reconcile the traversal against every top-level collection and reference.
- Retain item references, page numbers, bounding boxes, content layers,
  headings, groups, tables/cells, pictures/captions/descriptions, notes, and
  provenance fields even when policy excludes them from primary discourse.

### DocLang XML and archive

- Run current full XSD plus Schematron validation with empty namespace allowed.
- Support `.dclg`, `.dclg.xml`, and the current `.dclx` OPC/ZIP archive form.
- For `.dclx`, reject absolute/traversal names, symlinks, duplicate members,
  encrypted members, unsupported compression, excessive member/archive sizes,
  suspicious compression ratios, missing/duplicate `document.xml`, and invalid
  relationships. Read in memory or an isolated temporary directory and never
  execute or fetch an asset.
- Inventory all head, semantic, structural, layout, origin, thread/layer, field,
  asset, list, and recursively nested table content accepted by the validator.
- Valid nested tables are retained structurally; they are not flattened or
  rejected merely because primary RST does not analyse them.

## Default production policy: `authored_prose_v1`

| Content | Default disposition | Reason |
|---|---|---|
| Titles and authored headings | Primary | Discourse organization and macro structure |
| Authored paragraphs | Primary | Core discourse |
| Meaningful authored list-item text | Primary | Authored propositions with list ancestry |
| Authored or human-transcribed turns | Primary | Core conversational discourse |
| Block-quote prose | Primary with quote ancestry | Authored document discourse when source-present |
| Captions | Side channel | Contextual text, not assumed part of main discourse |
| Tables, rows, cells | Side channel | Preserve structure; do not invent linear discourse |
| Code and formulas | Side channel | Not natural-language discourse by default |
| Raw markup and metadata | Side channel | Source evidence, not prose |
| Script, style, template, navigation | Excluded and retained | Irrelevant or unsafe for discourse |
| Furniture, background, invisible layers | Excluded and retained | Layout/system content |
| Machine picture descriptions | Excluded and retained | Machine-generated, not source-authored discourse |
| Pictures and assets | Side channel | Preserve identity/placement, no fabricated text |
| Slide/speaker notes | Excluded and retained | Separate presentation channel by default |
| Unknown valid item | Side channel and `not_analysed` | Fail visible without destroying valid source content |

Callers may select another versioned named policy. They cannot mutate a shared
policy, pass arbitrary per-document exceptions, or request partial results.

## Duplicate handling

The system reports exact repeated primary-candidate text with item identities
and structure before taking action. The default retains authored repetitions,
because repetition may be intentional discourse. A named policy may deduplicate
only when provenance establishes that the repetition is a conversion artifact;
the canonical item and every replaced item remain in the receipt.

Similarity-based fuzzy deduplication is prohibited in production preparation.

## Text preparation and transformations

- Preserve source text by default; do not call unreceipted `strip`, whitespace
  collapse, compatibility normalization, or case folding.
- A named transformation records original and derived text, exact ranges,
  algorithm/version, and a reversible position map.
- Canonical NFC is allowed only through such a transformation. NFKC/NFKD are
  prohibited for prepared discourse.
- Separators are explicit synthetic segments chosen from source structure; they
  never receive source anchors.
- Each prepared character belongs to exactly one segment. Source-derived
  segments preserve exact native selectors and structural ancestry.
- The prepared `RstDocument` is constructed once from this canonical mapping;
  format adapters do not manufacture independent parser inputs.

## Structure-aware subdivision

The source hierarchy constrains parser input before inference:

1. build canonical document/section/group/slide/turn/list/paragraph structure;
2. select the largest complete structural unit within the released parser's
   declared capacity;
3. split an oversized unit at the deepest valid source boundary;
4. fall back deterministically to paragraph, sentence, EDU, then safe character
   ranges only when source structure cannot satisfy capacity;
5. record every fallback and its reason;
6. parse leaf units locally;
7. derive deterministic, anchored nuclear-spine macro representations from the
   full local analyses—not arbitrary text prefixes;
8. recursively analyse parents until one coherent document tree exists;
9. project all macro relations back to descendant EDU/source anchors.

Context may be supplied to adjacent units when the parser contract allows it,
but context-only EDUs are removed by stable identity before final assembly.
Every primary EDU appears exactly once in the final ordered tree.

There is no global 200,000-character rejection. A one-million-character source
must succeed within the performance and memory acceptance bounds when otherwise
valid.

## Coverage invariants

### Inventory coverage

```text
validated inventory item IDs
  = exactly-once union of final disposition item IDs
```

### Primary source coverage

```text
eligible source intervals
  = exactly-once union of source-derived prepared segment mappings
```

Receipted transformations must provide a total map; synthetic segments are
excluded from both sides.

### Prepared-text coverage

```text
[0, len(prepared_text))
  = contiguous non-overlapping union of prepared segment ranges
```

### Analysis coverage

```text
all final EDU IDs
  = exactly-once ordered union of leaf-unit output EDU IDs
```

Every EDU, relation, and tree node has at least one prepared range and at least
one source-derived descendant anchor. Macro representations link to the source
anchors from which they were derived.

Coverage below 100%, overlap, a dangling reference, or an impossible reverse
map is a production failure, not a warning.

## Cache contract

The cache fingerprint includes:

- exact raw source digest and frozen source form;
- submitted source name, original-source identity, and conversion provenance;
- raw and accepted source-contract identities;
- validator distribution, version, profile, and adapter digest;
- inventory, policy, transformation, structure, and subdivision digests;
- released parser/model/tokenizer/segmenter file digests;
- production package and result-schema versions.

Fingerprint input uses canonical JSON. Current validation, inventory,
preparation, and coverage proof always precede cache lookup. A matching hit is
accepted only after key, embedded identity, semantic digest, and stored payload
digest agree. Contradiction or corruption fails visibly. Writes use a temporary
file, flush/sync, and atomic replace on the same filesystem.

## Semantic and execution evidence

Two executions are semantically equal when their canonical source, preparation,
subdivision, model, final analysis, anchors, and preparation receipt match.
Timestamp, duration, RSS, host, and cache hit/miss are execution evidence and do
not participate in semantic equality.

This separation is mandatory for the ten-run determinism gate: cached and
uncached runs must be semantically identical while retaining truthful,
necessarily different execution observations.

# Feature 020: Consolidate DocLang decoding

Date: 2026-09-12. Status: approved by the user for full implementation. Execution results are recorded in `implementation-results.md`.

## Problem and outcome

The current DocLang path spreads text and table decoding across `rdam/ingest/doclang/text_walker.py`, `rdam/ingest/_harvest.py` and `rdam/ingest/prepare.py`. It converts current source contracts to legacy contracts and converts the resulting inventory back. Archive checking and harvesting also construct separate RDAM XML trees. These are code-inspection findings, detailed in [research](research.md).

Create one private DocLang decoding layer, consume it directly into current RDAM inventory contracts, reuse one RDAM-owned document tree, and provide private fragment addressing for precise text extraction and verification. Preserve source semantics, validation and the existing public entry points.

## Scope and decisions proposed for approval

- Cover both standalone `.dclg` and `.dclx` inputs.
- Include current-spec and fixture reconciliation, exactly-once mixed-content extraction, lists, tables and merged cells, pictures, metadata, layers, paths, package assets, typed inventory, identity/cache implications and regression verification.
- Keep fragment addressing private. Existing serialized element paths and source-anchor schemas remain the public contract.
- Retain the official DocLang validator and its required optional dependencies. Remove only RDAM's redundant parsing; do not promise one parse across the validator's independent engines.
- Learn from `docling-nlp` without depending on it, copying its C++ implementation, adopting its annotation graph or introducing a new public document API.
- Preserve other source-form implementations. Only shared integration changes and directly necessary test/tool repairs belong to this feature.
- Do not add NLP extraction, transcription, archive writing, annotation-sidecar interpretation, a new release system, publication or model changes.

## Requirements

| ID | Requirement |
|---|---|
| D01 | Resolve current upstream DocLang/Docling version and fixture drift before decoder migration; pin evidence to immutable revisions. |
| D02 | A private document object owns exact XML bytes, one RDAM tree and one canonical local-name path index for each decode operation. |
| D03 | Standalone and archive inputs use the same XML validation and decoding semantics. Archive identities remain bound to original container/member bytes. |
| D04 | One text-fragment traversal owns text/tail inclusion, metadata exclusion and structural boundaries. Every eligible fragment occurs exactly once in its intended content surface. |
| D05 | One table scan determines cells, coordinates, continuation ownership, spans and associated text; no subsequent coordinate-string parsing reconstructs those facts. |
| D06 | DocLang emits current typed inventory and source contracts directly, without constructing legacy source, inventory or anchor models. |
| D07 | Preserve inventory order, element IDs, classifications, origins, relationships, attributes, asset records and public anchors for semantically unchanged cases. |
| D08 | Preserve prepared text, boundaries, dispositions, provider-specific projections, source evidence and failure classification, except for individually demonstrated defects corrected against normative evidence. |
| D09 | Keep bounded ZIP checks, OPC validation, asset-reference checks, safe XML settings and official schema validation. No document may be exposed as validated after only a successful XML parse. |
| D10 | Private fragment selectors resolve against the same tree and support exact unnormalized text recovery; they never silently replace persisted element paths. |
| D11 | Implementation identity must include the actual decoder/text/mapping dependencies so changed preparation code cannot reuse stale cache entries. Historical serialized results remain readable. |
| D12 | No mutable XML tree escapes into public immutable results or a process-wide cache; independent requests cannot share mutable parse state. |
| D13 | Tests exercise real decoding and public preparation. Mutation checks distinguish assertion failures from broken setup, imports, collection, missing targets and timeouts. |
| D14 | Measure document preparation before/after on the same local inputs; report latency and memory honestly without inventing a speedup target. |

## Acceptance scenarios

1. A valid namespaced document and its namespace-free equivalent retain canonical local-name selectors and correct source text. XML formatting, comments, metadata tails, CDATA and Unicode do not duplicate or drop body text.
2. Raw and wrapped list/table forms decode through one content walker. Empty cells and horizontal/vertical continuation markers preserve coordinates and spans, while wrapper items remain accounted for without becoming extra cells.
3. A valid archive yields the same semantic document content as its `document.xml`, with appropriate container-specific identities and assets. A bare ZIP or invalid OPC relationship remains rejected where the normative contract requires it.
4. Invalid current upstream specimens fail through both official validation and RDAM's public preparation boundary. Package and XML failures retain their appropriate cause/category without partial success.
5. Existing valid outputs match the baseline field by field. Any corrected output has a source-grounded expected result and a failing-before/passing-after regression case; broad baseline regeneration is insufficient.
6. Direct DocLang dispatch leaves text, EDUs, Markdown and Docling JSON behaviour unchanged, including lazy optional dependency loading.
7. Every private fragment resolves to its exact source text. Generated fragment selectors do not appear in serialized public anchors, caches or schema declarations.
8. Refactoring removes the DocLang legacy conversion path and redundant RDAM XML parse, with profiling and causal tests supporting those claims.

## Success criteria

- Requirements D01-D14 are each mapped to implementation work and named acceptance checks in the [plan](plan.md).
- No unresolved analytical or source-anchor differences remain in the migration comparison.
- Current normative fixtures, adversarial package cases, typed preparation, relevant provider projections and non-DocLang regressions pass.
- Applicable lint, strict typing, format coverage, causal mutation and production-boundary checks pass without suppressions or weakened tests.
- Scope remains private Python ingestion work; no dependency on `docling-nlp`, model change or external publication is introduced.

The focused planning baseline was 98 passed in 0.85 seconds. That result establishes only the four test files listed in [quickstart](quickstart.md), not implementation readiness or complete current-spec coverage.

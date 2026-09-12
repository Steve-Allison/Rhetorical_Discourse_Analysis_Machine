# DocLang refactor compatibility contract

Status: approved. This document specifies preservation of existing interfaces; it introduces no new external interface.

## Public behaviour to preserve

Continue using existing source constructors, `rdam.ingest` preparation/analysis, machine preparation and serialization. Neither a public `DoclangDocument` nor a new source form, anchor discriminator, CLI option or HTTP field is added.

For the same accepted input and options, compare the following fields rather than checking only aggregate counts:

| Category | Required equality |
|---|---|
| Source | Original payload bytes, byte hash, source identity, declared origin and conversion provenance. |
| Inventory | Order, item IDs, class, parent/children, source layer/authorship, representation fields, attributes and relationships. |
| Text | Exact text before/after the already declared normalization, spaces/tails, prepared ranges and source quotations. |
| Tables | All cell IDs, coordinates, headers, row/column spans, text and ordered linked items; wrapper/marker accounting. |
| Anchors | Existing element paths, page/location coordinates and their resolution, archive member identities and selectors. |
| Preparation | Dispositions, retained content, structural boundaries, segment order, transformations and warnings. |
| Provider input | Content admitted by each existing requirement and exact mapping from projected text/cells to source anchors. |
| Failures | Malformed/unsafe inputs remain rejected at the corresponding public stage/category, retaining causes without exposing private contents. |
| Serialization | Current shapes/discriminators, historical reading, and no mutable XML/private fragment objects in public output. |

Different containers around identical XML legitimately have different source/member identities. Compare their decoded document semantics separately; do not require `.dclg` and `.dclx` outputs to be byte-identical.

## Differences that must be classified

1. Execution IDs and durations: compare structure and validity, not exact values.
2. Truthful implementation fingerprints: decoder changes must change the existing identity. Document the exact affected field and its derivation, including dependent digests; do not remove entire source-contract subtrees from the comparison.
3. Proven defects: before altering the expectation, provide a source specimen accepted by the selected validator, the precise wrong old result, the normative expected result and a regression through public preparation. Apply the narrow correction, then record the exact changed fields.

No other difference is accepted merely because the final tests pass. Public shape or anchor changes require an explicit plan revision rather than an automatic schema bump.

## Validation and archive invariants

Preserve official validation and safe XML parser settings. Preserve existing member-count, per-member size, total uncompressed size and compression-ratio bounds; duplicate names, traversal paths, symlinks, encryption and inconsistent ZIP metadata fail.

Retain normative OPC checks and existing content-type/relationship/asset/page-image behaviour. Do not adopt `docling-nlp`'s less restrictive read acceptance as the definition of DocLang compliance. External asset references remain references; decoding does not fetch them.

Annotations or unknown archive payloads retain their current asset identity treatment. They are not parsed into NLP or summary content by this feature. New upstream-main track/media acceptance is explicitly outside the released-validator boundary recorded in research, not silently reported as supported.

## Private fragment contract

Use exact source-tree slot addressing, preserve whitespace and exclude outer tails only when the selected content-surface rule requires it. A missing fragment raises an error; an empty fragment remains distinguishable. No arbitrary XPath evaluation and no normalized offsets presented as original XML byte offsets.

Keep canonical public element paths independent of private fragment selectors. The latter must not appear in output anchors or change item IDs. A future public fragment citation feature would require an explicit migration design.

## Import and cache boundaries

Constructing a source request must not eagerly load optional format validators, model runtimes or a mutable document. Non-DocLang paths must continue to operate without importing `doclang`. Production code imports no workbench/dev dependency.

Repeated identical decodes yield the same semantic output and current implementation identity. Different source bytes or changed decoder identity must not reuse stale prepared/projection results. Historical results remain interpretable under their stored identity.

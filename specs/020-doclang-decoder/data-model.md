# Private DocLang data model

Status: private implementation design. These types are private and are not JSON schemas, public exports or persisted results.

## Document ownership

`DoclangDocument` owns:

- `xml_bytes: bytes`: exact material submitted to official validation and RDAM parsing.
- A private lxml root: constructed once by RDAM and never mutated after construction.
- Element-to-canonical-path and path-to-element indexes built together in one traversal.
- Source namespace/version facts actually present in the root, without inferred defaults.

An internal construction function completes applicable official validation and archive checks before returning the validated document to the decoder. A parsed tree alone is not a validation result. Failed construction raises the existing appropriate exception; it does not return a partly initialized object or an `is_valid=False` object that consumers might accidentally use.

An optional private archive result composes the document with ordered existing `DoclangArchiveMember` records. Retain exact member/container identities. Do not retain all binary asset payloads after bounded checking, add archive mutation, or expose the tree on `SourceArtifact`.

Official validation remains independent and path-based. For in-memory XML, write the exact XML bytes to a bounded-lifetime temporary file, call the public validator with current options, and close/remove the file on success or failure. Never substitute reserialized XML for the source bytes.

## Text fragments and private selectors

`DoclangTextFragment` is a frozen, slotted record:

| Field | Meaning |
|---|---|
| `selector` | `ElementTextSlot` or `NonElementTailSlot`, the private discriminated selector defined below. |
| `text: str` | Exact unnormalized slot value. |
| `surface_path: str` | Content element/list item/cell to which the fragment contributes. |

Define two frozen, slotted selector records:

- `ElementTextSlot(kind='element_slot', owner_path: str, slot: Literal['text', 'tail'])`. Tail belongs to the named child, not its parent.
- `NonElementTailSlot(kind='non_element_tail', parent_path: str, child_index: int, node_kind: Literal['comment', 'processing_instruction'])`. The index is zero-based among all direct lxml child nodes, including elements/comments/processing instructions, and must be nonnegative. Resolution verifies the node kind before returning its tail.

Do not label either selector XPath `text()[n]` or invent a persisted element path for a non-element node. Include comments and processing-instruction tails in round-trip tests. The tree remains unmodified, so the private child index cannot drift during decoding.

`resolve_fragment(selector)` returns the exact slot text from the same tree or raises a specific lookup error. Empty text and missing slot/path must be distinguished. It does not normalize Unicode, strip whitespace, fetch URLs or evaluate arbitrary XPath.

Text surfaces concatenate ordered fragments exactly once. Apply only the selected surface's existing trim policy after concatenation. Retain a private fragment-to-surface character mapping where trimming changes boundaries; offsets are Python Unicode code-point indexes within decoded text, never byte offsets into XML markup. Do not claim normalization is reversible from offsets alone.

A fragment may be observed by structural inventory and by one selected content surface; exactly-once means no duplication within the emitted surface/prepared content. It does not prohibit retaining source structure alongside its semantic representation.

## Decoded elements and cells

`DecodedDoclangItem` is a frozen, slotted source-format record containing canonical path, parent/child paths, local name, source attributes, direct layer/location facts, optional text surface and optional table facts. It carries no RST relations, provider policy or legacy model instances.

Traversal must visit all semantic XML elements in document order, even when an element is excluded from authored text. Build paths and parent/child relationships once. Carry relevant ancestor context during traversal rather than rescanning all ancestors for every item.

`DecodedDoclangCell` contains:

- Marker element path and local marker name.
- Integer row and column, computed from the table's marker stream.
- Row/column span and owning cell for continuation markers.
- Header status, ordered linked item paths and text fragments.
- Empty-cell representation distinguished from absent/invalid coordinates.

Cell grid construction is local to each table. Continuation resolution must reject impossible ownership against the validated format semantics rather than guessing a coordinate or silently dropping text. Preserve all marker/wrapper inventory items even when only owning cells appear in `TableRepresentation.cells`.

## Direct RDAM mapping

`rdam.ingest._doclang.inventory_doclang(artifact)` returns the existing pair:

`tuple[tuple[ContentInventoryItem, ...], SourceContractIdentity]`.

It maps source records into current `TextRepresentation`, `TableRepresentation`, `TableCell`, metadata/annotation/media/structure representations and current anchor models. It preserves existing classification/back-matter/speaker policy and deterministic order. Format facts stay in the decoder; RDAM-specific classification and disposition remain at the ingestion/policy layer.

The mapper constructs typed locations/cell anchors directly. It must not build a legacy `NativeAnchor`, concatenate a selector string and parse it again. Invalid source coordinates fail with context rather than falling back to zero.

## Identity and lifecycle

Lifecycle: exact source bytes → bounded acquisition → RDAM parse plus official validation/package checks → decoded source records → current immutable inventory → existing policy/projection/preparation pipeline.

Keep no process-wide tree cache. The document and fragment indexes are discarded when the request has emitted its immutable inventory. Independent/concurrent requests must not share mutable nodes.

Original bytes, source IDs and element paths are stable for unchanged input. Decoder/mapping implementation changes update the existing implementation identity and dependent digests. No new persisted schema or envelope version is required by these private types; any discovered need to alter a public shape requires a separate decision.

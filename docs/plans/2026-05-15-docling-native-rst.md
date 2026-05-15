# Docling-native RST output

**Status:** Approved (with revisions — see § Revisions)
**Date:** 2026-05-15 (revised same day)
**Driver:** Steve Allison (the fork's owner)
**Consumer:** Content Structuring Machine (`/Users/steveallison/AI_Projects+Code/Content_Structuring_Machine`)
**Estimated effort:** 1–3 days of focused work

---

## Revisions

**2026-05-15 (revision, same day as proposal):** Three decisions taken before implementation. The body below has been edited inline to reflect them.

- **Harvester anchored on the canonical `docling-core` spec, not CSM's traversal.** The original draft said the fork's harvester must mirror `DoclingSource.collect_text()` in CSM. Revised: the fork walks `DoclingDocument` using `docling-core`'s canonical iteration API. The fork no longer depends on CSM at all. If CSM's `collect_text()` order diverges from the official spec, that is CSM's problem to reconcile. The contract is the library, not a shared fixture between two repos.
- **`docling_binary_hash` dropped from the output schema.** CSM creates its own hash upstream. The fork emits its output without a binary hash. (A `harvest_hash` over the concatenated text may be added for reproducibility testing — see the build plan.)
- **Overlap rule formalised.** A relation's `nucleus_refs` (resp. `satellite_refs`) contains every `self_ref` whose harvest character range has *any* non-empty intersection with the relation's nucleus (resp. satellite) span. When a relation's span overlaps ≥ 90% with one `self_ref` but marginally touches an adjacent one, the relation carries a `note` field of the form `"nucleus dominantly in #/texts/47; spills into #/texts/48 (8% overlap)"`. Other `note` shapes are reserved for future use.

Build plan lives at [`./2026-05-15-docling-native-rst-build.md`](./2026-05-15-docling-native-rst-build.md).

---

## Why this exists

This fork's RST parser is part of the **scaffold tech** for the Content Structuring Machine (CSM). In CSM's [Kitchen-frame mission](../../../Content_Structuring_Machine/README.md#mission), CSM is the Prep Kitchen (Stations 4–5 in the 21-station kitchen). The RST parser sits in the prep kitchen as one of the deterministic tools that pre-digests sources for the curator AI's structural decisions (alongside `sentence-transformers`, `BERTopic`, and Aho-Corasick alias scanning).

The fork's job is to do one thing well: produce RST analyses that the prep kitchen can mechanically consume. CSM consumes the output; we don't change CSM here.

## The current limitation

The parser works on **plain text** and emits relations indexed by **character offsets** in that text:

```json
{
  "relation": "Elaboration",
  "nuclearity": "NS",
  "start": 0,
  "end": 7055,
  "depth": 0
}
```

CSM's source format is **Docling JSON** — every text span has a stable `self_ref` identifier (`#/texts/47`, `#/texts/48`, …). CSM citations target source spans by `self_ref`:

```text
(source: foo.docling.json, #/texts/47, quote: "verbatim claim")
```

To use this fork's RST output, CSM currently has to:

1. Run `DoclingSource.from_path(...).collect_text()` to concatenate text from a Docling source into a single string (in some defined order: body → notes → picture descriptions → table cells).
2. Run this fork's parser on that concatenated string.
3. Match RST relations' character offsets back to the original `self_ref`s — which requires re-walking the Docling JSON with a position-tracking harvester and inverting the offset arithmetic.

Step 3 is **the mapping problem**. Doing it cleanly is non-trivial and brittle — any change to the harvest order or character-counting logic breaks the mapping. The 2026-05-15 CSM Phase 3 session deferred a validator rule (`related-to-supported-by-RST`) explicitly because of this — the mapping work belonged in the fork, not in CSM.

## The proposal

Add a Docling-aware entry point to this fork that:

1. **Accepts** a path to a Docling JSON file (`*.docling.json`) directly as input.
2. **Walks** the Docling structure once, harvesting text spans with their `self_ref` IDs preserved.
3. **Runs** RST parsing against the harvested text.
4. **Emits** RST relations indexed by `self_ref`, not by character offset.

### Output shape (proposed)

```json
{
  "schema_name": "isanlp_rst_docling",
  "schema_version": "1.0",
  "tool": "isanlp_rst",
  "tool_version": "<fork commit hash>",
  "model_version": "gumrrg",
  "inventory": "eng.rst.rstdt",
  "source": "foo.docling.json",
  "relations": [
    {
      "relation": "Elaboration",
      "nuclearity": "NS",
      "nucleus_refs": ["#/texts/47"],
      "satellite_refs": ["#/texts/48", "#/texts/49"],
      "depth": 0
    },
    {
      "relation": "Cause",
      "nuclearity": "NS",
      "nucleus_refs": ["#/texts/52"],
      "satellite_refs": ["#/texts/53"],
      "depth": 1
    }
  ]
}
```

Key differences from current output:

- `nucleus_refs` / `satellite_refs` are **lists of `self_ref` strings**, not character offsets.
- A relation may span multiple `self_ref`s when the harvested text crosses span boundaries.
- The `nuclearity` field stays (NS / NN / empty).
- A new `schema_name` flag (`isanlp_rst_docling`) lets CSM detect the richer format and fall back gracefully for plain-text RST output from older runs.

### Why list-of-refs, not single-ref

The standard `isanlp_rst` parser segments by EDU (elementary discourse unit), which doesn't always align with Docling text element boundaries. One EDU might be half of one `#/texts/N` plus half of `#/texts/N+1`. The right modelling: an RST relation says "this set of `self_ref`s is the nucleus" and "this set is the satellite" — both as lists. A single-ref shortcut would lose information when EDUs cross boundaries.

## What you need to add

### 1. New entry point

A new module or function:

```python
from isanlp_rst.docling import parse_docling

result = parse_docling(
    Path("source.docling.json"),
    hf_model_name="tchewik/isanlp_rst_v3",
    hf_model_version="gumrrg",
    cuda_device=-1,
)
# result is a typed dataclass / dict matching the proposed schema above
```

### 2. Position-tracking harvester

A function that walks `DoclingDocument` once via `docling-core`'s canonical iteration API and produces a list of `(text_start, text_end, self_ref)` triples alongside the concatenated text:

```python
def harvest_docling_text(path: Path) -> tuple[str, list[tuple[int, int, str]]]:
    """Returns (full_text, [(start, end, self_ref), ...]).

    Walks DoclingDocument using docling-core's canonical iteration
    (e.g. DoclingDocument.iterate_items()). Each yielded text-carrying
    node contributes its text and self_ref to the harvest; the
    concatenation order is whatever the library defines as canonical.

    Text-carrying node types harvested in v1 (verify against the pinned
    docling-core version during Phase 0 of the build plan):
      - TextItem and its variants (paragraphs, section headers, list items)
      - PictureItem captions
      - TableItem cell text (only if part of the canonical iteration)
    """
```

The canonical order is whatever `docling-core` defines. The fork does not mirror or coordinate with CSM's `DoclingSource.collect_text()` — if CSM diverges from the spec, that is CSM's reconciliation, not the fork's.

### 3. Offset-to-ref mapper

After parsing produces RST relations with character offsets, map each relation's nucleus and satellite character ranges to sets of `self_ref`s.

**Overlap rule (v1):** a relation's `nucleus_refs` (resp. `satellite_refs`) contains every `self_ref` whose harvest range has *any* non-empty intersection with the relation's nucleus (resp. satellite) span. No threshold.

**Note field:** when a relation's span overlaps ≥ 90% with one `self_ref` but marginally touches an adjacent one, attach a `note` field describing the imbalance, for example:

```json
"note": "nucleus dominantly in #/texts/47; spills into #/texts/48 (8% overlap)"
```

The 90% threshold is the only knob; other `note` shapes are reserved for future use.

### 4. Schema versioning + version flag

Stamp the output with `"schema_name": "isanlp_rst_docling"` and `"schema_version": "1.0"` so downstream consumers can detect format and version. Bump versions for breaking changes only.

### 5. Optional — Docling-cue awareness (later phase)

The standard parser treats text as a flat stream. Docling sources have structural cues the parser can't currently use:

- **Slide-N notes vs slide-N body** are rhetorically distinct (notes elaborate on body).
- **Picture descriptions** are rhetorically connected to the picture's caption / surrounding text but isolated structurally.
- **Table cells** rarely participate in cross-cell RST; relations within a table are usually structural (row/column), not rhetorical.

A Docling-cue-aware parser could:

- Treat notes-vs-body span pairs as candidate RST relations (likely Elaboration / Background).
- Skip RST parsing inside tables (they're not prose).
- Treat picture descriptions as anchored to nearby body text via Background or Circumstance relations.

**Don't do this in v1.** Ship the basic Docling-native output first, then evaluate whether the cue-awareness adds value. Steve's CSM curator-AI auditor can already work with the basic output.

## Testing

Suggested smoke tests:

1. **Round-trip:** harvest a Docling source, run RST, verify every relation's `nucleus_refs` and `satellite_refs` are present in the source's `self_ref` set.
2. **Reproducibility:** parse the same source twice with the same model version; output must be byte-identical (modulo a `generated_at` timestamp if you choose to add one).
3. **Coverage:** for a known small source, hand-verify that the harvest order matches `DoclingSource.collect_text()` in CSM, and that no `self_ref`s are dropped.

## What CSM does in response (out of scope here; tracked in CSM)

When this work ships:

- CSM bumps `RstArtifact.schema_version` (or adds a `docling_aware: bool` field) to consume the richer format.
- CSM implements the deferred `related-to-supported-by-RST` validator rule using direct `self_ref`-to-`self_ref` lookups.
- CSM sharpens the `csm-phase1-auditor` agent prompt to reference the structured output.
- CSM optionally surfaces a minimal RST hint on retrieval cards (still scaffold-derived, tied to citations the curator authored — measurement, not judgment).

None of these CSM changes block this fork work. CSM's `methodology-rst-coverage` validator rule already handles version skew gracefully (rejects mismatched `source_hash`, accepts any conforming `RstArtifact`), so CSM can keep running against the existing plain-text output while this fork-side work is in flight.

## Out of scope

- **Upstream PR to `tchewik/isanlp_rst`.** Per this fork's CLAUDE.md, feeding work back upstream is opt-in. The Docling-native entry point is a Steve-specific concern; not necessarily generalisable. Default: keep it in the fork.
- **Anything pedagogic.** RST is descriptive linguistics. The fork measures rhetorical structure in source material. It does not judge relevance, importance, learner-difficulty, or pedagogic value. Those are Chef-side concerns in the Kitchen frame.
- **Embedding outputs.** The fork emits structural relations, not vector representations. Embeddings are a separate scaffold layer; if Steve wants them, they belong in a different tool.

## Coordination with CSM

- CSM is at `/Users/steveallison/AI_Projects+Code/Content_Structuring_Machine`. Its Mission section in `README.md` defines the Sacred Boundary that governs both projects.
- CSM consumes RST output via `tools/schemas/methodology.py:RstArtifact`. The schema is open to additive change (the model has `kind: Literal["rst"]` as discriminator and the rest as plain typed fields).
- CSM's curator-AI auditor (`Content_Structuring_Machine/.claude/agents/csm-phase1-auditor.md`) was updated 2026-05-15 to consult RST artefacts during Phase 1 audit. The richer Docling-native output, when shipped, sharpens that consultation.
- Don't add CSM-specific business logic to this fork. The fork's job ends at "Docling JSON in, RST relations indexed by `self_ref` out."
- **No harvest-order coordination.** The fork anchors on `docling-core`'s canonical iteration. CSM's `DoclingSource.collect_text()` may use the same canonical order or its own — that is CSM's concern. The fork emits `self_ref`-indexed relations; CSM looks them up directly.

---

*Next session: review this plan, scope to v1 (basic Docling-native output only), implement.*

---
name: open-output-schema-specifics
description: Output-schema underspecifications. Relation / EDU / boundary ordering, id space, tool_version format, source field format, JSON serialisation specifics. Affect byte-equality reproducibility tests.
metadata:
  type: project
---

The proposed `DoclingRstResult` schema has several underspecified details. Each must be pinned before Phase 1 because they affect byte-identical reproducibility tests.

## `relations[]` order

**Options:**

- **Pre-order DFS** (root first, then left subtree, then right subtree). Natural reading order; relation 0 is always the root.
- **Post-order DFS** (children before parents). Allows incremental tree-building consumers to construct the tree in one pass.
- **By depth, then by left-to-right** at each depth. Easier to slice by depth.

**Recommend pre-order DFS.** Predictable, matches how readers think about discourse hierarchy.

## `edus[]` order

**Recommend in left-to-right document reading order** (same order as character offsets in the harvest). Each EDU's id matches its position.

## Id space

**Options:**

- **Shared numeric space** between relations and EDUs. `relations[].id` and `edus[].id` from the same sequence; `left_id` / `right_id` resolves uniformly to either.
- **Separate spaces.** `relations[].id` and `edus[].id` are independent; `left_id` / `right_id` need a tag (`{"kind": "relation", "id": 14}`).

**Recommend shared.** Simpler resolution: walk the union of `relations` and `edus`, indexed by `id`. Cost: one numeric space; harmless.

## `tool_version` format

**Options:**

- **Bare commit SHA** (`"a937942..."`). Direct, but doesn't survive rebases / amend.
- **`git describe`** (`"v3.2.0-12-ga937942"`). Includes most recent tag and commits-since.
- **Package version** (from `importlib.metadata.version("isanlp_rst")` → `"3.2.0"`). Stable across editable installs.

**Recommend `git describe --always --dirty`.** Captures: tag + commits-since + commit SHA + `-dirty` suffix if uncommitted changes. Composed deterministically at build time; survives editable installs honestly (the `-dirty` flag is visible).

Implementation: a small helper in `_entry.py` that reads `git describe --always --dirty` once at import time. Fallback to package version if not in a git repo (e.g. PyPI install).

## `source` field format

**Options:**

- **Absolute path** (`/Users/steveallison/.../foo.docling.json`). Not portable; leaks paths.
- **Basename only** (`foo.docling.json`). Portable but loses provenance.
- **As-provided** (whatever the caller passed). Preserves caller intent but variable.

**Recommend basename only.** Provenance lives in `source_origin.filename` (the original document filename, e.g. `deck.pptx`). The Docling JSON path itself is a build artefact, not part of the document identity.

## JSON serialisation specifics

For byte-identical reproducibility:

- **Indent:** `indent=2` for human-readable storage; `indent=None` (compact) for production. Make this a knob on the serialiser.
- **Key ordering:** alphabetical within each object (`sort_keys=True`). Stable across runs regardless of dataclass field order.
- **Encoding:** UTF-8, no BOM.
- **Line endings:** LF.
- **Trailing newline:** yes (POSIX convention).
- **Float representation:** Python's `repr()` for floats. Avoid scientific notation surprises (`note_threshold: 0.9` not `0.9e0`).

## Empty / minimal cases

| Input | Output |
|---|---|
| Empty Docling JSON (no body, no texts) | Raise `EmptyDoclingError` (a custom typed exception). Refuse to fabricate empty RST output. |
| Document with only `TableItem`s (no prose) | Raise `EmptyHarvestError`. Tables aren't in the RST input by design. |
| Document with one TextItem (one EDU after parser) | Valid output: one `RstEdu` with id 0; zero relations; one boundary covering the whole document. |
| Document with two TextItems (one EDU each, parser produces one relation) | Valid: two edus + one relation. |

## How to apply

Pin each of these before Phase 1 (Phase 3 orchestrator + serialiser depends on them). Add to the build plan's Phase 1 deliverables (schema.py + serialiser tests).

Related: [[decision-one-tree-per-document]], [[open-boundary-design-decisions]].

---
name: decision-use-docling-core
description: Anchor the Docling-native harvester on docling-core.DoclingDocument.iterate_items rather than hand-rolling a JSON walker. Adds docling-core as a hard runtime dependency.
metadata:
  type: feedback
---

For the Docling-native RST entry point, the harvester uses `docling-core`'s `DoclingDocument.load_from_json(...)` + `iterate_items(...)` rather than walking the JSON as a plain dict. `docling-core` becomes a hard runtime dependency (`pyproject.toml` and `pixi.toml`).

**Why:**

- The walker is verified to exist, be canonical, and resolve `$ref`s correctly (see [[verified-docling-core-api]]).
- Pydantic-validated loader catches malformed Docling JSON at the boundary.
- Default content-layer filter (`{ContentLayer.BODY}`) gives us furniture exclusion for free.
- `page_no` filtering is built-in if we want per-page parsing later.
- Schema-version tracking is inherited — when Docling bumps its schema (it's currently v1.10.0), the `docling-core` pin tells us by failing to validate.
- Hand-walking the dict reinvents `$ref` resolution, content-layer filtering, page filtering, and forces us to track schema versions independently. All of that goes stale when Docling moves.

**How to apply:**

- Don't roll a custom JSON walker even when "it's just a small dict traversal." The cost of `docling-core` is small (pure Python + Pydantic); the benefit is the official contract.
- Pin `docling-core` to the latest stable; record the pin in [`docs/plans/2026-05-15-docling-native-rst-build.md`](../../docs/plans/2026-05-15-docling-native-rst-build.md) under Phase 0 verification log.
- When `docling-core` bumps to a major version, treat it as a Docling schema-compatibility checkpoint. Don't auto-bump.

Related: [[verified-docling-core-api]], [[decision-consumer-agnostic]].

---
name: decision-use-docling-core
description: Anchor the Docling-native harvester on docling-core.DoclingDocument.iterate_items rather than hand-rolling a JSON walker. docling-core is an optional 'formats' extra, not a core dependency.
metadata:
  type: feedback
---

For the Docling-native RST entry point, the harvester uses `docling-core`'s `DoclingDocument.load_from_json(...)` + `iterate_items(...)` rather than walking the JSON as a plain dict. `docling-core` is an **optional** dependency — the `formats` extra (`pip install isanlp_rst[formats]`), present in the pixi dev/test env but NOT a core requirement (2026-06-30). Consumers that only use the RST `Parser` as a library (e.g. Story_Analyser) install without it and avoid the docling-core dependency chain (incl. the transitive `typer` constraint that conflicted with conda).

**Why:**

- The walker is verified to exist, be canonical, and resolve `$ref`s correctly (see [[verified-docling-core-api]]).
- Pydantic-validated loader catches malformed Docling JSON at the boundary.
- Default content-layer filter (`{ContentLayer.BODY}`) gives us furniture exclusion for free.
- `page_no` filtering is built-in if we want per-page parsing later.
- Schema-version tracking is inherited — when Docling bumps its schema (it's currently v1.10.0), the `docling-core` pin tells us by failing to validate.
- Hand-walking the dict reinvents `$ref` resolution, content-layer filtering, page filtering, and forces us to track schema versions independently. All of that goes stale when Docling moves.

**How to apply:**

- Don't roll a custom JSON walker even when "it's just a small dict traversal." The cost of `docling-core` is small (pure Python + Pydantic); the benefit is the official contract.
- Keep `docling-core` **unpinned** — declare a floor only (`>=2.75.0`, the minimum API the harvester needs) and let it track latest, including majors. Per the 2026-06-27 policy (commit `5b7288d`), docling/doclang always run latest, not pinned; the test suite + CI are the breakage safety net, not a version ceiling. (`doclang` rides in transitively via docling-core's own `doclang>=0.7,<0.8` requirement.)
- A docling-core **major** bump is still worth watching as a Docling schema-compatibility checkpoint, but it is no longer blocked — if it breaks the harvester, the docling tests fail and we fix forward rather than holding an old version.

Related: [[verified-docling-core-api]], [[decision-consumer-agnostic]].

---
name: feedback-no-assumptions-hard-rule
description: HARD RULE breach on 2026-05-15. Inferred PictureItem.meta.description was a "Docling-Machine extension" from naming clues without reading PictureMeta. Hook now enforces. Steve does not tolerate this behaviour.
metadata:
  type: feedback
---

**Rule (project HARD RULE):** Any claim of the form "X is custom", "X is an extension", "X is non-canonical", "X is the canonical Y", "X isn't in the schema", "producer-specific", "Docling-Machine extension", or any equivalent claim about whether a field / path / API is standard requires a schema check BEFORE writing. Verify by reading the relevant Pydantic model class, primary docstring, or code at path:line. Cite the verification inline in the same edit.

**Why:** Verified 2026-05-15 by failing the rule. I claimed `PictureItem.meta.description` was a "Docling-Machine extension" and that `annotations[]` was "the canonical Docling place" for picture descriptions. Both wrong. The mechanism:

- Saw `created_by: "pptx_enrichment_gemini:gemini-2.5-pro"` and inferred "custom".
- Saw a sibling key `docling_machine__vlm_metadata` (which genuinely IS a Docling-Machine prefix-namespaced extra) and stretched the inference to the whole `meta.description` block.
- Did not open docling-core's `PictureMeta` model definition, despite having the source available in the session via raw GitHub fetch.

Reality (Verified 2026-05-15 by inspecting `type(picture.meta).__name__` at runtime via the pixi env):

- `picture.meta` is a typed `PictureMeta` declared field on `PictureItem`.
- `picture.meta.description` is a typed `DescriptionMetaField` with `.text`, `.created_by`, `.confidence`.
- `picture.annotations` is **deprecated in favour of `meta`** per the runtime DeprecationWarning emitted by docling-core 2.75+.
- So `meta.description` is the canonical Docling location, not a custom extension.

This is anti-pattern #2 from `.claude/rules/no-assumptions.md` (pattern-matched conclusion as verified fact). I read that rule today. I broke it anyway. Steve's response: "I spend MORE TIME fighting you than I do getting work actually done." The hook at `.claude/hooks/no-assumptions-check.sh` was wired in response.

**How to apply:**

- Before writing the kind of claim listed above, run a schema check: `pixi run -- python -c "from <module> import <Model>; print(<Model>.model_fields)"`, or grep the model class in the dependency's source, or read the primary docstring. Capture the output and cite it inline (`Verified <date> at <path>:<line>` or paste of `model_fields`).
- If verification truly isn't possible in the moment, mark the claim explicitly: `ASSUMED (<date>, to verify): <claim>. Verification needed: <path>.` Never write the claim as bare fact.
- The hook at `.claude/hooks/no-assumptions-check.sh` blocks Write / Edit / MultiEdit when the proposed content contains these triggers without a nearby evidence anchor or `ASSUMED` marker. Do not work around the hook by rephrasing. The rephrase is the symptom; the unverified claim is the disease.
- This applies to plans, memory files, rule files, READMEs, docstrings, comments, and inline prose in chat replies. Every surface.

Related: [[no-assumptions-rule]] (the four anti-patterns catalogued in full).

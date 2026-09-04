# Projection foundation verification

Verified 2026-09-04, before the user-story integration work (T029).

- `pixi run --locked test-all`: **1588 passed, 56 skipped in 314.47s**.
- `pixi run --locked smoke`: **41 passed, 54 skipped in 42.48s**.
- `HF_HUB_OFFLINE=1 pixi run --locked rst-baseline compare --baseline specs/017-universal-source-pipeline/evidence/baseline-dmrst-current --store /Users/steveallison/.cache/isanlp_rst/model-releases --release-id gumrrg-eb1d5745f3a1 --device cpu`: **analytical_differences: {}, analytically_equivalent: true**.
- Baseline non-analytical classifications: 32 approved contract-field renames,
  34 derived digests, 40 execution differences. Historical baseline files unchanged.
- Real CPU RST provider projection regression: **1 passed in 14.07s**.
- Projection equivalence covers text, EDUs, Markdown, Docling JSON, DocLang XML,
  and DocLang archive with the unchanged RST policy.
- Lint: **All checks passed!** Typecheck: **0 errors, 0 warnings, 0 informations**.
- Production boundary: **146 modules, valid: true, violations: []**.

The first full run exposed an eager-import regression. Both canonical ingest export
catalogues now resolve lazily, preserving typed exports without loading a technique
implementation during `import rdam`. The focused import test and the full rerun pass.

This verifies the foundation only, not completion of Feature 017. Skipped tests are
not evidence that their runtime paths passed.

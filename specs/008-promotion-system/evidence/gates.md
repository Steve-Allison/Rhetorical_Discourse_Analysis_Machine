# Feature 008 — gate results (2026-09-02)

| Gate | Command | Result |
|---|---|---|
| Promotion contract and workflow tests | `pixi run pytest tests/machine tests/offline/test_model_promotion.py -q` | **56 passed** |
| Fast suite | `pixi run test` | **890 passed**, 77 deselected |
| Ruff | `pixi run lint` | All checks passed |
| Pyright, strict | `pixi run typecheck` | 0 errors |
| Retroactive decisions | scratch script over committed evidence (values cited in each record) | 3 recorded in `workbench/promotions/rst/`; sidecars published beside `a52b70fbc1a3` and `462d68b82eae` in `models/model-releases/`, and beside `e5ea56cd620f` in `~/.cache/isanlp_rst/model-releases/` |
| Boundary inspection | `pixi run -e default production-boundary` | see commit |
| Markdown | `pixi run mdlint` | see commit |

Verdict output, verbatim from the recording run:

```text
recorded withhold modernbert-v1-a52b70fbc1a3
    output_quality     candidate does not exceed any baseline; no uncertainty or statistical comparison
    calibration        calibration neither measured nor declared absent
    latency_resources  latency and resources not measured
    compatibility      admissible
    provenance         admissible
    licensing          licence ... does not permit 'local, single-person discourse analysis on this machine'
recorded withhold modernbert-v1-462d68b82eae
    output_quality     output quality unmeasured: ... no training receipt and no evaluation evidence supplied ...
    compatibility      runtime and packaging compatibility not verified
recorded retire   modernbert-v1-e5ea56cd620f
    output_quality     output quality unmeasured: ... the literal 'GUM-12.1.0 Parseval evaluation verified' ...
```

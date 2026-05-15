# CLAUDE.md

`isanlp_rst` — Steve Allison's RST (Rhetorical Structure Theory) parser. Predicts discourse trees across 11 languages via the `unirst` multilingual model plus three monolingual / bilingual models (`rstdt`, `gumrrg`, `rstreebank`). Pixi-managed, MPS-aware, Apple-Silicon-first, real test suite, real CI.

## Provenance & licence

The original RST research code and the trained model weights are by Elena Chistova (`tchewik/isanlp_rst`). The MIT-licensed source carries her copyright (see [`LICENSE`](LICENSE)). Model weights are **CC BY-NC 4.0 — research and non-commercial use only** (see [`LICENSE_MODELS`](LICENSE_MODELS)). This repository is Steve's evolution of that code: own design direction, own infrastructure (pixi, tests, CI, MPS), own roadmap. Not a tracking fork.

Commercial use requires either retraining new weights under a permissive licence or replacing the models entirely.

## Git remotes

Single remote: `origin` → `Steve-Allison/isanlp_rst`. No upstream tracking. All pushes go to `origin`. Verify: `git remote -v`.

## Pixi commands

```bash
pixi install       # provision env from pixi.lock
pixi run test      # fast unit tests only
pixi run test-all  # include integration tests (downloads HF models, slow)
pixi run lint      # ruff check
pixi run typecheck # pyright (strict on our code, lenient on inherited research)
pixi run smoke     # quick parser smoke test
pixi run smoke-mps # smoke test on MPS
pixi run bench     # performance bench across models / dtypes
pixi run cuda-smoke # verify on NVIDIA hardware
pixi run mdlint    # markdownlint
```

Adding dependencies: `pixi add <package>`. Never `pip install`.

## Project-specific overrides of global rules

- **No fork-only-push rule.** This repo is not a fork in spirit; `origin` is the only valid push target by virtue of remote configuration. The earlier "fork-only push" rule has been retired.
- **No vendored-dependency mentality.** This is Steve's code. Refactor when it pays off; don't defer to "what would upstream accept".
- **Code-style mode mixed.** New modules use modern Python 3.13+ idioms (see [`code-standards.md`](.claude/rules/code-standards.md)); the inherited research modules under `*/src/parser/`, `*/src/corpus/`, `multiple_runs.py`, `data_manager.py`, `du_converter.py`, and `rstviewer/` are touched surgically — bug fixes are in scope, aesthetic sweeps are not.
- **No assumptions.** Factual claims about data / schema / code / runtime are either verified (with cited evidence) or explicitly marked `ASSUMED`. No silent inference, no sample-to-universal escalation, no eyeballing summary stats and concluding semantics. See [`no-assumptions.md`](.claude/rules/no-assumptions.md). **This is a project HARD RULE.**

## Detail in `.claude/rules/`

| File | Loads when |
|---|---|
| [`no-assumptions.md`](.claude/rules/no-assumptions.md) | Always. **HARD RULE.** Forbids stating assumptions as fact; requires evidence-cited claims or explicit `ASSUMED` marking. |
| [`architecture.md`](.claude/rules/architecture.md) | Always. Parser families, inference flow, visualisation, memory management. |
| [`code-standards.md`](.claude/rules/code-standards.md) | Always. Modern-Python rules for new code; surgical rules for inherited modules; testing and gotchas. |
| [`commands.md`](.claude/rules/commands.md) | Always. Full pixi command reference + when to use each. |

## Active roadmap

In flight: [Docling-native RST output](docs/plans/2026-05-15-docling-native-rst.md). New entry point `isanlp_rst.docling.parse_docling(path)` that takes a Docling JSON file and emits RST relations indexed by `self_ref`. Build plan: [`docs/plans/2026-05-15-docling-native-rst-build.md`](docs/plans/2026-05-15-docling-native-rst-build.md). Project memory at [`.claude/memory/MEMORY.md`](.claude/memory/MEMORY.md) tracks verified facts and open design questions.

## Files worth knowing

- [`isanlp_rst/parser.py`](isanlp_rst/parser.py) — public entry point, dispatches to predictor families.
- [`isanlp_rst/base_predictor.py`](isanlp_rst/base_predictor.py) — shared tokenisation, batching, offset remapping, MPS-safe init.
- [`isanlp_rst/dmrst_parser/predictor.py`](isanlp_rst/dmrst_parser/predictor.py) — DMRST inference path.
- [`isanlp_rst/universal_parser/predictor.py`](isanlp_rst/universal_parser/predictor.py) — UniRST inference path.
- [`isanlp_rst/__init__.py`](isanlp_rst/__init__.py) — viewer convenience helpers (`render`, `to_html`, `to_png`, `to_pdf`).
- [`tests/test_integration.py`](tests/test_integration.py) — end-to-end model parses; dtype-equivalence suite.
- [`docs/plans/`](docs/plans/) — design plans (proposals + build plans).
- [`UniRST_Metrics.md`](UniRST_Metrics.md) — per-corpus metrics for the multilingual model.

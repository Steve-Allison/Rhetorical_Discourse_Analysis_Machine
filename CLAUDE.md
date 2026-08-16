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
pixi run rst-diag  # RST quality diagnostics over a corpus (proxy metrics, no gold)
pixi run mdlint    # markdownlint
```

Adding dependencies: `pixi add <package>`. Never `pip install`.

CI (`.github/workflows/ci.yml`) runs on macOS arm64 with the pixi lock (**Python 3.12**). `requires-python` is `>=3.10` for downstream installs; the project's tested path is 3.12. PRs also run a short CPU smoke (`--quick`: gumrrg + unirst) with an HF hub cache, plus `mdlint`.

## Project-specific overrides of global rules

- **No fork-only-push rule.** This repo is not a fork in spirit; `origin` is the only valid push target by virtue of remote configuration. The earlier "fork-only push" rule has been retired.
- **No vendored-dependency mentality.** This is Steve's code. Refactor when it pays off; don't defer to "what would upstream accept".
- **One quality bar.** Every module is Steve's production Python — modern, world-class, always. Provenance is not a style freeze. See [`AGENTS.md`](AGENTS.md). **HARD RULE.**
- **No assumptions.** Factual claims about data / schema / code / runtime are either verified (with cited evidence) or explicitly marked `ASSUMED`. No silent inference, no sample-to-universal escalation, no eyeballing summary stats and concluding semantics. See [`no-assumptions.md`](.claude/rules/no-assumptions.md). **This is a project HARD RULE.**
- **Docling / DocLang spec currency.** Before format-native work, verify we match current upstream specs — lockfile and fixtures are last-shipped, not the spec. See [`AGENTS.md`](AGENTS.md). **HARD RULE.**

## Detail in `.claude/rules/`

| File | Loads when |
|---|---|
| [`no-assumptions.md`](.claude/rules/no-assumptions.md) | Always. **HARD RULE.** Forbids stating assumptions as fact; requires evidence-cited claims or explicit `ASSUMED` marking. |
| [`architecture.md`](.claude/rules/architecture.md) | Always. Parser families, inference flow, visualisation, memory management. |
| [`code-standards.md`](.claude/rules/code-standards.md) | Always. Modern Python everywhere (one bar). Testing and gotchas. |
| [`commands.md`](.claude/rules/commands.md) | Always. Full pixi command reference + when to use each. |
| [`AGENTS.md`](AGENTS.md) | Always. **HARD RULES.** One quality bar (Steve's code, modern Python). Docling / DocLang spec currency. |

## Active roadmap

**Shipped:** three first-class format-native entry points sit alongside the raw `Parser` API:

- `isanlp_rst.docling.parse_docling(path)` — Docling JSON in → RST relations indexed by `self_ref`. Plans: [proposal](docs/plans/2026-05-15-docling-native-rst.md), [build](docs/plans/2026-05-15-docling-native-rst-build.md). Walkthrough: [`docs/examples/docling-native.md`](docs/examples/docling-native.md).
- `isanlp_rst.doclang.parse_doclang(path)` — DocLang XML (namespace `https://www.doclang.ai/ns/v0`) in → RST relations indexed by local-name XPath, with `<thread>` aggregation. Plan: [`docs/plans/2026-05-15-doclang-native-rst.md`](docs/plans/2026-05-15-doclang-native-rst.md). Walkthrough: [`docs/examples/doclang-native.md`](docs/examples/doclang-native.md).
- `isanlp_rst.markdown.parse_markdown(path)` — CommonMark / GFM markdown in → RST relations indexed by `#/blocks/N`. Plan: [`docs/plans/2026-06-12-markdown-native-rst.md`](docs/plans/2026-06-12-markdown-native-rst.md). Walkthrough: [`docs/examples/markdown-native.md`](docs/examples/markdown-native.md).

These three entry points require the optional **`formats` extra** (`docling-core`, `markdown-it-py`, `mdit-py-plugins`; `doclang` rides in transitively) — `pip install isanlp_rst[formats]`. The core `Parser` does **not** import them, so library consumers that only need RST parsing install without the extra and avoid the docling-core dependency chain. `pixi install` includes `formats`. Do not move these back into `[project.dependencies]`.

All three honour the cross-format "analyse everything" directive **two-level** (2026-06-12, Option 2): prose enters the document tree; each table gets its own RST mini-parse in `result.table_analyses`, so table discourse never distorts the document tree. All three expose `dtype=`, `device="auto"` (CPU fallback), and an optional `cache_dir=` on-disk result cache.

Shared machinery lives in `isanlp_rst/_rst_common/`: `SpanIndex` (bisect overlap), iterative `flatten_tree` (no RecursionError on degenerate joint-chains), `resolve_tool_version` / `resolve_inventory`, and the result-cache helpers. Format mappers and `_entry` modules are thin bindings over it. (Device resolution moved to `resolve_device` in [`base_predictor.py`](isanlp_rst/base_predictor.py) — `_rst_common` no longer carries a device helper.)

Quality measurement: `pixi run rst-diag <paths>` ([`scripts/rst_diag.py`](scripts/rst_diag.py)) — per-document proxy metrics (joint ratio, tree skew, cross-boundary ratio, note ratio) across all three formats. Use it to A/B any harvest-policy change. Hierarchical long-input parsing remains a spike gated on rst-diag evidence of degradation at length.

Project memory at [`.claude/memory/MEMORY.md`](.claude/memory/MEMORY.md) tracks verified facts (spec citations, fixture evidence) and open design questions.

## Files worth knowing

- [`isanlp_rst/parser.py`](isanlp_rst/parser.py) — public entry point, dispatches to predictor families.
- [`isanlp_rst/base_predictor.py`](isanlp_rst/base_predictor.py) — shared tokenisation, batching, offset remapping, MPS-safe init.
- [`isanlp_rst/dmrst_parser/predictor.py`](isanlp_rst/dmrst_parser/predictor.py) — DMRST inference path.
- [`isanlp_rst/universal_parser/predictor.py`](isanlp_rst/universal_parser/predictor.py) — UniRST inference path.
- [`isanlp_rst/__init__.py`](isanlp_rst/__init__.py) — viewer convenience helpers (`render`, `to_html`, `to_png`, `to_pdf`).
- [`isanlp_rst/docling/`](isanlp_rst/docling/) — `parse_docling` entry point; `harvester`, `boundaries`, `mapper` flow.
- [`isanlp_rst/doclang/`](isanlp_rst/doclang/) — `parse_doclang` entry point; `loader` (XPath generator), `harvester`, `boundaries`, `mapper` flow.
- [`isanlp_rst/markdown/`](isanlp_rst/markdown/) — `parse_markdown` entry point; `loader` (markdown-it-py + front-matter), `harvester`, `boundaries`, `mapper` flow.
- [`isanlp_rst/_rst_common/`](isanlp_rst/_rst_common/) — shared overlap-rule maths + nuclearity split, format-agnostic.
- [`isanlp_rst/utils/serialization.py`](isanlp_rst/utils/serialization.py) — `tree_to_dict` / `tree_from_dict`: a `DiscourseUnit` tree ↔ nested JSON dict (core, zero-dep). For a validated typed model (`RstNode`), [`serialization_pydantic.py`](isanlp_rst/utils/serialization_pydantic.py) — requires the `pydantic` extra (`pip install isanlp_rst[pydantic]`), kept off the core import path so dependency-light consumers don't inherit pydantic.
- [`tests/test_integration.py`](tests/test_integration.py) — end-to-end model parses; dtype-equivalence suite.
- [`docs/plans/`](docs/plans/) — design plans (proposals + build plans).
- [`UniRST_Metrics.md`](UniRST_Metrics.md) — per-corpus metrics for the multilingual model.

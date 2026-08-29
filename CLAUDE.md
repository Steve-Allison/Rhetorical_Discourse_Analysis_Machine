# CLAUDE.md

`isanlp_rst` — Steve Allison's RST (Rhetorical Structure Theory) parser. Predicts discourse trees across 11 languages via the `unirst` multilingual model plus three monolingual / bilingual models (`rstdt`, `gumrrg`, `rstreebank`). Pixi-managed, MPS-aware, Apple-Silicon-first, real test suite, real CI.

## Provenance & licence

The original RST research code and the trained model weights are by Elena Chistova (`tchewik/isanlp_rst`). The MIT-licensed source carries her copyright (see [`LICENSE`](LICENSE)). Model weights are **CC BY-NC 4.0 — research and non-commercial use only** (see [`LICENSE_MODELS`](LICENSE_MODELS)). This repository is Steve's evolution of that code: own design direction, own infrastructure (pixi, tests, CI, MPS), own roadmap. Not a tracking fork.

Commercial use requires either retraining new weights under a permissive licence or replacing the models entirely.

## Git remotes

Single remote: `origin` → `Steve-Allison/isanlp_rst`. No upstream tracking. All pushes go to `origin`. Verify: `git remote -v`.

## Pixi commands

The repository uses two environments:

- **`default` (mapped to `offline`)**: Active by default. Contains all dependencies (`dev`, `formats`, `offline`) for friction-free everyday development.
- **`production`**: Isolated clean-room environment simulating a pip consumer install.

```bash
pixi install                            # provision default environment
pixi run test                           # fast unit tests (excludes slow/stress)
pixi run test-deep                      # full integration test battery
pixi run test-stress                    # multithreaded and megadoc stress tests
pixi run lint                           # ruff check
pixi run typecheck                      # pyright (Strict Mode A)
pixi run bench                          # benchmark harness across models/dtypes
pixi run mdlint                         # markdownlint over tracked files manifest
pixi run cleanup                        # remove bytecode, tool caches, dist (or ./cleanup.sh)
pixi run -e production production-smoke # verify clean-room production wheel
pixi run build-production               # build reproducible wheel and sdist
```

Adding dependencies: `pixi add <package>`. Never `pip install`.

CI (`.github/workflows/ci.yml`) runs on macOS arm64 with the pixi lock (**Python 3.14**). `requires-python` is `>=3.14`. PRs also run a short CPU smoke (`--quick`: gumrrg + unirst) with an HF hub cache, plus `mdlint`.

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

Production source ingest has one public surface: `isanlp_rst.ingest`. `ProductionIngestor.prepare()` and `.analyse()`, plus the convenience `analyse_source()`, accept five real-world source forms: plain text, Markdown, Docling JSON, DocLang XML, and DocLang archives. The old format-specific parsing functions and result envelopes were removed rather than deprecated; no compatibility route remains.

The optional **`formats` extra** supplies `docling-core`, `doclang`, `markdown-it-py`, and `mdit-py-plugins`: `pip install isanlp_rst[formats]`. Core parser consumers avoid that dependency chain. `pixi install` includes `formats`; keep these dependencies outside `[project.dependencies]`.

Canonical ingest inventories source content before applying the explicit `AUTHORED_PROSE_V1` relevance policy. Authored prose reaches the RST parser; tables, code, machine descriptions, furniture, and other non-prose remain traceable side channels unless a future named policy explicitly changes their role. Every decision is represented in the preparation receipt, source anchors survive into the analysis, long or structured material uses the governed subdivision/stitching path, and persistent cache identity includes the complete analytical pipeline fingerprint.

Format code beneath `isanlp_rst.doclang` and `isanlp_rst.markdown` is private decoding support for the canonical service. Docling JSON is loaded directly with current `docling-core`. There is no independent format mapper, result schema, cache, or public entry point.

Quality measurement: `pixi run rst-diag <paths>` ([`scripts/rst_diag.py`](scripts/rst_diag.py)) — preparation coverage, content-class decisions, anchor integrity, tree structure, relation distribution, subdivision, and timing across the canonical source forms.

Project memory at [`.claude/memory/MEMORY.md`](.claude/memory/MEMORY.md) tracks verified facts (spec citations, fixture evidence) and open design questions.

## Files worth knowing

- [`isanlp_rst/parser.py`](isanlp_rst/parser.py) — public entry point, dispatches to predictor families.
- [`isanlp_rst/cli.py`](isanlp_rst/cli.py) — unified `isanlp-rst` CLI (parse, view, serve, version).
- [`isanlp_rst/transformer_parser/`](isanlp_rst/transformer_parser/) — SOTA ModernBERT pure-transformer parsing net, biaffine scorer, and CKY chart decoder.
- [`isanlp_rst/annotation_rst.py`](isanlp_rst/annotation_rst.py) — native `DiscourseUnit` and RS3 XML serialization.
- [`isanlp_rst/ingest/`](isanlp_rst/ingest/) — sole production source inventory, preparation, analysis, receipt, subdivision, and cache API.
- [`isanlp_rst/contracts/`](isanlp_rst/contracts/) — typed contracts: `RstAnalysis`, `RstDocument`, `SecondaryRelationEdge`, `DiscourseSignal`, envelope serializations.
- [`isanlp_rst/erst/`](isanlp_rst/erst/) — Extended RST (eRST): RS4 reader/writer, typed signals, complete candidates, and formally constrained `ErstSecondaryEdgeDecoder`.
- [`isanlp_rst/hierarchical/stitcher.py`](isanlp_rst/hierarchical/stitcher.py) — `MacroMicroStitcher`: two-stage hierarchical section/macro tree stitching.
- [`isanlp_rst/rstviewer/`](isanlp_rst/rstviewer/) — visualizer and HTML/PNG export engine.
- [`isanlp_rst/doclang/`](isanlp_rst/doclang/) — private DocLang XML/archive decoding helpers used by canonical ingest.
- [`isanlp_rst/markdown/`](isanlp_rst/markdown/) — private Markdown decoding helper used by canonical ingest.
- [`workbench/`](workbench/) — offline workbench: corpus ingestion, training recipes, Parseval evaluation, and central audit ledger (`workbench/experiments/central_ledger.jsonl`).
- [`docs/metrics/UniRST_Metrics.md`](docs/metrics/UniRST_Metrics.md) — per-corpus metrics for the multilingual model.

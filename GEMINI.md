# GEMINI.md — Rhetorical Discourse Analysis Machine (`rdam`)

## 🔗 Inheritance

- Inherits from: `/Users/steveallison/.gemini/gemini.md`

## 🎯 World-Class Quality Mandate

- **NO ASSUMPTIONS**: Verify all paths, names, and states before acting.
- **PRODUCTION-READY CODE**: No stubs, no placeholders, complete implementations only.
- **INTEGRITY PROTOCOL**: Maintain system and architectural integrity at all times.
- **VERIFICATION IS FINALITY**: Nothing is complete until verified by tests or shell commands.

## 🛠 Tech Stack

- **Language & Runtime**: Python 3.14 (Mode A, PEP 649 deferred annotations).
- **Environment Management**: Pixi (`pyproject.toml` / `pixi.lock`), Conda-Forge + PyPI packages.
- **Deep Learning Framework**: PyTorch (installed version from `pixi.lock`) (Apple Silicon MPS + NVIDIA CUDA + CPU autodispatch), Hugging Face `transformers` with verified fast tokenizers, `tiktoken`.
- **Analytical techniques**: RST, PDTB, SDRT, Toulmin, Walton, Dung and IBIS retain native outputs. Dung and IBIS require supplied structures. eRST is workbench-only.
- **Parser and source representations**: Classical RST trees (`DiscourseUnit`), passive saved Extended RST graphs (execution is workbench-only) (`RstAnalysis`, `SecondaryRelationEdge`, `DiscourseSignal`), RS3 / RS4 XML, DocLang 0.7 XML, Docling Document ASTs, GFM Markdown.
- **NLP & Parsing Tools**: `razdel`, `lxml` (`Saxon-HE` Schematron validation), `networkx`.
- **Package boundary**: `rdam` is production; `workbench` owns research and offline dependencies such as `nltk`. Current usage: [README.md](README.md); project briefing: [CLAUDE.md](CLAUDE.md).
- **Testing & Quality Assurance**: `pytest >= 9`, `pyright >= 1.1.380` (strict Mode A type checking), `ruff >= 0.6` (linting & formatting), `markdownlint-cli2`.

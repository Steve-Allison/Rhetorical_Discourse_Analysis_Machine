# GEMINI.md - isanlp_rst

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
- **Deep Learning Framework**: PyTorch 2.13.x (Apple Silicon MPS + NVIDIA CUDA + CPU autodispatch), Hugging Face `transformers` with verified fast tokenizers, `tiktoken`.
- **Parsing Formalisms**: Classical RST trees (`DiscourseUnit`), Extended RST DAGs (`RstAnalysis`, `SecondaryRelationEdge`, `DiscourseSignal`), RS3 / RS4 XML, DocLang 0.7 XML, Docling Document ASTs, GFM Markdown.
- **NLP & Parsing Tools**: `isanlp`, `nltk`, `razdel`, `lxml` (`Saxon-HE` Schematron validation), `networkx`.
- **Testing & Quality Assurance**: `pytest >= 9`, `pyright >= 1.1.380` (strict Mode A type checking), `ruff >= 0.6` (linting & formatting), `markdownlint-cli2`.

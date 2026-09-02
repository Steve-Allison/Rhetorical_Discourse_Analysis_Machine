# Agent instructions

Full project briefing: [`CLAUDE.md`](CLAUDE.md). Hard rules in [`.claude/rules/`](.claude/rules/).

## HARD RULE — this is Steve's code

Treat **every** module in this repo as Steve Allison's production Python. Elena Chistova / `tchewik` provenance is licence and history, not a quality waiver.

- One bar: modern, world-class Python 3.14 (Mode A in [`.claude/rules/code-standards.md`](.claude/rules/code-standards.md)). Apply it **always**, including `*/src/parser/`, `*/src/corpus/`, `rstviewer/`, `data_manager.py`, `du_converter.py`, and anything else that started as research code. Do not add `from __future__ import annotations` (PEP 563 stringification; 3.14 deferred evaluation is the default).
- Always fix quality issues you encounter: warnings, no-op constructor args, footguns, outdated idioms, missing types on code you touch. Do not leave them because the file is “inherited” or “not the task.”
- Never refuse a fix on “upstream wouldn't accept it” or “surgical touch only.” Those rules are retired.
- Do not change trained architecture or inference maths in the name of style. Constructor no-ops and dead warnings are in scope; swapping a 1-layer LSTM for a 2-layer one is not.

## HARD RULE — Pixi environment topology

The repository defines two Pixi environments:

- **`default` (mapped to `offline` feature)**: The primary development environment containing all dependencies (`dev`, `formats`, `offline`). All everyday tasks (`pixi run test`, `pixi run lint`, `pixi run typecheck`, `pixi run bench`, `pixi shell`) execute here by default without `-e` flags.
- **`production`**: The isolated clean-room consumer environment containing only what `pip install isanlp_rst` provides (installed as the editable source). Release certification is `pixi run build-production`, `pixi run validate-production-artifacts`, and `pixi run -e production production-clean-install`; `production-import-check` only imports the editable source and certifies no wheel.

Do not break this boundary: production code (`isanlp_rst/`) must never import offline/dev packages (`pytest`, `nltk`, `peft`, `fire`, `jsonnet`, `blake3`).

## HARD RULE — no invented release theatre

When asked to release or publish an API, deliver the requested distributable
artefacts and the requested publication action directly. It is forbidden to
invent, require, or preserve receipt files, evidence lifecycles, promotion
gates, second-machine ceremonies, downstream-specific contracts, or other
process machinery unless the user has explicitly asked for that mechanism or it
is technically necessary for the stated release.

External publication is forbidden unless the user explicitly names the exact
destination in that request. In particular, never upload this project or its
artefacts to PyPI, package indexes, registries, release services, or any other
external destination by inference from the word “release”. A repository tag and
tracked artefacts are a complete release when that is what the user requested.

Verification must establish the requested fact, then stop. Do not turn a
straightforward build, install, commit, tag, or push into a new release system.
Do not delay a release because of a process requirement the project does not
already require. If an existing mechanism blocks the requested delivery without
serving it, remove that mechanism rather than asking the user to satisfy it.

## HARD RULE — Docling / DocLang spec currency

Before changing `parse_docling`, `parse_doclang`, format harvest / boundaries / mappers, fixtures, or docs that describe those contracts, **verify we are compliant with the current Docling and DocLang specs**. Do this even when the task looks unrelated to a version bump.

The pixi lock, in-repo fixtures, and [`.claude/memory/`](.claude/memory/) notes are **what we last shipped**, not what upstream is today. Stating a lock version as “the spec” is a no-assumptions violation.

### What to check (cite evidence)

1. **Docling** — [`docling-core`](https://pypi.org/project/docling-core/) PyPI latest vs `pyproject.toml` pin vs `pixi.lock`; fixture `DoclingDocument` `version` vs what current `load_from_json` accepts; `iterate_items` / `ContentLayer` against current `docling-core` source (not memory from 2026-05-15). Spec / schema live with [docling-project/docling](https://github.com/docling-project/docling) and [docling-project/docling-core](https://github.com/docling-project/docling-core).
2. **DocLang** — [`doclang`](https://pypi.org/project/doclang/) PyPI latest vs pin vs lock; current [`spec.md`](https://github.com/doclang-project/doclang/blob/main/spec.md) (element head, layers, new elements); upstream [`tests/data/valid`](https://github.com/doclang-project/doclang/tree/main/tests/data/valid) vs `tests/fixtures/doclang/` (count, names, extension — upstream uses `.dclg`); whether `validate()` still needs extras such as `doclang[schematron-saxon]`.
3. **Our envelopes** — `isanlp_rst_docling` / `isanlp_rst_doclang` `schema_version` bump only when *our* result shape changes. Do not conflate that with upstream package versions.

If lock, fixtures, or harvest behaviour lag the current spec, update them in the same work (or flag the gap explicitly). Do not document a stale contract as current.

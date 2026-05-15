# Commands

Every Python invocation goes through pixi. Never `pip`, `pip3`, `conda`, `poetry`, `venv`, or `virtualenv` for project work. System `python3` lacks the project dependencies and will fail with import errors.

## Daily-use commands

```bash
pixi install            # provision env from pixi.lock
pixi run test           # fast unit tests only (excludes `slow` marker)
pixi run test-all       # all tests, including HF-downloading integration suite
pixi run lint           # ruff check on isanlp_rst, tests, scripts
pixi run typecheck      # pyright (strict scope per pyproject.toml)
pixi run smoke          # parser smoke test on CPU
pixi run smoke-mps      # parser smoke test on MPS (Apple Silicon)
pixi run mdlint         # markdownlint-cli2 for README, CLAUDE.md, UniRST_Metrics.md
```

## Performance and verification commands

```bash
pixi run smoke-full     # full smoke (all five published models)
pixi run smoke-full-mps # full smoke on MPS
pixi run bench          # performance bench across models / dtypes
pixi run cuda-smoke     # CUDA verification (for NVIDIA hosts only)
```

## Dependency management

```bash
pixi add <package>           # add a new dependency, updates pixi.lock
pixi add --pypi <package>    # add a PyPI-only package
pixi remove <package>        # remove a dependency
```

Never edit `pixi.lock` manually — it's generated.

## When to use each test command

- **Refactoring or editing inherited research code:** `pixi run test-all` to catch dtype-equivalence regressions.
- **Editing tests, scripts, or new modules:** `pixi run test` is usually enough; integration tests are slow and require model downloads.
- **Before commit on substantive changes:** `pixi run lint && pixi run typecheck && pixi run test`.
- **Before commit on changes to the predictor stack:** add `pixi run smoke` or `pixi run smoke-mps` to the above.
- **CI:** GitHub Actions runs fast tests on every push and integration tests nightly. See [`.github/workflows/`](../../.github/workflows/).

## Single-test invocation

```bash
pixi run pytest tests/test_integration.py::test_specific_thing -v
```

Use this when iterating on one test rather than running the whole suite.

## One-off Python with project deps

```bash
pixi run python -c 'from isanlp_rst.parser import Parser; print(Parser.__doc__)'
pixi run -- python script.py
```

Never `python script.py` directly — the system interpreter doesn't see the project deps.

## Forbidden

- `pip install ...` — blocked by `~/.claude/settings.json` deny list; backstop for the pixi-only rule.
- `conda install ...` — same.
- `poetry add ...` — same.
- Bare `pytest ...` — runs under whichever interpreter happens to be on PATH; bypasses the pixi env.
- Editing `pixi.lock` by hand — regenerate via `pixi install` or `pixi add` / `pixi remove`.

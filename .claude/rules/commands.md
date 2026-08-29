# Commands

Every Python invocation goes through pixi. Never `pip`, `pip3`, `conda`, `poetry`, `venv`, or `virtualenv` for project work. System `python3` lacks the project dependencies and will fail with import errors.

## Daily-use commands

The `default` environment is active by default:

```bash
pixi install                            # provision default dev environment from pixi.lock
pixi run test                           # unit and offline test battery (excludes slow/stress)
pixi run test-deep                      # full integration test suite
pixi run test-stress                    # multithreaded and megadoc stress tests
pixi run lint                           # ruff check on isanlp_rst, tests, scripts, tools
pixi run typecheck                      # pyright Strict Mode A
pixi run mdlint                         # markdownlint-cli2 across all tracked markdown
pixi run cleanup                        # remove bytecode, tool caches, temp files (not .pixi)
pixi run -e production production-smoke # verify clean-room production wheel boundary
pixi run build-production               # build reproducible production wheel and sdist
```

`./cleanup.sh` is the same cleaner without going through the pixi task table; it still prefers `pixi run python` when `.pixi` exists.

## Performance and verification commands

```bash
pixi run smoke-full     # full smoke (all five published models)
pixi run smoke-full-mps # full smoke on MPS
pixi run bench          # performance bench across models / dtypes
pixi run cuda-smoke     # CUDA verification (for NVIDIA hosts only)
pixi run rst-diag <paths>  # RST quality proxy metrics over .md / docling / doclang sources
```

`rst-diag` loads the model once and dispatches by suffix; use it to A/B
any harvest-policy change (joint ratio, tree skew, cross-boundary ratio,
note ratio, table-analysis count). `--json` for machine output.

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

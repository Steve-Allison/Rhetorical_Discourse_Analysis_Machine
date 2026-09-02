# Commands

Every Python invocation goes through pixi. Never `pip`, `pip3`, `conda`, `poetry`, `venv`, or `virtualenv` for project work. System `python3` lacks the project dependencies and will fail with import errors.

## The task table is the authority

Task names, commands, and their one-line descriptions live in `pyproject.toml` under
`[tool.pixi.feature.offline.tasks]` (the `default` environment) and
`[tool.pixi.feature.production.tasks]`. This file does not copy them — a copied
description is a description that drifts. List them with:

```bash
pixi task list
```

Tasks defined in more than one environment (`production-boundary`,
`production-import-check`) need an explicit `-e`; the bare form fails as ambiguous.

## When to use what

- **Everyday**: `pixi run test`, `pixi run lint`, `pixi run typecheck`, `pixi run mdlint`.
- **Editing the predictor stack** (`rdam/rst/transformer_parser/`, `parser.py`,
  `model_loading/`): `pixi run test-all`. It includes the dtype-equivalence suite and the
  production smoke, which loads every release in `models/model-releases` on every
  available device. `pixi run smoke` runs the smoke alone.
- **Before committing substantive changes**: `pixi run lint && pixi run typecheck && pixi run test`,
  plus `test-all` for predictor-stack changes.
- **Release**: tag the commit `v<version>` (the version declared in `pyproject.toml`),
  then `pixi run build-production`, `pixi run validate-production-artifacts`, and
  `pixi run -e production production-clean-install`. `dist/<version>/` is ignored build
  output; the committed record is the evidence JSON the build task names
  (`specs/010-repository-migration/evidence/release/` for 6.0.0). `production-import-check`
  imports the editable source only and certifies no wheel.
- **A stored release under a new package line**: `pixi run redeclare-compatibility`
  records a manifest-bound compatibility re-declaration beside the release with its
  evidence; `pixi run rst-baseline compare` gives the classified equivalence verdict.
- **Quality diagnostics**: `pixi run rst-diag <paths>`; `--json` for machine output.
- **CI** (`.github/workflows/`): fast tests on every push, the slow suite nightly. The
  model smoke is local-only because weights are not in git.

## Single-test invocation

```bash
pixi run pytest tests/integration/test_integration.py::test_specific_thing -v
```

## One-off Python with project deps

```bash
pixi run python -c 'from rdam.rst.parser import Parser; print(Parser.__doc__)'
pixi run -- python script.py
```

Never `python script.py` directly — the system interpreter doesn't see the project deps.

## Dependency management

```bash
pixi add <package>           # add a new dependency, updates pixi.lock
pixi add --pypi <package>    # add a PyPI-only package
pixi remove <package>        # remove a dependency
```

Never edit `pixi.lock` manually — it's generated.

## Forbidden

- `pip install ...` — blocked by `~/.claude/settings.json` deny list; backstop for the pixi-only rule.
- `conda install ...` — same.
- `poetry add ...` — same.
- Bare `pytest ...` — runs under whichever interpreter happens to be on PATH; bypasses the pixi env.
- Editing `pixi.lock` by hand — regenerate via `pixi install` or `pixi add` / `pixi remove`.

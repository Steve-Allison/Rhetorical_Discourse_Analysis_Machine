# Code standards

Two modes coexist here. Match the mode of the module you're editing.

## Mode A — New code (modern Python 3.13+)

Anything we author from scratch (e.g. anything that will land under `isanlp_rst/docling/` when the Docling-native entry point ships, plus any new test files, scripts, or utility modules):

- `from __future__ import annotations` at the top of every module
- Type hints on every public signature
- `X | None`, never `Optional[X]`
- `@dataclass(frozen=True, slots=True)` for value types
- `pathlib.Path`, never `os.path`
- f-strings, never `.format()` or `%`
- `match` statements where they read naturally
- `@cache` from `functools`, not `lru_cache(maxsize=None)`
- Modern stdlib: `itertools.batched`, `pairwise`, `chain.from_iterable`; `operator.attrgetter` / `itemgetter` over lambdas
- `datetime.now(UTC)`, never `datetime.utcnow()`
- Native exception propagation; no `Result[T, E]` for internal flow; no defensive returns. Honour `~/.claude/rules/no-defensive-coding.md`.
- `type X = ...` (PEP 695, 3.12+), not `TypeAlias`
- `def f[T](...)`, not `TypeVar` declarations
- `@override` decorator on subclass overrides

## Mode B — Inherited research modules (surgical)

These directories are inherited research code from `tchewik/isanlp_rst`. Match their existing style there; no opportunistic refactors:

- `isanlp_rst/dmrst_parser/src/`
- `isanlp_rst/universal_parser/src/`
- `isanlp_rst/dmrst_parser/multiple_runs.py`
- `isanlp_rst/dmrst_parser/data_manager.py`
- `isanlp_rst/universal_parser/multiple_runs.py`
- `isanlp_rst/universal_parser/data_manager.py`
- `isanlp_rst/utils/du_converter.py`
- `isanlp_rst/rstviewer/`

These are listed in `tool.ruff.extend-exclude` in `pyproject.toml`. Bug fixes are in scope; aesthetic sweeps are not. If you touch them for a bug fix, follow their existing style (often: no type hints, mixed casing, older idioms).

## Lint and type scope

| Tool | Strict on | Lenient on |
|---|---|---|
| ruff | `isanlp_rst/parser.py`, `isanlp_rst/base_predictor.py`, `isanlp_rst/{dmrst,universal}_parser/predictor.py`, `isanlp_rst/utils/mps_init.py`, `tests/`, `scripts/`, anything new | the Mode B directories above |
| pyright | the same set as ruff (see `tool.pyright.include` in `pyproject.toml`) | everything not in `include` is not type-checked |

If new code lands outside `tool.pyright.include`, add it to that list.

## Tests

- Real test suite under `tests/` — 85 unit + 27 integration as of 2026-05.
- New code lands with new tests in the same commit (or the next, if scope permits). Not "later".
- Markers (defined in `pyproject.toml`):
  - `slow` — integration tests that download HF models (~2 GB each). Excluded from `pixi run test`; included in `pixi run test-all`.
- Run tests via pixi (`pixi run test` / `pixi run test-all`); never bare `pytest`.

### Test honesty

- **No mocks for internal code.** Mock only truly external systems (the HF Hub, the network).
- **Default to KEEP for tests during audits.** Tests are evidence; don't remove them unless they encode something demonstrably false (and you have the verbatim evidence).
- **Don't modify a test to make it pass.** Fix the code instead. The only exception: the test is provably wrong, and you've explained why before changing it.
- **`tests/test_integration.py`** is the dtype-equivalence + end-to-end suite. If you change any part of the predictor stack, run `pixi run test-all` and check the equivalence suite still passes.

## Gotchas

- **Python `requires-python = ">=3.8"`** in `pyproject.toml`. The pixi env is 3.10+. Use 3.13 idioms for new code; trust the `requires-python` floor for compatibility.
- **`numpy==1.26.4`** is pinned. Don't bump without checking transformer compatibility.
- **HF revisions are the version channel.** `hf_model_version` maps to a git ref on the HF repo — switching versions re-downloads weights / config / relation table.
- **`<P>` token** is added to the tokenizer at load time (`tokenizer.add_tokens(['<P>'])`) and the transformer embeddings are resized accordingly. Anything that re-instantiates the tokenizer must replicate this.
- **`tokenizer.model_max_length = 1e9`** is intentional — sliding-window encoding, this suppresses HF's max-length warning. Don't "fix" it.
- **Razdel** does the initial word-level tokenisation regardless of language; the transformer subword tokenisation runs on top.
- **Pydantic field annotations:** if the project ever picks up Pydantic v2, do NOT move field types into `TYPE_CHECKING` blocks (`TC001` / `TC002` / `TC003` should be ignored in Pydantic-using modules because the model resolves types at runtime).

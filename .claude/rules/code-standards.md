# Code standards

One quality bar for the whole repo. Treat every module as Steve Allison's
production Python. Provenance (Elena / `tchewik`) is not a style freeze.
See [`AGENTS.md`](../../AGENTS.md).

## Mode A — Modern Python (3.14 idioms, every file you touch)

Including `*/src/parser/`, `*/src/corpus/`, `rstviewer/`, `data_manager.py`,
`du_converter.py`, tests, and scripts. When you edit a file, bring the
touched code up to this bar. Do not leave a warning or footgun because
the file started as research code.

- Do **not** add `from __future__ import annotations`. 3.14 deferred
  evaluation (PEP 649 / 749) is the default; the future import *stringifies*
  annotations (PEP 563) and is scheduled for deprecation after 3.13 EOL
  (2029), then removal. Forward references work unquoted. When you touch a
  module that still has the future import, delete it.
- Type hints on every public signature
- `X | None`, never `Optional[X]`
- `@dataclass(frozen=True, slots=True)` for value types
- `pathlib.Path`, never `os.path`
- f-strings, never `.format()` or `%`
- `match` statements where they read naturally
- `@cache` from `functools`, not `lru_cache(maxsize=None)`
- Modern stdlib: `itertools.batched`, `pairwise`, `chain.from_iterable`; `operator.attrgetter` / `itemgetter` over lambdas
- `datetime.now(UTC)`, never `datetime.utcnow()`
- Native exception propagation; no `Result[T, E]` for internal flow; no defensive returns; no silent retries — native LLM output and transport retries are explicitly bounded; failures are classified (see the `Retryability` contract in `rdam/ingest/contracts/failure.py`) and propagated when their declared retry policy is exhausted.
- `type X = ...` (PEP 695, 3.12+), not `TypeAlias`
- `def f[T](...)`, not `TypeVar` declarations
- `@override` decorator on subclass overrides

Do not change trained architecture or inference maths in the name of style.

## Mode B — retired

The old “inherited research, surgical only, no aesthetic sweeps” split is
**retired**. There is no second, lower bar. The current Ruff task covers all declared project roots; provenance grants no
exception from that scope.

## Lint and type scope

| Tool | Strict on |
|---|---|
| ruff | `rdam/` (including `rstviewer`), `workbench/`, `tests/`, `scripts/`, `tools/` |
| pyright | `rdam/` plus the explicitly listed tests and tools in `tool.pyright.include`; not the entire workbench/test tree |

If new code lands outside `tool.pyright.include`, add it to that list.

## Tests

- Real test suite under `tests/`: `pixi run test` is the fast set, `pixi run test-all` is everything.
- Run the existing targeted tests for what you changed; add tests only when asked.
- Markers (defined in `pyproject.toml`):
  - `slow` — tests that load models (local releases from `models/model-releases`, or HF downloads). Excluded from `pixi run test`; included in `pixi run test-all`.
  - `stress` — concurrency, megadoc, and memory-leak tests; `pixi run test-stress`.
- Run tests via pixi; never bare `pytest`.

### Test honesty

- **No mocks for internal code.** Mock only truly external systems (the HF Hub, the network).
- **Default to KEEP for tests during audits.** Tests are evidence; don't remove them unless they encode something demonstrably false (and you have the verbatim evidence).
- **Don't modify a test to make it pass.** Fix the code instead. The only exception: the test is provably wrong, and you've explained why before changing it.
- **`tests/integration/test_integration.py`** is the dtype-equivalence + end-to-end suite and **`tests/integration/test_production_smoke.py`** is the release smoke. If you change any part of the predictor stack, run `pixi run test-all` once at the end of the work and check both still pass.

## Gotchas

- **Python `requires-python = ">=3.14"`** in `pyproject.toml`. Pixi / CI use **Python 3.14** (`python = "3.14.*"`). Avoid exactly 3.14.1 (`networkx` excludes it). Annotations use 3.14 deferred evaluation; do not reintroduce PEP 563 stringification.
- **`numpy>=1.26.4`** tracks latest (resolves to 2.5.0 as of 2026-06-27). The old `==1.26.4` exact pin was lifted after verifying numpy 2.x is green across the full suite; transformers 5.x only requires `numpy>=1.17`.
- **HF revisions are the version channel.** `hf_model_version` maps to a git ref on the HF repo — switching versions re-downloads weights / config / relation table.
- **`<P>` token** is added to the tokenizer at load time (`tokenizer.add_tokens(['<P>'])`) and the transformer embeddings are resized accordingly. Anything that re-instantiates the tokenizer must replicate this.
- **Existing tokenizer sentinel:** the DMRST/UniRST predictors set `model_max_length` to `int(1e9)` to bypass tokenizer warnings before sliding-window encoding. This is not a measured or declared model capacity and must not be reported as one. Capacity evidence must come from the actual model/runtime contract.
- **Razdel** does the initial word-level tokenisation regardless of language; the transformer subword tokenisation runs on top.
- **Pydantic field annotations:** the project uses Pydantic v2; do NOT move field types into `TYPE_CHECKING` blocks (the model resolves these types at runtime; keep the imports available).

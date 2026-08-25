# Feature 003 completion evidence

Date: 2026-08-25

Pre-split baseline revision: `07813048d6cb3bb9f26883bf2f54d918c3355099`

Production version: `isanlp_rst 4.0.0`

## Exact completion candidate

| Artifact | SHA-256 | Members | Boundary result |
|---|---|---:|---|
| `dist/isanlp_rst-4.0.0-py3-none-any.whl` | `d1e920a2be0b22ab88376ccf7197d862656f6c1e30b016b5884bb17172b130e6` | 120 | valid; zero forbidden members or dependencies |
| `dist/isanlp_rst-4.0.0.tar.gz` | `b1faf23ac97ef3b27c3b76ca95d369a2f5c406d05a56d3e18c4a56168452cfe9` | 126 | valid; zero forbidden members or dependencies |

The artifact receipt was produced by:

```bash
pixi run --environment production production-artifacts
```

It inspected the exact member names and `Requires-Dist` metadata in both archives. Neither archive contains `offline_workbench`, `research_harness`, tests, scripts, specs, corpora, experiments, caches, local data, unsafe serialized model files, or secret-like paths.

## Clean installed-wheel proof

The exact wheel above was installed outside the repository in two independently created environments based on the production Pixi environment:

1. core-only: wheel installed with `--no-deps` over the production dependency set;
2. formats-enabled: wheel installed with its `[formats]` extra.

Both environments resolved `isanlp_rst` from their temporary `site-packages`, not the checkout, and proved `fire`, `jsonnet`, `nltk`, `peft`, `pytest`, and `tiktoken` unavailable. The formats-enabled environment successfully executed Markdown, DocLang, and Docling adapters and serialized each result.

The formats-enabled install then loaded every promoted model release through `Parser.from_model_release` and executed raw-text, predefined-EDU, and typed-analysis serialization/reload routes:

| Release | Family | CPU | MPS | Raw/pre-segmented end | Typed nodes |
|---|---|---:|---:|---:|---:|
| `gumrrg-eb1d5745f3a1` | DMRST | pass | pass | 53 / 53 | 5 |
| `rrtrrg-a4d19fc65bb1` | UniRST | pass | pass | 53 / 53 | 5 |
| `rstdt-cc01afde1232` | DMRST | pass | pass | 53 / 53 | 5 |
| `rstreebank-a3df81661baa` | DMRST | pass | pass | 53 / 53 | 5 |
| `unirst-9407970f1d9d` | UniRST | pass | pass | 53 / 53 | 5 |

The same installed wheel also passed hierarchical analysis (`3` stitched nodes), deterministic eRST capability rejection without a completion bundle, and RS4 runtime round-trip. CPU and MPS installed-wheel comparisons against the frozen pre-split baseline both returned `differences: []`. Parity covers prepared inputs, raw/pre-segmented trees, warnings, deterministic failure, stable provenance, typed serialization/reload, and representative Markdown behavior; timestamps, timings, and checkout-only Git availability are explicitly environment-normalized.

Commands:

```bash
pixi run --environment production production-clean-install
pixi run --environment production python tools/production_boundary/clean_install.py \
  --wheel dist/isanlp_rst-4.0.0-py3-none-any.whl \
  --root . \
  --model-store /Users/steveallison/.cache/isanlp_rst/model-releases \
  --full --device mps \
  --parity-baseline specs/003-production-codeline-split/evidence/parity-baseline.json
```

Both returned `valid: true`; both parity receipts returned zero differences.

## Boundary, model, and offline-workbench proof

- Routine boundary: `185` files scanned, `107` production modules, `860.829 ms`, zero violations.
- Ownership: every relevant nested path matches exactly one rule; unmatched and ambiguous paths fail causally.
- Local model input: loose `model_dir` fails before predictor construction; only a complete hash-verified, compatible release manifest is accepted.
- Promotion: all five available released models were promoted byte-for-byte into `/Users/steveallison/.cache/isanlp_rst/model-releases`; strict receipts are in `model-promotion-receipts.json`.
- Offline workbench: eight canonical commands across corpus preparation, both parser trainers, segmenter training, eRST training, evaluation, research, and benchmarking reached bounded help or causal-test boundaries with exit code `0` and hashed output receipts. No category is quarantined.

## Regression and quality gates

| Gate | Actual result |
|---|---|
| Full repository suite | `941 passed in 457.71s (0:07:37)` |
| Non-slow suite | `867 passed, 73 deselected in 13.65s` |
| Boundary/model/parser focused tests | `50 passed in 2.34s` |
| Ruff | `All checks passed!` |
| Pyright | `0 errors, 0 warnings, 0 informations` |
| Routine production boundary | `valid: true`, `violations: []`, `860.829 ms` |
| Wheel/sdist boundary | `valid: true`, zero forbidden members/dependencies |
| Core-only clean install | `valid: true`, offline distributions absent |
| Formats clean install | `valid: true`, all three adapters passed |
| CPU clean-wheel parity | `differences: []` |
| MPS clean-wheel parity | `differences: []` |

## Result

Feature 003 is implemented as a physical, install, dependency, model-asset, and execution boundary. Other projects import the small production `isanlp_rst` distribution; corpus creation, fitting, evaluation, benchmarking, research, and promotion remain in the single root offline environment and are absent from publication artifacts.

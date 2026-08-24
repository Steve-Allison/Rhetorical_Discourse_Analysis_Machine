# Verification Quickstart

This is an operator sequence, not proof of success. Every command must be run and its actual output
captured in the release ledger before “passing” or “complete” is claimed.

## Environment

```bash
cd '/Users/steveallison/AI_Projects+Code/isanlp_rst'
/Users/steveallison/.pixi/bin/pixi install --locked
```

The ignored repository-root `.env` may contain `HF_TOKEN` or fallback
`HUGGINGFACEHUB_API_TOKEN`. Do not source it into shell tracing and do not print it.

## Focused contract validation

```bash
/Users/steveallison/.pixi/bin/pixi run --locked pytest \
  tests/test_format_projections.py \
  tests/test_doclang_harvester.py \
  tests/test_doclang_boundaries.py \
  tests/test_result_cache.py -q

PYTHONWARNINGS=error /Users/steveallison/.pixi/bin/pixi run --locked pytest \
  tests/test_erst_formalism.py \
  tests/test_erst_corpus.py \
  tests/test_neural_erst.py \
  tests/test_erst_checkpoint.py -q
```

## Corpus and baseline

The published comparison authority is GUM V9.2.0, not the current production-corpus pin. Private
corpus and experiment roots are arguments, not tracked configuration. The current authority receipt
is deliberately blocked because the paper's claimed official scorer is not publicly locatable.

```bash
/Users/steveallison/.pixi/bin/pixi run --locked python scripts/reproduce_erst_baseline.py \
  --authority config/erst/baseline-authority-gum-v9.2.0.json \
  --experiment-root '/private/path/to/isanlp-rst-v4-runs'
```

Expected current result: exit status 2 after writing `baseline-reproduction-diagnosis.json`; no corpus,
training, test, or test2 data is accessed. That non-zero status is the verified fail-closed outcome,
not a passing baseline reproduction.

## Architecture screening and final evaluation

Architecture screening and champion evaluation are not executable in this release candidate: the
validated research-program diagnosis retains every mandatory system as blocked, and the promotion
decision forbids upload. Do not create or invoke screening/final-evaluation commands until a new
authority receipt identifies the official scorer and records parity. If that authority is later
resolved, final evaluation remains one-time for a champion/protocol pair and must not be rerun after
seeing test results.

## Exact release candidate

Run focused checks during development. Run this complete set once after the publication candidate is
frozen:

```bash
PYTHONWARNINGS=error /Users/steveallison/.pixi/bin/pixi run --locked test-all
/Users/steveallison/.pixi/bin/pixi run --locked lint
/Users/steveallison/.pixi/bin/pixi run --locked typecheck
/Users/steveallison/.pixi/bin/pixi run --locked mdlint
PYTHONWARNINGS=error /Users/steveallison/.pixi/bin/pixi run --locked smoke-full
PYTHONWARNINGS=error /Users/steveallison/.pixi/bin/pixi run --locked smoke-full-mps
/Users/steveallison/.pixi/bin/pixi run --locked python scripts/verify_release_candidate.py
```

The release verifier must build wheel/sdist in a fresh temporary directory, inspect every member,
install the wheel in a clean temporary Pixi environment, run representative format/API/cache/eRST
paths, audit dependencies, scan secrets, validate a private promoted bundle if one exists, and persist
hashes/results.

Regenerate Graphify only after source and documents are final, then inspect graph health and diff from
the preserved before-state.

## Publication close

If and only if promotion passed, validate and privately upload the bundle, then pin the returned
immutable Hugging Face commit. Otherwise release metadata must contain no canonical eRST checkpoint.

After all gates and report closure:

```bash
git status --short --branch
git log --oneline --decorate -8
git push origin codex/spec-kit-adoption
git status --short --branch
```

Final evidence names CUDA as unverified on this host.

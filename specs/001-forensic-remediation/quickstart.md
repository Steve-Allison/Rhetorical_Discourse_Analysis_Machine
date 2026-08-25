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

## Corpus and scorer contract

Private corpus and experiment roots are arguments, not tracked configuration. GUM V12.1.0 document
partitions and the repository-owned scorer are the comparison authorities. Validate their current
implemented boundaries with:

```bash
/Users/steveallison/.pixi/bin/pixi run --locked pytest \
  tests/test_erst_corpus.py \
  tests/test_erst_corpus_contracts.py \
  tests/test_parseval_math.py -q
```

These checks establish corpus, candidate, and metric behavior. They do not establish that any model
comparison has run.

## Architecture screening and final evaluation

Architecture screening and champion evaluation are not executable in the current checkout because
the shared experiment runner, executable protocol/receipt boundaries, and most required architecture
implementations do not exist. This is open implementation work, not an externally blocked or
successful outcome. T054-T064 define the required build and evaluation sequence. Final evaluation
remains one-time for a champion/protocol pair and must not be rerun after seeing test results.

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
paths, audit dependencies, scan secrets, validate a private selected bundle if one exists, and persist
hashes/results.

Regenerate Graphify only after source and documents are final. First align the installed package with
the active skill version, then build a directed graph and require clean raw-extraction and persisted-
graph integrity diagnostics before diffing against the preserved before-state.

## Publication close

If and only if selection passed, validate and privately upload the bundle, then pin the returned
immutable Hugging Face commit. Otherwise release metadata must contain no canonical eRST checkpoint.

After all gates and report closure:

```bash
git status --short --branch
git log --oneline --decorate -8
git push origin codex/spec-kit-adoption
git status --short --branch
```

Final evidence names CUDA as unverified on this host.

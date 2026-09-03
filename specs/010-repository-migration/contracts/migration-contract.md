# Contract: Repository Migration

## Package topology

1. `pyproject.toml` is the sole package identity authority.
2. The wheel target contains exactly one package directory: `rdam`.
3. Production technique modules live beneath that root.
4. `workbench`, tests, repository ontology, and offline dependencies are forbidden artifact members.

## Preservation

1. Baseline inputs and records are immutable.
2. The migration-commit output was recaptured with the same public operations.
3. Every changed leaf in the immutable comparison is classified.
4. Any analytical difference is a contract failure.
5. Execution/package/derived changes are accepted only when the classifier proves their exact category.
6. Historical source-form and model-backed output remains evidence of the migration
   commit and is not rerun through formats or a production family that have since changed.

## Reproducible build

1. Source selection requires a clean exact Git revision.
2. A deterministic archive is extracted into two independent roots.
3. Both roots build the exact wheel/sdist pair using locked local dependencies and no package index.
4. Corresponding artifact bytes must be identical.
5. Packaged provenance names the selected source, never the caller's ambient checkout state.

## Installed acceptance

1. The wheel is installed into a fresh environment outside the checkout.
2. External network access is disabled.
3. Offline-only distributions are absent.
4. Public imports, capability declarations, canonical round trips, and optional-format behaviour are exercised.
5. Full acceptance additionally proves model-backed Python/CLI semantic parity when explicitly requested.

# Data Model: Repository Migration

## ReleaseIdentity

The derived identity for the one distribution.

- `distribution`: static `[project].name`
- `version`: static `[project].version`
- `package_dir`: the sole wheel package path
- Derived: import package, normalized filename stem, wheel name, sdist name, tag, output directory

Validation: name/version are strings; the wheel declares exactly one package directory.

## SourceReleaseRecord

The exact clean source selected for a build.

- Git commit and tree identities
- deterministic Git archive SHA-256
- source date epoch

Validation: the checkout root matches the requested root and the worktree is completely clean.

## ReproducibleBuildReport

The relationship between one source record and two independently built artifact pairs.

- source commit/tree/tag/archive/date
- build frontend/backend identities
- build-report and packaged-provenance digests
- exact wheel and sdist filename, size, and SHA-256

Validation: each independent wheel hash agrees and each independent sdist hash agrees.

## BaselineRecordSet

The immutable pre-migration public-contract sample.

- capabilities record
- six preparation records, one for each source form
- text and EDU analysis records when the model release is available
- canonical digest index

## RecordComparison

- baseline digest
- actual digest
- ordered field differences
- each difference has path, before value, after value, and `DifferenceClass`

State rule: a comparison is analytically equivalent exactly when no difference is
classified `analytical`.

## BoundaryReport

- scanned source members
- production module count
- artifact receipts when requested
- typed violations

State rule: valid exactly when no violations exist and every artifact receipt is valid.

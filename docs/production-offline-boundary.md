# Production package and offline workbench boundary

## Ownership rule

`rdam` — the one production package — contains only code and resources required while
a consumer performs analysis: the machine (`rdam`), the RST/eRST provider (`rdam.rst`),
and the Dung and IBIS providers (`rdam.dung`, `rdam.ibis`). `workbench` owns corpus
construction, training, calibration, evaluation, benchmarking, research, and promotion.
Provenance does not change that boundary: inherited inference code is production code
and must meet the same Python 3.14 standard.

`rdam.rst.ingest` is core production code. Docling, DocLang, and Markdown
distributions are optional under the `formats` extra; their adapter modules are
private implementation details. The core wheel can import, load schemas,
serialize contracts, prepare text/EDUs, and discover all capability states
without those distributions installed.

## Install boundaries

```bash
# Core runtime (after `pixi run build-production`; dist/<version>/ is ignored build output)
pip install dist/6.0.0/rdam-6.0.0-py3-none-any.whl

# Core plus Markdown, Docling, DocLang XML, and DocLang archive ingest
pip install "dist/6.0.0/rdam-6.0.0-py3-none-any.whl[formats]"

# Repository development environments
pixi install -e production
pixi install -e offline
```

The production environment runs inference and production-boundary checks. The
offline environment adds test, lint, type-check, corpus, training, evaluation,
research, and promotion dependencies.

## Capability and identity boundary

Capability discovery reads installed distribution metadata only. It must not:

- import a format adapter;
- instantiate a parser;
- resolve, download, or mmap model bytes;
- access a network;
- inspect `workbench`.

Parser identity has four explicit states:

| State | Meaning | Durable cache |
|---|---|---|
| `immutable_release` | every participating runtime file is manifest-validated, loaded locally, and rehashed | eligible when every component is immutable |
| `mutable_instance` | a configured component has no immutable release | ineligible |
| `unidentified` | a parser-like object cannot state its identity | ineligible |
| `not_configured` | preparation is available but analysis is not | ineligible |

The active production parser families are DMRST and UniRST. Candidate architectures
(such as ModernBERT) reside strictly in the workbench. No model weight is packaged in the wheel.

A stored release's manifest declares `compatibility_range` as of promotion time and is
immutable. When a later package line runs a release unchanged, that finding is recorded
beside the release as a manifest-bound `CompatibilityRedeclaration`
(`<store>/<release_id>.compatibility.json`, `pixi run redeclare-compatibility`); the
loader honours it only for the exact manifest it names.

## Published and excluded content

| Capability | Owner | Wheel |
|---|---|---:|
| The machine: declarations, capability states, outcomes, promotion decision contract | `rdam` | yes |
| Parser facade and active inference runtime | `rdam.rst.parser`, predictors, segmenter | yes |
| Machine-facing RST/eRST adapter | `rdam.rst.provider` | yes |
| Strict source, preparation, analysis, inference, failure, and capability contracts | `rdam.rst.ingest` | yes |
| Canonical schemas, public-surface inventory, and build provenance | package resources | yes |
| Private Docling/DocLang/Markdown loaders | `rdam.rst.doclang`, `rdam.rst.markdown`, ingest harvest | yes, dependencies via `formats` |
| eRST signal detection, scoring, decoding, checkpoint loading | `rdam.rst.erst`, `rdam.rst.english.erst` | yes |
| Released-model manifest validation, loading, compatibility re-declaration | `rdam.rst.model_loading` | yes |
| Dung semantics and provider, with its packaged decision | `rdam.dung` | yes |
| gIBIS grammar and provider, with its packaged decision | `rdam.ibis` | yes |
| Vendored Central distribution and LinkML profile | `ontology/` (repository) | no — only the projected `rdam/resources/framework-identities.json` |
| Corpora and corpus conversion | `workbench.corpus` | no |
| Training and calibration | `workbench.training` | no |
| Evaluation and benchmarking | `workbench.evaluation` | no |
| Research comparisons | `workbench.research` | no |
| Promotion/build tooling, tests, specs, evidence, caches | repository-only | no |

The artifact validator rejects workbench, tests, scripts, specs, corpora,
experiments, cache files, secrets, pickles, Python bytecode, model-weight
extensions, and any import root other than `rdam/` in the wheel. It verifies wheel
`RECORD`, metadata, the `rdam-rst` console entry point, schemas, public surface,
`py.typed`, and packaged provenance — all against the name and version declared in
`pyproject.toml`.

## Installed provenance

The release build exports one clean named Git commit, derives
`SOURCE_DATE_EPOCH` from that commit, and injects `rdam/build-provenance.json` (a package
resource) into independent temporary build roots. The wheel is built through the sdist
twice; corresponding SHA-256 hashes must be identical.

Installed runtime provenance reads that packaged resource. It does not call Git
or assume a checkout exists. The resource identifies source commit/tree/archive
and build input, but excludes wheel/sdist hashes to avoid self-reference.

## Clean-install proof

The clean-install tool creates fresh virtual environments without
`--system-site-packages`, installs the exact wheel path, runs `python -I` from a
temporary directory, rejects imports from the checkout, checks the installed and runtime
versions against the version in the wheel's filename, disables external network access
for acceptance, runs `pip check`, and retains `pip inspect`.

Core acceptance proves unavailable optional forms yield typed provider
failures. Formats acceptance covers all six source forms. Full acceptance also
requires the exact promoted ModernBERT release and checks canonical parser
results, loaded-component receipts, validation, and CLI semantic parity.

```bash
git tag v6.0.0
pixi run build-production
pixi run validate-production-artifacts
pixi run -e production production-clean-install
```

The build command refuses any tracked or untracked worktree change, refuses a HEAD tag
that names a different version, and replaces the previous pair in the ignored
`dist/<version>/` directory. A release is the tagged commit; the artifacts are rebuilt
from it on demand and the committed record is `source-release.json` and
`reproducible-build.json` in the evidence directory the build task names
(`specs/010-repository-migration/evidence/release/` for 6.0.0). Source-tree tests are not
artifact certification — `production-clean-install` is.

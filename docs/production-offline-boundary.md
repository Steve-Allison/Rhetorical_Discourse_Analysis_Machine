# Production package and offline workbench boundary

## Ownership rule

`isanlp_rst` contains only code and resources required while a consumer performs
RST/eRST analysis. `workbench` owns corpus construction, training, calibration,
evaluation, benchmarking, research, and model promotion. Provenance does not
change that boundary: inherited inference code is production code and must meet
the same Python 3.14 standard.

`isanlp_rst.ingest` is core production code. Docling, DocLang, and Markdown
distributions are optional under the `formats` extra; their adapter modules are
private implementation details. The core wheel can import, load schemas,
serialize contracts, prepare text/EDUs, and discover all capability states
without those distributions installed.

## Install boundaries

```bash
# Core runtime
pip install dist/5.0.0/isanlp_rst-5.0.0-py3-none-any.whl

# Core plus Markdown, Docling, DocLang XML, and DocLang archive ingest
pip install "dist/5.0.0/isanlp_rst-5.0.0-py3-none-any.whl[formats]"

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

The active production parser family is ModernBERT. Historical DMRST and UniRST
releases remain repository/runtime history but are not advertised as active
5.0 canonical-result capability. No model weight is packaged in the wheel.

## Published and excluded content

| Capability | Owner | Wheel |
|---|---|---:|
| Parser facade and active inference runtime | `isanlp_rst.parser`, predictors, segmenter | yes |
| Strict source, preparation, analysis, inference, failure, and capability contracts | `isanlp_rst.ingest` | yes |
| Canonical schemas, public-surface inventory, and build provenance | package resources | yes |
| Private Docling/DocLang/Markdown loaders | `isanlp_rst.doclang`, `isanlp_rst.markdown`, ingest harvest | yes, dependencies via `formats` |
| eRST signal detection, scoring, decoding, checkpoint loading | `isanlp_rst.erst`, `isanlp_rst.english.erst` | yes |
| Released-model manifest validation and loading | `isanlp_rst.model_loading` | yes |
| Corpora and corpus conversion | `workbench.corpus` | no |
| Training and calibration | `workbench.training` | no |
| Evaluation and benchmarking | `workbench.evaluation` | no |
| Research comparisons | `workbench.research` | no |
| Promotion/build tooling, tests, specs, evidence, caches | repository-only | no |

The artifact validator rejects workbench, tests, scripts, specs, corpora,
experiments, cache files, secrets, pickles, Python bytecode, and model-weight
extensions in the wheel. It verifies wheel `RECORD`, metadata, console entry
point, schemas, public surface, `py.typed`, and packaged provenance.

## Installed provenance

The release build exports one clean named Git commit, derives
`SOURCE_DATE_EPOCH` from that commit, and injects canonical
`isanlp_rst/build-provenance.json` into independent temporary build roots. The
wheel is built through the sdist twice; corresponding SHA-256 hashes must be
identical.

Installed runtime provenance reads that packaged resource. It does not call Git
or assume a checkout exists. The resource identifies source commit/tree/archive
and build input, but excludes wheel/sdist hashes to avoid self-reference. The
external release receipt owns artifact and verification identities.

## Clean-install proof

The clean-install tool creates fresh virtual environments without
`--system-site-packages`, installs the exact wheel path, runs `python -I` from a
temporary directory, rejects imports from the checkout, disables external
network access for acceptance, runs `pip check`, and retains `pip inspect`.

Core acceptance proves unavailable optional forms yield typed provider
failures. Formats acceptance covers all six source forms. Full acceptance also
requires the exact promoted ModernBERT release and checks canonical parser
results, loaded-component receipts, validation, and CLI semantic parity.

```bash
pixi run -e default build-production
pixi run -e default validate-production-artifacts
pixi run -e default production-ingest-clean-install
pixi run -e production production-boundary
```

The build command refuses any tracked or untracked worktree change and never
overwrites an existing promoted artifact. It becomes executable only after the
source-release commit exists; source-tree tests are not artifact certification.

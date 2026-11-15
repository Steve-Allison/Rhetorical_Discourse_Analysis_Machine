# Production package and offline workbench boundary

## Ownership rule

`rdam` — the one production package — contains only code and resources required while
a consumer performs analysis: the machine (`rdam`), shared ingest and linguistic
substrate (`rdam.ingest`), lexical concept linking (`rdam.concepts`), the RST provider
(`rdam.rst`), and the twelve additional discourse, rhetorical, and argumentation
providers (`rdam.centering`, `rdam.pdtb`, `rdam.sdrt`, `rdam.speech_acts`,
`rdam.classical_rhetoric`, `rdam.argument_mining`, `rdam.toulmin`, `rdam.walton`,
`rdam.pragma_dialectics`, `rdam.ibis`, `rdam.aspic`, `rdam.dung`;
`rdam/composition.py:14-73`). `workbench` owns corpus construction, training,
calibration, evaluation, benchmarking, research, eRST, and model releases. Provenance
does not change that boundary: inherited inference code is production code and must meet
the same Python 3.14 standard.

`rdam.ingest` is core production code. `dclq` and `doclang[schematron-saxon]` ship in
core `[project.dependencies]` (`pyproject.toml:44-45`), and DocLang validation, decoding,
`dclq` XPath indexing, and archive handling belong to `rdam.ingest.doclang` and
`rdam.ingest._doclang`; every technique consumes the shared inventory,
`LinguisticSubstrate`, and projections.

Starlette, Uvicorn, and h11 belong to the independent `http` extra (`pyproject.toml:58-63`).
Core Python, CLI, schemas, DocLang ingestion, and saved-result operations do not require
`http`. Install `[http]` when loopback HTTP service is wanted.

## Install boundaries

```bash
# Core runtime (after `pixi run build-production`; dist/<version>/ is ignored build output)
pip install dist/6.1.0/rdam-6.1.0-py3-none-any.whl

# Core plus loopback HTTP service
pip install "dist/6.1.0/rdam-6.1.0-py3-none-any.whl[http]"

# Repository development environments
pixi install -e production
pixi install
```

The `production` environment is the isolated consumer environment. The `default`
environment includes HTTP, test, lint, type-check, corpus, training, evaluation,
research, and model-release dependencies (`pyproject.toml:136-140`); everyday tasks need
no environment flag.

## Capability and identity boundary

Model-free ingest discovery reads installed dependency metadata. Configured
machine discovery may additionally validate local model manifests and hashes.
Neither operation may:

- import a format adapter;
- instantiate a parser;
- download, load into tensors, or mmap model weights;
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

A stored release's manifest declares `compatibility_range` as of release time and is
immutable. When a later package line runs a release unchanged, that finding is recorded
beside the release as a manifest-bound `CompatibilityRedeclaration`
(`<store>/<release_id>.compatibility.json`, `pixi run python -m workbench.promotion.compatibility`); the
loader honours it only for the exact manifest it names.

## Published and excluded content

| Capability | Owner | Wheel |
|---|---|---:|
| The machine: declarations, capability states, outcomes | `rdam` | yes |
| Parser facade and active inference runtime | `rdam.rst.parser`, predictors, segmenter | yes |
| Machine-facing RST adapter | `rdam.rst.provider` | yes |
| Strict source, preparation, analysis, inference, failure, and capability contracts | `rdam.ingest` | yes |
| Canonical schemas, public-surface inventory, and build provenance | package resources | yes |
| Private DocLang + `dclq` loaders and linguistic substrate | `rdam.ingest.doclang`, `rdam.ingest._doclang`, `rdam.ingest.substrate` | yes |
| Rust Aho–Corasick lexical concept linker | `rdam.concepts` | yes |
| eRST signal detection, scoring, decoding, checkpoint loading and experimental contracts | `workbench.erst` | no |
| Released-model manifest validation, loading, compatibility re-declaration | `rdam.rst.model_loading` | yes |
| Deterministic Centering Theory & Entity Grid provider | `rdam.centering` | yes |
| CaDiCaL SAT Dung semantics, Wave-2 compilers, and provider | `rdam.dung` | yes |
| Dual-mode gIBIS grammar and provider | `rdam.ibis` | yes |
| Dual-mode ASPIC+ structured argumentation theory and provider | `rdam.aspic` | yes |
| LLM-backed discourse, pragmatic, rhetorical, and argumentation providers | `rdam.pdtb`, `rdam.sdrt`, `rdam.speech_acts`, `rdam.classical_rhetoric`, `rdam.argument_mining`, `rdam.toulmin`, `rdam.walton`, `rdam.pragma_dialectics` | yes |
| Vendored Central distribution and LinkML profile | `ontology/` (repository) | no — generated framework/discourse/technique projections, Walton crosswalk and digest-identified snapshots in `rdam/resources/` |
| Corpora and corpus conversion | `workbench.corpus` | no |
| Training and calibration | `workbench.training` | no |
| Evaluation and benchmarking | `workbench.evaluation` | no |
| Research comparisons | `workbench.research` | no |
| Release/build tooling, tests, specs, evidence, caches | repository-only | no |

The artifact validator rejects workbench, tests, scripts, specs, corpora,
experiments, cache files, secrets, pickles, Python bytecode, model-weight
extensions, and any import root other than `rdam/` in the wheel. It verifies wheel
`RECORD`, metadata, the `rdam` console entry point, schemas, public surface,
`py.typed`, and packaged provenance — all against the name and version declared in
`pyproject.toml`.

## Installed provenance

The standard `build-production` task exports one clean named Git commit, derives
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

The two clean-install environments are `core` and `core+http` (`tools/production_boundary/clean_install.py:147-163`).
Both installs exercise all four canonical `SourceForm` values (`text`, `edus`,
`doclang_xml`, `doclang_archive`), the unified CLI, schema resources, deterministic
`CenteringProvider`, and CaDiCaL-backed `DungProvider`; `core+http` also exercises a real
loopback server. Full acceptance additionally requires the exact stored model release and
checks canonical parser results, loaded-component receipts, validation, and CLI semantic
parity.

```bash
pixi run build-production
pixi run validate-production-artifacts
pixi run -e production production-clean-install \
  --model-store "$HOME/.cache/isanlp_rst/model-releases" \
  --release-id gumrrg-eb1d5745f3a1
```

The build command refuses any tracked or untracked worktree change, refuses a HEAD tag
that names a different version, and replaces the previous pair in the ignored
`dist/<version>/` directory. A tag is optional; if present it must match the package version. The artifacts are rebuilt
from it on demand and the committed record is `source-release.json` and
`reproducible-build.json` in the evidence directory the build task names
(`specs/010-repository-migration/evidence/release/` for 6.0.0). Source-tree tests are not
artifact certification — `production-clean-install` is.

The owner moved eRST to the workbench on 2026-09-06. Production contains no
eRST engine, checkpoint loader, configuration option or completion method. Shared
passive contracts retain saved graph evidence without importing the workbench. Boundary
ownership, production imports, and test suites are verified across all thirteen active
technique boundaries (`rdam/frameworks.py:55-69`); dated seven-technique clean-install
records remain preserved in [Feature 019](../specs/019-unified-machine-interfaces/tasks.md).
Historical release evidence must not be reused to certify a changed checkout.

The documentation refresh builds the current package inputs from an isolated
local Git snapshot under `build/`. Its provenance truthfully identifies that
snapshot; it is not a commit or tag on the main repository branch. The same
existing double-build and artifact checks apply. No external publication occurs.

# Contract: Public Surface and Durable Distribution

**Package release**: `isanlp_rst` 5.0.0  
**Promoted artifact directory**: `dist/5.0.0/`  
**Scope**: Local cross-machine production use

## Public-surface authority

`isanlp_rst/ingest/public-surface.json` is the machine-readable authority for
production symbol membership and support classification. Each entry declares:

- fully qualified symbol or resource name;
- supported public import path, if any;
- kind: function, class, protocol, enum, alias, exception, schema, or resource;
- classification: `supported`, `deprecated`, or `internal`;
- introduced, deprecated, and removal package versions where applicable;
- serialized schema membership;
- stable documentation anchor;
- compatibility guarantee.

The manifest does not duplicate editable function signatures or Pydantic field
definitions. Reconciliation derives those from runtime objects and joins them
to manifest entries. The resulting conformance report must find zero mismatch
among:

- `isanlp_rst.ingest.__all__` and actual importability;
- inspected signatures and protocol members;
- enum/status/error values;
- Pydantic discriminators and fields;
- analysis-policy/output-formalism/evidence-detail enum values;
- analysed-document, decision-evidence, composite-identity, refinement,
  decoder, recombination, and validation receipt models;
- packaged JSON Schemas;
- public documentation examples and anchors;
- compatibility and deprecation declarations.
- installed console-script and retained local-HTTP projection classifications,
  request/result parity, and presentation-view guarantees.

Generated schema and documentation projections are not independently editable
authorities.

## Required distribution metadata

The 5.0.0 package must:

- declare Python 3.14 support and the exact supported dependency ranges;
- keep Docling, DocLang, and Markdown packages under the `formats` extra;
- include `py.typed`;
- declare `Import-Name: isanlp_rst` through current project metadata;
- include public-surface, schema, and build-provenance resources;
- install exactly one supported `isanlp-rst` console entry point whose JSON and
  retained local-HTTP behaviours project the canonical production contract;
- report 5.0.0 through `importlib.metadata.version("isanlp_rst")`;
- contain no research, training, evaluation, promotion, corpus, or model-weight
  content in the production wheel.

Wheel `METADATA`, filename version, runtime version, packaged provenance, and
release receipt must agree exactly.

## Tracked artifact layout

The repository tracks only promoted release content under versioned
directories:

```text
dist/5.0.0/
├── isanlp_rst-5.0.0-py3-none-any.whl
├── isanlp_rst-5.0.0.tar.gz
├── release-receipt.json
└── release-receipt.sha256
```

The blanket `dist/` Git ignore rule must be removed. Build scratch directories
are created outside the repository and are never promoted implicitly. Existing
released directories are immutable; no build overwrites their bytes.

The wheel is the cross-machine install artifact. The sdist proves complete
source packaging and reproducible wheel construction; consuming machines do
not need to build it.

## Release source and promotion sequence

1. Produce a clean source release commit containing package version, contract,
   schemas, public manifest, documentation, tests, and build tooling.
2. Require `git status --porcelain=v1 --untracked-files=all` to be empty.
3. Identify the full source commit and tree; derive `SOURCE_DATE_EPOCH` from the
   commit timestamp.
4. Export that named commit into independent temporary build roots. Do not build
   from mutable checkout files.
5. Build the sdist and build the wheel from the extracted sdist in two
   independent runs with a machine-readable PyPA build report.
6. Require identical SHA-256 hashes for corresponding artifacts from both
   runs.
7. Run artifact, contract, and clean-install verification against the chosen
   artifact bytes.
8. Add the wheel and sdist to `dist/5.0.0/` in an untagged candidate commit.
9. On the second development machine, check out that candidate commit and
   verify the exact committed wheel without rebuilding.
10. Create the canonical release receipt and detached receipt SHA-256 from the
    local and second-machine evidence.
11. Add those two files in a certification commit and tag that commit. The
    receipt identifies the exact source commit from which the unchanged
    artifact bytes were built.

This staged sequence avoids both self-reference and a false second-machine
claim: the artifact must be committed before another machine can verify the
repository artifact, and the final receipt is created only after that
verification exists.

## Release evidence lifecycle

Release evidence is governed repository content, but it is not part of the
installed production API. Strict JSON evidence records are owned by
`tools/production_boundary/contracts.py`, carry an explicit schema name and
version, use RFC 8785 canonical bytes, and are validated before their digests
may enter the release receipt. Human review records are Markdown with a dated
scope, named reviewer, inspected revision, and explicit disposition.

The lifecycle and authority of every Feature 004 evidence file are fixed:

| Evidence | Created | First tracked in | Authority and use |
|---|---|---|---|
| `source-spec-currency.md` | Before source changes | Source release commit | Dated Docling/DocLang currency decision and any required remediation |
| `pre-release-quality.json` | Before source selection | Source release commit | Focused tests, Ruff, and Pyright results over the proposed source tree |
| `performance.json` | Before source selection | Source release commit | Per-run preparation performance measurements and thresholds |
| `scope-audit.md` | Before source selection | Source release commit | Human confirmation of the feature boundary and prohibited changes |
| `source-release-gates.json` | Immediately before source selection | Source release commit | Canonical aggregate of all source-only gates; it contains no not-yet-built artifact claims |
| `source-release.json` | After the source release commit exists | Candidate-artifact commit | Exact source commit, tree, archive, and `SOURCE_DATE_EPOCH` identities |
| `artifact-verification.json` | After deterministic artifacts exist | Candidate-artifact commit | Local artifact, core-install, formats-install, and production-boundary results for the chosen bytes |
| `second-machine-candidate-verification.json` | After the candidate-artifact commit exists | Certification commit | Exact candidate commit and artifact bytes verified on the second machine without rebuilding; this evidence is an input to the receipt |
| `release-certification.json` | After the certification commit and tag exist remotely | Post-certification evidence commit | Second-machine verification of the tagged receipt and unchanged artifact bytes, plus the already-existing source, candidate, certification, tag, and remote identities |

No evidence record contains its own future commit identity. The release receipt
may name and hash evidence that exists before the certification commit; it
cannot claim the later post-certification verification. The post-certification
record verifies the final receipt instead and is committed without moving the
release tag or changing any file under `dist/5.0.0/`.

## Release receipt schema

`release-receipt.json` is RFC 8785 canonical JSON under the separate strict
contract `isanlp_rst.release_receipt` 1.0.0. It is not an ingest outcome under
`isanlp_rst.production`.

### Contract identity

- receipt schema name and version;
- package name and 5.0.0 version;
- public contract name, 2.0.0 write version, and readable versions.

### Source identity

- VCS type;
- full source commit and tree identity;
- source state `clean`;
- source archive identity;
- commit-derived `SOURCE_DATE_EPOCH`.

Dirty source is never incorporated into a promoted artifact. The source-state
field remains required so the receipt makes this guarantee explicit rather
than inferred.

### Build identity

- Python implementation and full version;
- Python 3.14 `build-details.json` facts when available;
- build frontend and version;
- build backend and version;
- platform identity;
- production lock-file SHA-256;
- relevant deterministic-build environment values.

The receipt records environment facts that explain produced bytes; it does not
dump arbitrary environment variables.

### Artifact identity

For each wheel and sdist:

- filename and kind;
- byte size;
- SHA-256;
- wheel tags when applicable;
- build-report identity;
- package name/version extracted from artifact metadata.

The detached `release-receipt.sha256` covers the canonical receipt bytes. Wheel
`RECORD` hashes the wheel's internal files and is verified independently; it
does not replace this external artifact identity.

### Verification evidence

For every release gate:

- stable check identifier;
- pass/fail status;
- exact command;
- tool/runtime identity;
- evidence-output SHA-256;
- completion timestamp.

Required checks include lint, strict type check, Markdown lint, full pytest,
Feature 004 conformance, deterministic mutation tests, performance, artifact
validation, core clean install, formats clean install, production boundary, and
second-machine verification. A failed required check prevents promotion.

## Packaged build provenance

The build tool deterministically injects a read-only
`isanlp_rst/build-provenance.json` resource into each isolated build root. It
contains package/contract version, source commit/tree, source archive identity,
build-input identity, and build-tool identity. The same canonical resource
bytes are used in both independent builds and recorded by digest in the
external receipt. Runtime provenance reads this package resource; it never
invokes Git or assumes a checkout exists.

The packaged resource deliberately excludes the final wheel/sdist hashes,
which cannot be embedded in an artifact without self-reference. The external
receipt records those hashes and all post-build verification. Overlapping
source and build fields must match.

## Artifact validation

Validation must prove:

1. all four expected tracked files exist and no unexpected promoted file is
   present;
2. detached receipt digest matches canonical receipt bytes;
3. artifact sizes and hashes match the receipt;
4. wheel filename, `METADATA`, runtime, packaged provenance, and receipt agree
   on package version;
5. wheel tags and Python requirement are supported;
6. wheel `RECORD` contains SHA-256-or-better hashes for required entries and all
   entries verify;
7. wheel and sdist contain the expected production modules, schemas, manifest,
   `py.typed`, and provenance;
8. neither artifact contains forbidden offline/research content or model
   weights;
9. the source commit and tree exist and correspond to the recorded archive;
10. required verification records are present and passed.
11. the installed console entry point, its declared commands, and any retained
    local-HTTP capability match the public-surface inventory and define no
    independent result schema.

## Clean-install conformance

Create two isolated environments without `--system-site-packages`:

### Core environment

- install the exact tracked wheel by path;
- do not install the `formats` extra;
- run with `python -I` from a temporary directory;
- prove imported module paths are outside the checkout;
- verify package/provenance/receipt equality;
- import every supported core public symbol;
- run public-surface and schema reconciliation;
- query capabilities offline and see unavailable optional forms;
- serialize/load capabilities, outcomes, and failures;
- run the installed CLI and any retained loopback adapter against equivalent
  Python requests, require canonical semantic-byte parity and one inference
  execution, and reject raw exception-string or count-only substitutes;
- verify the typed analysis policy, exact analysed substrate, decision-complete
  evidence, composite identity, both-endpoint anchors, recombination receipt,
  and validation receipt using installed public imports only;
- prove forbidden raw tensors, embeddings, activations, unrestricted charts,
  training-only fields, and workbench types are absent from the public surface;
- attempt an unavailable format and receive typed provider unavailability;
- run `python -m pip check` and retain `python -m pip inspect` JSON evidence.

### Formats environment

- install the same tracked wheel plus its `formats` extra dependencies;
- repeat identity and checkout-exclusion proof;
- query capabilities and see all supported source forms available;
- run one conformance fixture for each form and rich retained-content
  round-trip;
- run one decision-complete primary analysis and one eRST analysis, including
  marker refinement, signal/candidate links, decoder receipt, and normalized
  distribution policy when the selected backend supports it;
- run subdivided analysis and verify complete local-to-global recombination
  mappings plus the validation receipt;
- run deliberate evidence-loss fixtures for every packaged production backend
  and handoff;
- route each supported structured source form through the installed CLI and
  shared `SourceArtifact` boundary;
- run `pip check` and retain `pip inspect` evidence.

Network access is allowed only for dependency installation when packages are
not already available locally. Acceptance runs execute with network access
disabled and must not load or download a model for capability checks.

## Second-machine acceptance

Second-machine proof has two distinct stages.

### Candidate verification before certification

On another supported development machine:

1. check out the untagged candidate-artifact commit;
2. verify the exact committed wheel and sdist hashes;
3. create an isolated Python 3.14 environment;
4. install `dist/5.0.0/isanlp_rst-5.0.0-py3-none-any.whl` directly;
5. run the installed contract conformance entry point without rebuilding; and
6. return canonical `second-machine-candidate-verification.json` evidence for
   inclusion by digest in the release receipt and certification commit.

### Tagged-release verification after certification

After the certification commit and release tag exist on the remote, the second
machine:

1. fetches and checks out the release tag;
2. verifies the detached receipt, every artifact hash, and every evidence digest
   named by the receipt;
3. installs the exact tagged wheel in a fresh isolated environment;
4. runs installed conformance and the complete quickstart without rebuilding;
5. confirms the tag resolves to the certification commit and the remote source,
   candidate, and certification identities are the expected identities; and
6. returns canonical `release-certification.json` for a separate
   post-certification evidence commit.

Success requires the exact committed wheel at both stages. Rebuilding locally
is not an acceptable substitute. The post-certification evidence commit does
not move the release tag and does not alter the certified artifact or receipt
bytes.

## Release immutability

After promotion:

- the bytes under `dist/5.0.0/` do not change;
- any code or public-contract change uses a new SemVer release;
- any incompatible change uses a new major package version;
- an artifact with different bytes never reuses the same filename/version;
- release verification reports observed bytes and revisions rather than
  inferring them from Git tags or file names.

Hosted attestations and signing are not required for this solo local release.
If publication to a package index is requested later, PEP 740/Sigstore
provenance is evaluated as a separate release feature.

# Verification, 2026-09-12

## Authorized normal-environment cutover

The user authorized advancing CSM's normal dependency and RST lock after the initial
candidate-only delivery. `pixi install` succeeded in CSM's default environment.
The selected wheel is `RDAM/dist/concept-cutover/rdam-6.0.0-py3-none-any.whl`.
Its SHA-256 is `832f5c713406c9071fc7144650fa4e56c57f55c3c0a7d1f52a76f4c57aa2a6de`;
the source archive SHA-256 is `28be398e1225bcb1bf3e2b8461bcd29ca55a4186715edb1b7e66da42ce9ffae5`.
Two independent builds through the source archive produced identical artifact bytes.

Embedded provenance identifies the real isolated Git snapshot
`4661808d4c39e6030a4fa504dc7356facbfc59b8`, retained in
`RDAM/dist/concept-cutover-source`. This snapshot commit is local build input;
neither working branch was committed, pushed or tagged. All runtime wheel files were
compared byte-for-byte with the current RDAM checkout and matched.

The existing DMRST model passed actual Docling JSON, Markdown and DocLang analyses,
canonical serialization round trips and source-locator reconciliation. The compatibility
probe preserved protected state. Normal installed-provider dynamic preflight returned
`status: pass`; model and capability semantic identities remain unchanged.
Historical methodology evidence is not rewritten or certified by this lock update.

Normal CSM lint passed. Strict typing: zero errors and warnings. Formatting passed
(303 files). An API-wiki fixture expectation omitted an existing retained source;
the repaired test now requires all existing unextracted sources to remain pending.
Its focused rerun passed all four tests. Source plates and authored wiki have no Git changes.

Strict normal-environment corpus CI ran against the original source locations:
**92 errors, 73 warnings, exit 1**. Reported errors identify historical RST evidence
created under a different provider lock. Warnings include missing authored coverage
reviews and unlinked aliases. The extractor regenerated only the derived build
(47 nodes, five roots, maximum depth two); validation used `--no-write`.
No source/wiki publication, corpus migration or historical evidence rewrite occurred.
See `csm-cutover-ci.log`; the old validation JSON is not this run's report.

Final normal-environment full suite: **1141 passed, one failed, 22 skipped, one
warning in 573.19s**. The only failure was the metadata fixture expectation repaired
during that run; its complete module rerun returned **4 passed**. The full suite was
not rerun after that test-only repair. The 22 skipped checks require paid provider
adoption opt-in; the warning is the upstream Google GenAI Python 3.14 deprecation.
All RST provider/compatibility/plate, concept authoring/retrieval, schema and installed
CLI tests passed. Final lint and format checks passed; graph AST refresh completed.
The cutover is verified; corpus CI remains failed as reported above.

## Initial candidate verification (historical)

This records actual local execution, not a release certificate or remote CI claim.
Existing Feature 020 and concurrent CSM Feature 014 changes remain uncommitted.

## Shared implementation

- Final focused RDAM run: **35 passed in 20.42s** (22 concept tests plus public-surface,
  persisted-schema and mutation-site regression checks).
- Python/CLI/actual HTTP requests produce identical semantic bytes; all six source
  forms, Unicode normalization, synonyms, ambiguity, repeated/overlapping occurrences,
  unknown supplied candidates and stale source/ontology evidence are exercised.
- Fresh-process linking rejects attempted network connections and confirms no PyTorch
  or Transformers import. Source ingestion is invoked once by the convenience API.
- Native-analysis consumer proof serializes a real SDRT provider result using its
  FunctionModel test boundary, reloads it, and joins original inventory evidence.
- Ruff and modern production Ruff: all checks passed. Strict typing: zero errors,
  zero warnings. Markdown checks: 284 files, zero issues at the recorded run.
- Production boundary: valid=true, 183 production modules scanned, no violations.
- All 66 installed schemas and generated public-surface authority match their generators.
- The first broad run produced 3105 passed and three failures. These identified the
  schema inventory/test expectation and moved Markdown mutation target; all were
  repaired and their focused checks passed. A final full rerun is recorded below.

## Downstream and evaluation

- Final actual installed candidate in a fresh CSM Pixi environment: **57 passed in
  39.70s**, including Docling, DocLang and rich Markdown plate reconciliation,
  typed reviewed authoring, XML/build/retrieval persistence, stale-evidence rejection,
  old-card reading, schema documentation, and cached task inputs.
- CSM's whole candidate-environment suite: **1071 passed, 26 failed, 32 errors,
  22 skipped, one warning in 148.09s**. Detailed output is in CSM's feature folder.
  Most failures/errors reject the candidate because its origin differs from the
  exact released RST wheel. One compatibility check loads the old wheel, which lacks
  rdam.concepts. A separate API-wiki draft test fails its window-refinement configuration.
  These are not represented as passing.
- Final CSM strict typing passed; full lint/format results are tracked in CSM's report
  because concurrent Feature 014 edits continued during checks.
- AST graph refreshes completed in both repositories. Graphify reported its existing
  0.9.54-skill/0.9.53-package mismatch and changed community labels; no paid relabeling ran.
- Docling NLP 1.4.0 installation and extraction ran in the isolated experiment. Frozen
  gold, exact occurrence outputs, model hashes, offset proof, timings, memory and the
  measured no-adoption recommendation are in workbench/experiments/concept_linking.

## Local artifacts and delivery limit

The wheel and source archive were built locally; no commit, push, tag, live corpus
publication, model download for linking, or ontology edit was performed.

- `dist/concept-candidate/rdam-6.0.0-py3-none-any.whl`: SHA-256 `b8ea62e322bc069915cde9fe5d063cf63d5bf91d099ee031351f82b9dab1338c`.
- `dist/concept-candidate/rdam-6.0.0.tar.gz`: SHA-256 `08751284abfedfa12eeab6c38cbdeb55edabda6560cc6138d46bebed9676c698`.

The installed proof reports site-packages/rdam and direct_url.json pointing to this
candidate wheel. CSM's normal environment and exact RST lock still select the old
release. The new CSM source checkout needs the candidate environment until the normal
RDAM dependency is advanced; default-environment cutover has not been completed.
The generator `CSM/tools/concept_candidate.py` makes that isolated proof reproducible.

Upstream currency gap: DocLang 0.7.3 matches the installed contract. Docling Core 2.96.0
was current upstream, while RDAM remains at 2.94.1 and CSM at 2.92. Production dependency
constraints were preserved as requested; no claim of current Docling spec parity is made.

## Full rerun and corpus gate

Final full RDAM fast suite: **3110 passed, 197 deselected, one warning in 422.43s**.
The warning is Google GenAI’s Python 3.14 `_UnionGenericAlias` deprecation; it was not
suppressed. Full output is saved as rdam-concepts-fast-final.log.
The installed-source import check also returned valid=true; it is explicitly an
editable-source check, separate from the verified installed candidate wheel.

Strict corpus-copy validation returned **92 errors and 73 warnings**, exit 1.
Reported errors include source-identity mismatches in historical RST records after
relocating the source directory. Warnings include missing authored coverage reviews
and unlinked aliases. This is a failed copied-corpus gate, not a claim that the live
corpus is unchanged and failing for identical causes. The full CLI summary is in
csm-corpus-ci.log. No report was written because --no-write was used.

CSM full strict typing: 0 errors, 0 warnings. Full formatting: 302 files already formatted.
A 121-character string in concurrently edited api_wiki/meta.py was split without changing
its output to repair the final lint defect encountered during this task.

Later repository-wide CSM lint/format checks encountered new edits in
src/csm/api_wiki/revision.py while Feature 014 work was ongoing (including an undefined
require_current_coverage reference in that transient snapshot). The earlier clean
strict-type/format observations do not certify the later changing tree. The concept
implementation's focused lint check passed. Full cross-repository acceptance remains
open; these parallel edits are not rewritten by this feature.

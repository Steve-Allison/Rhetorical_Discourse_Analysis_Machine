# Forensic code review — `isanlp_rst`

Review date: 2026-08-24  
Reviewed commit: `4ae828d44cbd3d3b80edbf7e7fcacc0fa13f08e0`  
Branch: `codex/spec-kit-adoption`  
Mode: report-only; production code, tests, configuration, and documentation were not edited

## Executive verdict

The core parser façade and all five published model variants work on both CPU and
MPS in the reviewed environment. The full test suite also passes. Those green
results do **not** establish that every published contract is trustworthy.

The review confirmed four P1 integrity defects:

1. Docling, DocLang, and Markdown projections manufacture empty text, zero
   character spans, and non-ordinal EDU spans. The resulting typed analyses are
   structurally valid but semantically false.
2. The DocLang harvester sends current-spec `description` and `summary`
   element-head metadata into the RST model as document prose or code.
3. `Parser.parse_document()` persists package version `1.0.0` even though the
   installed package is `3.2.0`.
4. The eRST training path silently drops malformed source documents and splits
   candidates rather than documents. In the repository's own fixture corpus,
   `GUM_news_sensitive.rs4` occurs on both sides of the 80/20 train/dev split.

There are also five P2 defects: opt-in DocLang code/formula spans disappear from
page/group membership, 44.3% of production Python is excluded from typechecking,
the Python 3.14 environment reaches unsupported and vulnerable TorchScript code,
the eRST “end boundary” is actually `[SEP]`, and package import globally suppresses
warnings. Lower-severity findings concern Markdown-check coverage, the vulnerable
setuptools build backend, and DocLang fixture/documentation drift.

No P0 issue was found. No source remediation was performed.

## Severity model

- **P0** — immediate destructive, remote-compromise, or unrecoverable-data risk.
- **P1** — output, evidence, evaluation, or provenance can be materially false.
- **P2** — important reliability, compatibility, or verification weakness.
- **P3** — bounded hardening, scope, documentation, or toolchain defect.

## Findings summary

| ID | Priority | Finding | Status |
|---|---:|---|---|
| F-01 | P1 | Format-native projections emit false RST coordinates and empty content | Confirmed by runtime reproduction |
| F-02 | P1 | Current-valid DocLang element-head metadata contaminates model input | Confirmed against current fixture/spec |
| F-03 | P1 | Parser provenance persists the wrong software version | Confirmed by real model parse |
| F-04 | P1 | eRST corpus ingestion hides failures and leaks a document across train/dev | Confirmed on repository fixtures |
| F-05 | P2 | DocLang page/group memberships ignore code/formula opt-in flags | Confirmed by synthetic valid input |
| F-06 | P2 | Typecheck excludes 44.3% of production Python and hides 338 errors | Confirmed by independent Pyright run |
| F-07 | P2 | Python 3.14 reaches unsupported TorchScript in a vulnerable torch lock | Confirmed by targeted test and audit |
| F-08 | P2 | eRST span encoder uses `[SEP]` as its lexical end boundary | Confirmed with the configured tokenizer |
| F-09 | P2 | Package import globally suppresses actionable warnings/logging | Confirmed statically |
| F-10 | P3 | Green Markdown task checks only 3 of 84 tracked Markdown files | Confirmed by full-corpus lint |
| F-11 | P3 | The active setuptools build backend has a known macOS sdist flaw | Confirmed by dependency audit |
| F-12 | P3 | DocLang fixtures and prose lag the current `.dclg` contract | Confirmed against upstream |

## Detailed findings

### F-01 — Format-native projections emit false coordinates and empty content (P1)

Affected code:

- `isanlp_rst/docling/schema.py:156-291`
- `isanlp_rst/doclang/schema.py:175-310`
- `isanlp_rst/markdown/schema.py:170-305`
- `tests/test_format_projections.py:28-173`

All three `to_format_analysis()` implementations apply the same projection:

- every EDU receives `edu_span=(edu.id, edu.id)`;
- every node receives `char_span=(0, 0)` and `text=""`;
- every relation span is derived from its two child **node IDs** rather than
  descendant EDU ordinals.

Flattened IDs share one pre-order namespace across internal nodes and leaves.
They are therefore not contiguous EDU indexes. A three-EDU nested tree reproduced:

```text
[(1, 'edu', (1, 1), (0, 0), ''),
 (3, 'edu', (3, 3), (0, 0), ''),
 (4, 'edu', (4, 4), (0, 0), ''),
 (0, 'span', (1, 2), (0, 0), ''),
 (2, 'multinuclear_group', (3, 4), (0, 0), '')]
actual_edus=3 parseval_inferred_num_edus=4
```

This is not cosmetic. `StandardParsevalScorer` infers document EDU count from
the maximum projected EDU span; `SoftParsevalScorer` uses character spans;
eRST candidate features consume node text and both coordinate systems; and the
hierarchical stitcher treats these values as real offsets. The existing tests
assert only node/edge counts and reference maps, so the false semantics pass.

Recommended remediation:

1. Define one shared projection implementation rather than three copies.
2. Carry or supply harvested text/offset evidence to the projection boundary.
3. Assign leaves contiguous document EDU ordinals and derive every internal
   span from descendant leaves.
4. Preserve source text and half-open character coordinates for every node.
5. Add nested-tree contract tests plus Parseval, eRST-feature, and hierarchical
   consumer tests. Bump the repository's own schema version only if its
   serialized result shape changes.

### F-02 — Current-valid DocLang element-head metadata contaminates model input (P1)

Affected code:

- `isanlp_rst/doclang/harvester.py:63-76`
- `isanlp_rst/doclang/harvester.py:120-140`
- `tests/test_doclang_harvester.py:321-335`

The current DocLang element head includes `description` and `summary`, after
`caption`. `_HEAD_LOCALS` omits both. `_prose_itertext()` consequently emits
their text as body text. Other collection paths use broad `itertext()` and have
the same semantic risk for nested content.

The repository's current valid fixture
`tests/fixtures/doclang/ok_description_element_head.dclg.xml` reproduced:

```text
/doclang[1]/text[1]
  'The authors describe ... Overview of the experimental methodology. ...
   The full paragraph text follows here.'
/doclang[1]/code[1]
  'Prints a greeting to standard output. ... def main(): ...'
```

The first two passages are metadata, not body text. They change segmentation,
model input, coordinates, relations, and cached results for valid current
DocLang documents. Existing tests cover `layer` and `location` but do not assert
that `description` and `summary` are excluded.

Recommended remediation: update the element-head model from the current spec,
filter head children recursively in every prose/list/table/code/formula path,
and add positive body plus negative metadata assertions using the existing
fixture.

Current authority: [DocLang specification](https://github.com/doclang-project/doclang/blob/main/spec.md).

### F-03 — Parser provenance persists the wrong software version (P1)

Affected code:

- `isanlp_rst/contracts/document.py:62-75`
- `isanlp_rst/parser.py:267-273`
- `pyproject.toml:6-8`

`ProvenanceRecord` defaults to `1.0.0`, and `Parser.parse_document()` explicitly
hardcodes the same value. A real cached-model parse produced:

```text
installed_package_version 3.2.0
persisted_software_version 1.0.0
producer isanlp_rst.parser
```

This makes persisted results and evidence receipts claim the wrong producer
version. It also prevents reliable comparison, cache forensics, and regression
attribution between releases.

Recommended remediation: derive one package version from installed metadata
with an explicit source-checkout fallback, inject it at the provenance boundary,
and add an integration assertion against `importlib.metadata.version()`.
Ontology versioning is a separate authority and should not be conflated with
the software version.

### F-04 — eRST ingestion hides failures and leaks a document across train/dev (P1)

Affected code:

- `isanlp_rst/erst/dataset.py:201-220`
- `scripts/train_erst_scorer.py:69-89`

`load_gum_erst_corpus()` catches four broad exception classes per RS4 file and
continues without naming the rejected file or returning a receipt. Training
then concatenates all candidates and slices them at 80%, rather than splitting
by document.

The current ten-fixture corpus yields 254 candidates. The split index is 203;
`GUM_news_sensitive.rs4` occupies indexes 186-206, so candidates from the same
source document occur in both train and dev. Dev F1 is therefore not an honest
held-out-document measure. Because malformed files vanish silently, neither
the candidate count nor corpus coverage proves what was actually trained.

Recommended remediation:

1. Return a typed ingestion receipt containing accepted/rejected documents and
   fail closed by default on parse/conversion failures.
2. Split deterministic document IDs first, then generate/flatten candidates.
3. Persist the exact split, seed, source fingerprints, and per-document counts.
4. Add a test that train/dev document sets are disjoint and a test that a
   malformed source cannot disappear silently.

### F-05 — DocLang page/group memberships ignore code/formula opt-ins (P2)

Affected code:

- `isanlp_rst/doclang/boundaries.py:156-230`
- `isanlp_rst/doclang/boundaries.py:355-374`
- `tests/test_doclang_boundaries.py:213-220`

`detect_boundaries()` passes `include_code_blocks` and `include_formulas` to
heading and document-fallback detection, but not to page or group detection.
Group detection calls `_harvest_eligible_xpaths()` with default flags; page
detection has a separate hardcoded tag list.

Reproduction with opted-in `<code>alpha</code>` and `<formula>beta</formula>`:

```text
harvested [('/doclang[1]/group[1]/code[1]', 'alpha'),
           ('/doclang[1]/formula[1]', 'beta')]
boundaries [('page-0', 'page', ()),
            ('page-1', 'page', ()),
            ('group-0', 'group', ())]
```

The RST input contains the spans, but boundary membership evidence says it does
not. Recommended remediation: route every boundary detector through one
eligibility policy carrying all harvest knobs, and add page/group tests—not
only a direct helper test.

### F-06 — Typecheck excludes 44.3% of production Python and hides 338 errors (P2)

Affected code:

- `pyproject.toml:113-132`
- `isanlp_rst/dmrst_parser/src/**`
- `isanlp_rst/universal_parser/src/**`

The default `pixi run typecheck` reports zero errors and warnings, but Pyright
explicitly excludes both parser implementation trees. They contain 13,317 of
30,088 production Python lines (44.3%). Running the same Pyright 1.1.411 and
Python 3.14 environment independently over those directories analyzed 36 files
and reported **338 errors**. Representative errors include arithmetic and
subscription on possible `None`, dereferencing attributes on `None`, and
incompatible collection types.

This is a verification-honesty defect: the green task is described as the
project typecheck while omitting nearly half the product. Recommended
remediation: remove the exclusions, establish an explicit measured baseline,
repair underlying types without suppressions, and keep the check fail-closed.

### F-07 — Python 3.14 reaches unsupported TorchScript in a vulnerable lock (P2)

Affected evidence:

- `pyproject.toml:23-42`
- `isanlp_rst/erst/neural_scorer.py:67-112`
- `tests/test_neural_erst.py:190-218`
- locked torch `2.11.0`

The full suite passes but emits seven warnings that `torch.jit.script` is not
supported on Python 3.14+ and may break. Treating deprecations as errors makes
the neural eRST scorer fail while Transformers imports DeBERTa at its
`@torch.jit.script` decorator. The command reported a pytest failure and process
exit 139; the normal targeted test passes with nine warnings.

`pip-audit` also identifies torch 2.11.0 as affected by
[GHSA-rrmf-rvhw-rf47](https://github.com/advisories/GHSA-rrmf-rvhw-rf47), fixed
in 2.13.0. The advisory is local and low-CVSS, so this is not presented as a
remote compromise. It matters here because the actual configured model path
executes `torch.jit.script` during import.

Recommended remediation: resolve a tested Python 3.14-compatible
torch/Transformers combination that no longer reaches unsupported TorchScript,
update the lock, run the neural eRST tests with deprecations as errors, and
repeat full CPU/MPS model validation.

### F-08 — eRST span encoder uses `[SEP]` as its lexical end boundary (P2)

Affected code:

- `isanlp_rst/erst/neural_scorer.py:40-57`
- `tests/test_neural_erst.py:190-218`

The method says it extracts first and last non-special tokens. Start index 1
does skip `[CLS]`, but `attention_mask.sum() - 1` points at the final
non-padding token, which for the configured DeBERTa tokenizer is `[SEP]`:

```text
tokens ['[CLS]', '▁Alpha', '▁beta', '.', '[SEP]']
selected_start_index 1 token ▁Alpha
selected_end_index 4 token [SEP]
```

The learned “boundary-aware” vector therefore receives a constant special-token
position instead of the last lexical/subword boundary. Existing tests verify
only output keys, shapes, and positive loss.

Recommended remediation: derive lexical boundaries from tokenizer special-token
masks or offset mappings, add exact-index tests for padded/unpadded sequences,
and assess checkpoint compatibility before changing trained inference maths.

### F-09 — Package import globally suppresses warnings and logging (P2)

Affected code: `isanlp_rst/__init__.py:60-75`.

Importing the package sets the Transformers logger to `ERROR` and installs two
process-global warning filters. One hides LSTM dropout configuration warnings;
the other hides embedding-initialization warnings. This changes host-process
behavior merely by importing a library and can conceal configuration or model
loading defects from this project and callers.

Recommended remediation: remove process-global filters and logger mutation,
correct originating configuration where it is under project control, and let
applications choose their own logging policy.

### F-10 — Green Markdown task checks only 3 of 84 tracked files (P3)

Affected code: `pyproject.toml:134-147`.

`pixi run mdlint` passes because it checks only `README.md`,
`UniRST_Metrics.md`, and `CLAUDE.md`. Running the same linter over all 84 tracked
Markdown files reports 180 issues in 33 files. A large share is duplicated
Spec Kit projections or fixture Markdown, but first-party plan/memory/test docs
also fail.

Recommended remediation: define intentional generated/fixture exclusions and
lint every remaining authoritative Markdown file. Name the narrow task
accurately if it is intentionally retained.

### F-11 — Active setuptools build backend has a known macOS sdist flaw (P3)

Affected code: `pyproject.toml:1-3`; installed setuptools `81.0.0`.

The project builds with setuptools and the locked environment contains 81.0.0.
`pip-audit` reports
[GHSA-h35f-9h28-mq5c](https://github.com/advisories/GHSA-h35f-9h28-mq5c), fixed
in 83.0.0: Unicode-normalization mismatches on macOS can bypass certain
`MANIFEST.in` exclusions during sdist creation. This repository has no tracked
`MANIFEST.in`, so present exploitability is limited; the vulnerable tool is
nevertheless the active backend on the target filesystem.

Recommended remediation: require and lock setuptools 83.0.0 or newer, then
build and inspect wheel/sdist contents in a temporary publication candidate.

### F-12 — DocLang fixtures and prose lag the current `.dclg` contract (P3)

The installed and latest DocLang package is 0.7.3 and the current spec is 0.7.
Upstream currently carries 42 valid `.dclg` fixtures. This repository mirrors
the 42 basenames but stores them as `.dclg.xml`; loader prose still mentions
“verified 40” while other package prose says 42. All 42 local fixtures validate
under the installed package when the no-namespace fixture is handled with the
intended option; the content is therefore substantially current, but naming and
documentation are not.

Recommended remediation: mirror upstream extension/names exactly and derive
fixture-count assertions rather than embedding prose counts.

Current authorities: [DocLang on PyPI](https://pypi.org/project/doclang/) and
[upstream valid fixtures](https://github.com/doclang-project/doclang/tree/main/tests/data/valid).

## Upstream contract and dependency currency

### Docling

- Locked `docling-core`: 2.91.0.
- Latest on review date: 2.92.0 ([PyPI](https://pypi.org/project/docling-core/)).
- Four local `DoclingDocument` 1.10.0 fixtures loaded successfully under both
  2.91.0 and an ephemeral 2.92.0 environment, with identical canonical item
  counts: 54, 603, 28, and 37.
- Current `iterate_items()` shape and `ContentLayer` filtering remain compatible
  with the harvester.

Conclusion: one patch release behind, with no demonstrated contract break.

### DocLang

- Locked and latest `doclang`: 0.7.3.
- `doclang[schematron-saxon]` support is directly installed as required.
- The current spec's element-head additions expose F-02; package/validator
  currency itself is otherwise good.
- Upstream result versions and this repository's own `schema_version` are
  separate contracts; no upstream package bump alone justifies changing the
  repository result envelope version.

## Graph and architecture evidence

Graphify was rerun with the ignored `.env` `GOOGLE_API_KEY` and the Gemini deep
semantic backend. No secret value was printed or persisted in the report.

Final directed graph:

- 3,315 nodes
- 7,410 directed edges
- 149 reported communities (148 unique non-null names in final `graph.json`)
- 4 hyperedges
- 224,591 semantic input tokens and 7,353 semantic output tokens
- zero missing endpoints, dangling endpoints, self-loops, or exact duplicate
  directed edges in the post-build health check

Highest-connectivity nodes are `Parser` (108 edges), `RstAnalysis` (85),
`parse_doclang()` (56), `parse_markdown()` (55), `parse_docling()` (55), and
`BasePredictor` (50). No import cycle was detected. This supports the review's
focus on the parser façade, typed contracts, and three format entry points.

Limitations: the semantic stage dispatched 93 files; 65 produced no semantic
nodes, and 18 out-of-scope or misattributed nodes were dropped. AST-derived
structure remains present, but the graph is navigation evidence, not proof of
runtime wiring. The installed Graphify package is 0.9.44 while its skill is
0.9.45; no unrequested tool upgrade was performed.

Artifacts:

- `graphify-out/GRAPH_REPORT.md`
- `graphify-out/graph.html`
- `graphify-out/graph.json`

## Verification ledger

| Check | Result |
|---|---|
| `pixi install --locked` | Passed |
| `pixi run lint` | Passed |
| `pixi run typecheck` | Passed, but excludes 44.3% of production LOC (F-06) |
| Independent excluded-tree Pyright | 36 files, 338 errors, 0 warnings |
| `pixi run mdlint` | Passed, but checks only 3/84 Markdown files (F-10) |
| Full tracked-Markdown lint | Failed: 180 issues in 33/84 files |
| `pixi run test` | 676 passed, 73 deselected, 4 warnings in 13.62 s |
| `pixi run test-all` | 749 passed, 11 warnings in 506.66 s |
| `pixi run smoke-full` | Passed: all five model variants on CPU |
| `pixi run smoke-full-mps` | Passed: all five model variants on MPS |
| Neural eRST test, normal warnings | Passed: 1 test, 9 warnings |
| Neural eRST test, deprecations as errors | Failed at Python 3.14 TorchScript; process exit 139 |
| `pip-audit` over Pixi environment | Failed: torch and setuptools advisories; `isanlp` unaudited because not on PyPI |
| Current tracked secret-pattern scan | No matches |
| Git-history secret path/name scan | No suspicious paths/names; historical blob contents were not exhaustively audited |
| `.env` Git state | Ignored by `.gitignore`; never tracked in available history |

Passing parser smokes prove the core current runtime path, not the structured
projection, DocLang metadata, training-evaluation, or provenance claims covered
by the P1 findings.

## Recommended remediation order

1. Repair F-01 and add downstream semantic contract tests before trusting any
   `FormatRstAnalysis` output.
2. Repair F-02 and F-05 together against the current DocLang spec; invalidate
   caches generated with contaminated harvests.
3. Correct F-03 and explicitly identify/rebuild evidence carrying false 1.0.0
   provenance where provenance matters.
4. Redesign F-04 around document-level split receipts before making further
   eRST performance claims.
5. Resolve F-07 and F-08 together, with checkpoint-compatibility evidence and
   fresh CPU/MPS neural-eRST verification.
6. Remove warning suppression and expand type/Markdown gates.
7. Update audited build/runtime dependencies and refresh DocLang fixture naming.

## Review coverage and limits

Files read in full before relying on them included:

- governance: `AGENTS.md`, `CLAUDE.md`, `.claude/rules/architecture.md`,
  `.claude/rules/code-standards.md`, `.claude/rules/commands.md`, and
  `.claude/rules/no-assumptions.md`;
- project/build: `pyproject.toml`, `.gitignore`, `.gitattributes`, licences,
  the three GitHub workflows, root/cleanup utilities, `scripts/smoke_test.py`,
  and `scripts/train_erst_scorer.py`;
- core: `isanlp_rst/__init__.py`, `parser.py`, `base_predictor.py`, and the
  contract modules;
- structured formats: the complete Docling and DocLang entry, loader/harvester,
  boundary, mapper, schema, error, MIME, and package-init modules, plus the
  Markdown schema;
- downstream paths: `eval/parseval.py`, `erst/dataset.py`,
  `erst/neural_scorer.py`, `english/erst/completer.py`, and the hierarchical
  stitcher;
- focused tests: DocLang harvester/boundary tests, all format-projection tests,
  neural eRST tests, and the relevant current DocLang fixtures;
- generated evidence: `graphify-out/GRAPH_REPORT.md` and the pip-audit result.

The remaining corpus was covered through directed Graphify extraction, full
test execution, Ruff/Pyright/Markdown/security scans, Git history inspection,
and targeted searches. It was not represented as 182 production Python files
all read line-by-line by a human reviewer. CUDA behavior was not verified
because the reviewed Apple Silicon machine has no NVIDIA device. External
GitHub scheduled-run history was not inspected; workflow definitions and local
equivalent commands were inspected and exercised.

## Git and mutation statement

The review began at clean tracked commit
`4ae828d44cbd3d3b80edbf7e7fcacc0fa13f08e0`. Only the authorised
`graphify-out/**` artifacts and this report were created. No production source,
test, configuration, documentation, commit, remote branch, or external system
was changed.

## 4.0.0 remediation closure — 2026-08-24

The original report above remains the before-state. Its exact original form and
the original Graphify evidence are preserved by commit `f47507d`. This section
records the authorised remediation outcome. The release decision is fail-closed:
the corrected 4.0.0 interfaces and reproduced current baseline capability may
ship, but no new canonical eRST checkpoint, benchmark result, public weight,
private Hugging Face upload, or SOTA claim exists.

### Finding closure matrix

| ID | Closure | Evidence / release disposition |
|---|---|---|
| F-01 | Closed | One shared projection computes exact source text, half-open character spans, one-based inclusive EDU spans, leaf order, and ancestor coverage for Docling 1.2, DocLang 1.1, and Markdown 1.1. Round-trip, hierarchy, Parseval, and downstream eRST tests pass. |
| F-02 | Closed | The single DocLang metadata-aware walker excludes `description` and `summary` heads at any depth while emitting eligible text and tails exactly once. Current fixture and nested text/tail regressions pass. |
| F-03 | Closed | Installed distribution metadata is the semantic package-version authority; source revision is separate. Clean installation reports both distribution and module version `4.0.0`. |
| F-04 | Closed | Pydantic corpus receipts/failures, official document partitions, source hashes, fail-closed loading, and document/hash-disjoint split validation replace silent flatten-and-split behaviour. Private corpus bytes and derived weights remain unpublished. |
| F-05 | Closed | One immutable DocLang eligibility policy governs harvest and document/page/group/heading/table/list/code/formula boundaries; the option matrix passes. |
| F-06 | Closed | Both formerly excluded parser trees are included. Full `pyright` reports `0 errors, 0 warnings, 0 informations`; no production ignore was introduced. |
| F-07 | Closed | The lock contains PyTorch 2.13.0 and setuptools 84.0.0. Python 3.14 warning-as-error full tests and all five CPU/MPS parser smokes pass; the dependency audit finds no known vulnerability. |
| F-08 | Closed | Fast-token offsets now supply lexical span ends rather than the special `[SEP]` position; padded and unpadded boundary regressions pass. |
| F-09 | Closed | Package-wide warning filters and Transformers logger mutation are removed. Production suppression scan is empty and `PYTHONWARNINGS=error` passes full tests and CPU/MPS smokes. |
| F-10 | Closed | A sorted manifest governs 63 tracked Markdown files. Exactly 35 generated Spec Kit projections and one intentional Markdown syntax fixture are excluded; all governed files lint with zero issues. |
| F-11 | Closed | The active build backend is setuptools 84.0.0. Fresh wheel/sdist creation, archive inspection, and dependency audit pass. |
| F-12 | Closed | All 42 DocLang fixtures use `.dclg`; immutable-upstream parity at commit `6d3b3d3c195d1f63333c5c5fcba8da17937a33bd` reports equal names and hashes, with counts derived at runtime. |
| N-01 | Closed | Normalized source basename is part of result-cache identity; equal bytes under two names miss and preserve the second basename. |
| N-02 | Closed | Envelope schema version is part of every result-cache key; pre-bump entries miss. |
| N-03 | Closed | One complete candidate generator serves train/dev/test/test2/inference. Candidate-identity tests cover every mode. |
| N-04 | Closed | Gold labels annotate but cannot create candidates; gold-shuffle invariance passes and hard-negative selection is train-only. |
| N-05 | Closed | The eRST decoder enforces only valid signal, no self-loop, no duplicate directed pair, and no invented node. Cyclic, non-projective, concurrent, reverse, and primary-overlap conformance tests pass. |
| N-06 | Closed | Typed signals retain type, subtype, overlapping token anchors, confidence, and detector provenance; validated discourse-marker and morphosyntactic trigger coverage replaces the phrase heuristic. |
| N-07 | Closed | Raw GUM eRST relations are preserved and projected separately through the ontology adapter; reversible raw/coarse tests pass. |
| N-08 | Closed | Missing corpus, malformed documents, zero candidates, zero steps, and absent checkpoints are typed errors with regression coverage. |
| N-09 | Closed | Complete safetensors bundles carry strict component/config/tokenizer/calibration/inventory/decoder state plus a hashed Pydantic manifest; save/reload parity passes. No promoted bundle exists. |
| N-10 | Closed | Parser argument is `erst_scorer_checkpoint`; an `erst_graph` request without a validated completion bundle raises an explicit capability error. |
| N-11 | Blocked, fail-closed | Exact GUM V9.2 authority is pinned, but the paper's claimed public official scorer cannot be resolved and released baseline code carries no stated code licence. Baseline-authority receipt SHA-256: `d97961ef5f9c7f524e5beaeb634d033476c866dcb4b442f966da6d6bf03dec0e`; reproduction-diagnosis SHA-256: `a9f5fc7ce5aadc0c094e0358c12d40b9ecd5b9e071e9213c8faaada5b3acf0b4`. No baseline run was started. |
| N-12 | Blocked, fail-closed | Because N-11 is a hard prerequisite, no mandatory architecture saw corpus/test data and no champion was selected. Research-diagnosis SHA-256: `2e9fa1bde74599b415f18aa464509905b57e72a696f9e205ae2fb46181ed75b9`; no-promotion decision SHA-256: `34270305f49e52a2d5155ecf4025f1f83d76ac13bb914cc6131a8fcd10872651`. |
| N-13 | Closed | Repository-root `.env` loading is explicit and non-logging. `HF_TOKEN` has precedence and `HUGGINGFACEHUB_API_TOKEN` is fallback; only operation-relevant values are loaded and secret values are never serialized. |
| N-14 | Closed | Runtime tokenizers use verified fast artifacts; compatibility/parity receipts and warning-as-error CPU/MPS paths pass. |
| N-15 | Closed | Fresh build, member inspection, isolated install, representative three-format/cache/import execution, five-parser CPU/MPS smokes, audit, and secret scans provide package and clean-machine proof. |

### Exact release-candidate evidence

| Gate | Command / observed result |
|---|---|
| Locked environment | `pixi install --locked` — passed in 0.03 s. Lock: Python 3.14, PyTorch 2.13.0, Transformers 5.15.1, setuptools 84.0.0, docling-core 2.92.0, DocLang 0.7.3. |
| Full tests | `PYTHONWARNINGS=error pixi run --no-config --locked test-all` — `907 passed in 460.47s`; process wall time 461.36 s. |
| Static quality | `pixi run --no-config --locked lint` — all checks passed. `pixi run --no-config --locked typecheck` — zero errors/warnings. Production suppression scan — zero matches. |
| Documentation | `python scripts/verify_markdown_manifest.py --lint` — 63 linted, 36 approved exclusions, zero issues. |
| Contract currency | `python scripts/verify_doclang_fixtures.py` — local/upstream 42, names and hashes equal. `pytest -q tests/test_version_compat.py tests/test_doclang_fixture_parity.py` — 94 passed. |
| Primary CPU runtime | `PYTHONWARNINGS=error pixi run --no-config --locked smoke-full` — all five variants and error/offset guards passed in 70.38 s. |
| Primary MPS runtime | `PYTHONWARNINGS=error pixi run --no-config --locked smoke-full-mps` — all five variants and error/offset guards passed in 63.61 s. |
| Build | Fresh build produced wheel SHA-256 `6639d499891b184b115144112faa72acaaf285674907c1e216a216567b3936fe` (150 members) and sdist SHA-256 `a49160f75eff53dbd9a0cceb6f8215e6b6d4cac0f1345ac2df67fd28786f3c1b` (253 members); forbidden-member count zero. |
| Clean install | Isolated Python 3.14.6 environment reports `4.0.0`; Docling 1.2, DocLang 1.1, Markdown 1.1 self-contained outputs, basename-sensitive cache provenance, and both corpus import graphs pass. |
| Dependency audit | `uvx pip-audit --path .pixi/envs/default/lib/python3.14/site-packages` — no known vulnerabilities. `isanlp` 0.0.7 (VCS) and local `isanlp-rst` 4.0.0 are explicitly unauditable via PyPI. |
| Secret audit | 682 tracked/staged files scanned. Structural credential/private-key patterns: zero. `detect-secrets` reports 1,468 entropy findings, all generated hashes/fingerprints, plus one intentional secret-keyword test proving non-disclosure. `.env` remains ignored and uncommitted. |
| Graph health | Directed Graphify graph: 4,620 nodes, 10,352 edges, 227 labeled communities; zero missing/dangling endpoints, self-loops, exact duplicates, or directed same-endpoint collapses; no import cycle detected. Graphify package 0.9.44 warned that its installed skill is 0.9.45, and 21 JSON/config sources emitted no AST nodes; neither condition created a structural defect. |

CUDA remains unverified because the release-candidate machine is an Apple M5
Max with MPS and no NVIDIA device. No CPU/MPS result is represented as CUDA
evidence. The exact public Git commit and remote branch equality are verified
after this closure record is committed; no report edits are made after the
final candidate validation.

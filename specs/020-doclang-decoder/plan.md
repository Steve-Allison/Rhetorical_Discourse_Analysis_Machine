# Implementation Plan: Consolidate DocLang decoding

**Date:** 2026-09-12. **Feature:** 020-doclang-decoder. **Status:** approved and implemented; final verification is recorded in [implementation-results.md](implementation-results.md).

**Planning checkout:** `master` at `74f7f3a11183abcd707bf7021a9604b966c1160f`. **Implementation branch:** `codex/020-doclang-decoder`. **Input:** [spec.md](spec.md).

## Summary

Replace the DocLang legacy conversion detour with a private native decoder and direct current-contract inventory mapping. Reuse the same RDAM-owned XML tree for archive checks, addressing and harvesting. Centralize mixed-content and table decoding, including private fragment resolution. Preserve official validation, source evidence and all seven native technique boundaries.

The design borrows separation of responsibilities from `docling-nlp`; it does not import that package or adopt its permissive archive reader. Source findings and upstream currency are recorded in [research.md](research.md). Proposed private types are in [data-model.md](data-model.md), preservation rules in [contracts/compatibility.md](contracts/compatibility.md), and commands in [quickstart.md](quickstart.md).

## Technical context

| Concern | Decision |
|---|---|
| Runtime | Python 3.14, repository locked Pixi default environment; macOS ARM64 reference machine. |
| Existing dependencies | `lxml`, current RDAM/Pydantic contracts and optional `doclang[schematron-saxon]`; no additional runtime library. |
| State | Per-request XML bytes/tree/path index and immutable decoded records; no database, shared document cache or archive writer. |
| Entry points | Existing `rdam.ingest`, machine preparation, CLI and HTTP source routes. No new public command or document type. |
| Source scope | DocLang XML and archive paths. Other source forms retain their current route and receive regression checks. |
| Validation | Official path-based XSD/Schematron validation remains. One RDAM-owned parse, not one total parse across independent validator engines. |
| Performance | Remove duplicate RDAM parsing and repeated cell-prefix scans; measure elapsed time and peak process memory on identical inputs. No unmeasured speedup claim. |
| Identity | Original bytes and public anchors remain authoritative; implementation/schema fingerprints and their dependent digests must truthfully change. |
| Dependencies with drift | DocLang release matches local 0.7.3; upstream main fixture corpus has advanced. Docling Core latest is 2.96.0, outside our 2.94.1 lock/range. See Phase A. |

## Constitution check

| Principle | Design response |
|---|---|
| Evidence before claims | Immutable upstream references; observed baseline; proposed behaviour distinguished from current code. |
| One production quality bar | Strict Python 3.14 types; no `Any`-based decoder interface, suppressions, swallowed validation or guessed coordinates. |
| Solo-local simplicity | One private DocLang implementation, synchronous request-local state; no generic plugin framework or service. |
| Honest verification | Full semantic comparisons, causal failure tests and truthful mutation verdicts. |
| Canonical contracts/current specs | Official validation retained; explicit release-versus-main distinction; unchanged persisted shapes. |
| Production topology | No offline/dev imports in `rdam/`; DocLang stays behind optional-format access. |
| Scope and approval | This package is the requested plan. Execution requires approval of its direction; no release or publication is included. |

Pre-design and post-design assessment: the proposed design satisfies these constraints. Actual implementation compliance remains to be checked.

## Project structure and ownership

Proposed additions:

```text
rdam/ingest/doclang/document.py       # private bytes/tree/path ownership and resolution
rdam/ingest/doclang/decoder.py        # source-native element/list/table records
rdam/ingest/_doclang.py            # direct current-contract inventory adapter

tests/ingest/test_doclang_document.py
tests/ingest/test_doclang_decoder.py
tests/ingest/test_doclang_identity.py
tests/production_boundary/test_rst_mutation_verdict.py
```

Retain `rdam/ingest/doclang/loader.py` as bounded archive handling and `text_walker.py` as the single mixed-content traversal. The complete private DocLang package moves out of RST into shared ingestion, as clarified by Steve during implementation. Neither module may import a technique parser or any offline package. Remove obsolete private functions after caller reconciliation; do not delete the legacy contract package, which still serves other formats and historical readers.

## Implementation sequence

Execute phases in order. Each phase ends with a checkable result. Keep intermediate production dispatch coherent; do not leave a selectable legacy/new backend in the final product.

### Phase A — Lock the comparison boundary and repair its verification

**Requirements:** D01, D07-D09, D13-D14.

**Files:** `tests/fixtures/doclang/upstream-manifest.json`, its README and mirrored specimens only if a justified refresh is needed; `tests/ingest/test_doclang_fixture_parity.py`, `tests/ingest/production_ingest/test_upstream_conformance.py`, `tools/rst_mutation_test.py`, the new mutation-verdict test; feature research notes. Read `tools/shared_runtime_mutation_test.py` before reusing its existing causal verdict logic.

1. Recheck HEAD, dirty files, pins, lock, upstream releases and immutable spec commits at implementation start. Keep DocLang package version, DocLang document version and RDAM envelope version distinct.
2. Preserve the released validator boundary. Compare newly added upstream-main fixtures separately; do not replace the supported fixture corpus with specimens the released validator cannot accept. Record exact unsupported cases and the required upstream release. Do not weaken validation to obtain a green current-main result.
3. Explicitly retain the Docling Core 2.94.1 dependency in this refactor and record the known 2.96.0 gap. Its upgrade is a distinct dependency decision, not an implicit consequence of reorganizing DocLang code. If implementation reveals a dependency change is required, revise that decision before proceeding.
4. Capture existing public preparation outputs for every supported valid DocLang fixture, the real-world form, representative archive variants and non-DocLang specimens. Preserve invalid-case expectations separately. Compare field by field using the rules in the compatibility contract; temporary comparison output belongs in a local temporary directory, not a new release-evidence system.
5. Repair three stale `rdam/rst/ingest/_harvest.py` mutation paths. Run each unmodified causal test before mutating. Require a targeted test-call assertion failure with no collection/setup errors; missing sites, import errors, runner failures and timeouts are infrastructure failures, never kills.
6. Record baseline timings for plain XML and archives, including metadata-heavy lists/tables. Record input bytes, node/cell counts, runtime versions, warmup policy and all measured runs.

**Exit:** supported baseline passes; upstream drift is classified; mutation runner targets exist and verdict tests reject false kills; complete comparison outputs and timing observations exist locally.

### Phase B — Introduce one parsed document owner

**Requirements:** D02-D03, D09-D12.

**Files:** new `document.py`; `loader.py`, `errors.py` only where required; new document tests; existing loader/archive tests.

1. Introduce the private document type described in the data model. Retain exact input XML bytes and build one local-name path index with the existing linear traversal.
2. Extract archive acquisition from document-reference validation internally. Acquire bounded member identities/control parts/document bytes, construct one RDAM document, then use its root for existing reference/page checks and subsequent decoding.
3. Keep the existing `load_doclang_archive` private helper callable for its tests/callers; implement it through the same acquisition/check functions. The production adapter consumes the validated document result rather than calling a bytes-only helper and parsing again.
4. Run official validation on the exact bytes via the retained path-based temporary-file bridge. Do not validate a reserialized DOM. Return a validated document only after every applicable XML/package check succeeds.
5. Preserve safe parser settings and error causality. Trees remain request-local and are not embedded in frozen public contracts. Repeated failures cannot expose a partly decoded object.

**Exit:** standalone/archive tests pass; profiles show one RDAM construction of the main document tree per decode; invalid XSD/Schematron/package cases still fail. Control-part and validator-owned parses are counted separately.

### Phase C — Centralize content and table decoding

**Requirements:** D04-D05, D07-D08, D10, D12.

**Files:** `text_walker.py`, new `decoder.py`, document/decoder tests; focused additions under `tests/ingest/production_ingest/`; new local fixtures in a dedicated subdirectory outside the upstream mirror.

1. Extend the existing walker to yield typed unnormalized fragments while preserving its string helpers for real callers. Each fragment has an explicit element text/tail selector or a non-element tail selector as defined in the data model. Join and trim only at the same semantic boundary as the supported behaviour.
2. Cover metadata heads and excluded subtree tails exactly once, including nested formatting, comments, CDATA and whitespace. Inventory traversal still observes metadata and structural nodes; excluding text from authored prose must not remove their inventory records.
3. Decode lists by marker boundaries for raw and wrapped forms. Do not treat only `ldiv.tail` as the full definition of list-item content.
4. Decode each table in one document-order scan, collecting typed row/column coordinates, header markers, continuation ownership and text fragments. Compute merged spans from the resulting grid, including `lcel`, `ucel`, `xcel`, empty cells and nested wrapped content. Preserve standalone wrapper inventory items and deterministic linked-item order.
5. Decode pictures/fields/layers/locations without globally flattening descendants or silently inferring new authorship. Preserve source-derived values and existing policy boundaries.
6. Implement private fragment resolution using explicit slot semantics, not upstream's whitespace-filtered `text()[n]` convention. Use resolution in fragment integrity tests and decoder diagnostics; do not add unused public convenience methods.
7. For any observed mismatch, validate the specimen under the selected official contract. Correct real defects with exact expected text/cells and a causal regression; retain the old result only when it is semantically correct.

**Exit:** each eligible fragment round-trips; no duplicate or missing text; every supported fixture decodes; table coordinates/spans and metadata separation match independently specified expectations.

### Phase D — Emit the current inventory directly

**Requirements:** D06-D09, D11-D12.

**Files:** new `rdam/ingest/_doclang.py`; `prepare.py`, `_harvest.py`; affected tests. Private shared helpers may be extracted into a small `rdam/ingest/_classification.py` only for classification rules demonstrably required by both old non-DocLang and new DocLang callers.

1. Map decoder records directly to `ContentInventoryItem`, current representation types, typed anchors and `SourceContractIdentity`.
2. Preserve element-path item IDs, document order, parent/child links, attributes, source layers, speaker treatment, back-matter reclassification, asset identities and admission policy. Preserve actual existing provider/adapter labels unless a separately justified identity change is necessary.
3. Construct typed coordinate boxes and table coordinates from source values. No selector-string round trip and no fallback to invented zero/default coordinates.
4. Dispatch DocLang source forms before `_legacy_artifact()` in `prepare.inventory_source()`. Other forms continue through their existing translation route.
5. Remove the dead DocLang branches/helpers/imports in `_harvest.py` after enumerating callers. Do not globally modernize unrelated format logic or delete shared legacy translation helpers still used elsewhere.
6. Bind implementation identity to the decoder, text walker, document/archive handling and inventory mapper. Preserve original-byte identities; compare changed implementation fingerprints and downstream digests explicitly. Do not disguise changed code with a frozen old fingerprint.

**Exit:** DocLang no longer constructs legacy models; semantic comparison passes or contains only independently proven defect corrections; other formats and lazy-import checks remain unchanged; repeated calls are deterministic and cache-safe.

### Phase E — Prove the production boundary and measured outcome

**Requirements:** D01-D14.

**Files:** listed tests; `tools/rst_mutation_test.py`; `pyproject.toml` for focused gate/strict-type coverage of the new modules and tests; relevant current documentation such as `docs/production-source-ingest.md` and `CLAUDE.md` only after reading them in full and only where this change invalidates their descriptions.

1. Exercise real `ProductionIngestor.prepare()` and machine preparation for both DocLang forms. Compare provider projections and anchor reconciliation, especially RST authored prose and Toulmin/Walton table evidence. Preserve error categories, serialization/historical reads and source identity.
2. Add causal mutation cases for validation bypass, duplicated/dropped tails, metadata leakage, swapped cell coordinates, lost continuation spans and stale decoder identity. Update moved mutation sites rather than dropping them. Keep all existing non-DocLang mutation cases.
3. Extend the existing format-coverage task's measured module list to include new document/decoder/mapper modules. Keep its existing floor; do not use the refactor to hide code outside the measured set. Add all new test files to strict typing and the appropriate focused task list.
4. Run focused checks first, then the all-ingest, applicable machine/interface, fast full suite, format coverage, mutation, lint, typecheck, markdown and production-boundary gates. Resolve failures before broadening or repeating checks.
5. Repeat baseline profiling/timings with the same inputs and conditions. Report all runs and memory measurements, not a selected best case. Separate validation cost from RDAM parse/decode cost. Investigate material regressions; do not change the benchmark until it passes.
6. Refresh the graph using `graphify update .` after code changes. Inspect the final diff for scope, dead branches, public contract drift and dependency changes.

**Exit:** all named gates pass; each requirement has a recorded check; no unexplained semantic differences; actual structural/performance outcome reported. Build/publish/tag/push is not part of this plan. If inference/tokenization code must change, stop treating this as an ingest-only refactor and apply the project's full model integration checks.

## Validation matrix

| Area | Required observations |
|---|---|
| Corpus | All supported valid/invalid mirrored fixtures, namespace variants, real-world form; upstream-main incompatibilities reported separately. |
| Mixed content | Nested formatting; metadata before/between content; comments; CDATA; empty/whitespace-only nodes; leading/trailing whitespace; Unicode and tails after excluded subtrees. |
| Lists/tables | Raw/wrapped forms, nested content, headers, empty cells, row breaks, all continuation directions, rectangularity rejection, exact links and coordinates. |
| Archive | Every existing limit/rejection; assets and page images; unchanged byte hashes; identical semantic XML content with container-specific anchors. |
| Compatibility | Order, IDs, all representation fields, anchors, links, authorship/layers, prepared ranges, transformations, dispositions and provider projections. |
| Failures | Invalid XML, XSD-only and Schematron-only failures, missing optional dependency, archive rejection, failure after a prior successful request, no partly validated success. |
| Isolation | Independent repeated/concurrent decode requests; no tree in serialization; lazy format imports; no new public API. |
| Verification | Baseline passes; intended assertion kills each mutant; runner/setup failure never passes; coverage includes all moved code. |
| Performance | Main-tree construction count, path-index count, table prefix scans removed; same-fixture latency and peak memory before/after. |

## Risks and handling

- **Preserving a latent defect:** use normative expected results alongside comparison snapshots. Never make the legacy output the only oracle.
- **Changed fingerprints look like semantic drift:** classify differences using the compatibility contract and trace derived digests to the precise changed input.
- **Shared helpers affect other formats:** preserve their current route and run non-DocLang conformance; extract only genuinely shared rules.
- **Raw bytes and tree diverge:** do not mutate the source tree or serialize it as replacement input; retain original archive/document bytes.
- **Fragment grammar becomes accidental API:** keep types private and test their absence from serialized anchors. Public fragment anchors would need a separate explicit contract decision.
- **Dependency/main drift:** use released validator support as the runtime boundary and preserve a dated, explicit current-main gap. No vendored validator fork or silent acceptance relaxation.
- **Rollback:** use ordinary focused commits during approved implementation. Revert an incomplete phase before integration rather than retaining a permanent legacy fallback flag. Existing historical readers stay in place.

## Planning evidence and completion boundary

Planning checks observed: the four-file DocLang baseline passed **98 tests in 0.85 seconds**. A mutation-target existence check found three stale paths. These findings are recorded in research; the full mutation gate and complete production suite were not run during planning.

The six planning documents were read in full after creation. Repository Markdown lint passed across 271 files. Spec Kit setup selected this feature in its local feature state; the planning checkout was `master`; implementation uses `codex/020-doclang-decoder`. No before/after planning hooks are configured. The approved execution checklist is `tasks.md`; the implementation sequence and exit criteria are fully specified here.

The implementation is complete only after Phase E's checks and semantic review. Approval of this plan accepts the proposed private fragment semantics and explicit dependency boundary; it does not authorize a public schema migration, dependency upgrade or publication.

## Ownership correction during implementation

Steve clarified that source decoding belongs to shared ingestion for all processes. Move the complete private DocLang package from `rdam.rst.doclang` to `rdam.ingest.doclang`, update consumers and checks, and assert the old RST helper package is absent. The historical research paths above now name their implementation destinations. No technique owns document decoding.

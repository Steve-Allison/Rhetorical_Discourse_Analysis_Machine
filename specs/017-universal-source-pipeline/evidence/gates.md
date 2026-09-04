# Feature 017 implementation verification

Date: 2026-09-04. Source checkout on `master`; no commit, push, publication, or branch
change was performed. Historical baseline artifacts remain unchanged.

## Status

**All 91 of 91 tasks are complete.** The owner-approved source-identity and DocLang
table corrections are independently verified, with zero unexplained regressions and
unchanged historical baseline files. The final full suite and smoke checks passed after
all behavioural code changes. Corrected records are explicitly not analytically equivalent
to the historical faulty records. T029 is closed under the approved FR-005 / SC-010.

The implementation uses canonical `rdam.ingest`, with no old-module shim or contract
aliases. Composition lives in `rdam/composition.py`. Providers declare requirements;
text providers without a requirement are rejected. The machine inventories once,
shares identical projections, preserves structured-input boundaries, and returns a
single preparation receipt.

## Verification runs

Commands below ran through `pixi run --locked` in the default environment unless
an environment is explicitly shown. Counts are observed results, not collection estimates.

| Check | Observed result |
| --- | --- |
| `lint` after the current code repairs | `All checks passed!` |
| `typecheck` after the current code repairs | `0 errors, 0 warnings, 0 informations` |
| `test` after all code repairs | 1,622 passed, 147 deselected, 60.05 seconds |
| `test-all` after all code repairs | **1,713 passed, 56 skipped, 411.90 seconds** |
| `mdlint`, including this evidence file | `Summary: 0 issues in 0 files`; 247 files linted |
| `-e default production-boundary` | `valid: true`, `violations: []`, 149 modules scanned |
| `ontology-validate` | Exit 0; both validations `No issues found`; framework projection matches Central; one imported `_meta` naming warning remains |
| `smoke` after all code repairs | 41 passed, 54 skipped, 42.51 seconds |
| Migrated providers, ingest, machine, and LLM suites after table repair | 957 passed, 5 deselected, 30.14 seconds |
| Machine and LLM suites after requiring text-provider declarations | 227 passed, 6.67 seconds |
| Expanded table projections, projection invariants, Toulmin | 42 passed, 1 live-model test skipped, 4.72 seconds |
| Real batch inference and adversarial tests | 9 passed, 23.23 seconds; the subsequent dynamic-attribute parameter adds one more case |
| Real predictor/full-provider concurrency, CPU and MPS | 8 passed, 4 deselected, 88.33 seconds; see `parser-concurrency.md` |
| `rg -n 'type: ignore\|pyright: ignore\|noqa' rdam tests tools` | Exit 1, no output: zero matches |

The final runs above supersede the earlier passing checkpoints: fast suite 1,586 passed /
147 deselected / 46.14 seconds, full suite 1,677 passed / 56 skipped / 413.42 seconds,
and smoke 41 passed / 54 skipped / 53.47 seconds. Lint, typing, boundary, ontology and
Markdown checks were also rerun after the final comparison and section-row repairs.
All seven technique and all six source-form capability states were rechecked as available.

Two intermediate whole-suite runs are **not passes**: 1 failed / 1,656 passed /
56 skipped, and 1 failed / 1,668 passed / 56 skipped. Their failures were stale test
assertions for the previous RST safety declaration and previous OpenAI client class,
respectively. Both assertions were corrected with their substantive checks retained.
The subsequent fresh whole-suite run above passed.

## Live end-to-end proof

The tabular-evidence Markdown fixture was submitted through `production_machine()` and
`AggregateRequest.for_source` for RST, Toulmin, and Walton, with real configured models.
Observed after repairing the OpenAI endpoint:

```text
receipts: 1
projections: 3
rst ResultOutcome
validated native result: rst_tree aligned spans: 0
toulmin ResultOutcome
validated native result: toulmin_layout aligned spans: 1
walton ResultOutcome
validated native result: walton_schemes aligned spans: 0
```

Zero outer alignment entries do not mean invented offsets: RST retains its native
anchor evidence, and the generic exact-quote alignment does not assign coordinates to
unmatched paraphrases. Deterministic cross-technique alignment is separately exercised
by `tests/machine/test_alignment.py`.

The previous client returned HTTP 400: reasoning plus function tools was rejected on
Chat Completions. The boundary now constructs `OpenAIResponsesModel`, retaining the
configured model, typed output validators, deadlines, and `max_retries=0` on the SDK.
The configuration follows the current [Pydantic AI OpenAI documentation](https://github.com/pydantic/pydantic-ai/blob/main/docs/models/openai.md)
and [OpenAI model documentation](https://developers.openai.com/api/docs/models/gpt-5.6-sol).
The live run, not the documentation alone, establishes the observed fix.

## Quickstart scenario results

The quickstart selectors were executed again after the final declaration repair.
All six source forms reported `available`: text, EDUs, Markdown, Docling JSON,
DocLang XML, and DocLang archive. All seven technique capability states remain
`available`, matching T001: RST, PDTB, SDRT, Toulmin, Walton, Dung, IBIS.

| Scenario | Observed test result |
| --- | --- |
| SC-001, including unavailable-adapter failure | 9 passed |
| SC-002 / SC-003 | 12 passed, 141 deselected |
| SC-004 projection / Toulmin / RST | 1 passed in each of the three commands |
| SC-005 / SC-006 | 14 passed, 482 deselected |
| SC-007 / SC-008 inventory / SDRT | 3 passed / 1 passed |
| SC-009 | 6 passed, 490 deselected |
| SC-010 | **Passed**; model-backed comparison exit 0, zero unexplained regressions; 715 identity and 437 table corrections independently verified |
| SC-011 / SC-012 | 13 passed, 61 deselected; six actual identity-change misses included |
| SC-013 / SC-014 machine | 6 passed, 147 deselected |
| SC-013 / SC-014 real CPU/MPS parser and provider | 8 passed, 4 deselected |
| SC-015 | 1 passed, 152 deselected |
| SC-018 | 2 passed, 494 deselected |
| SC-019 | 6 passed, 490 deselected |
| SC-020 | 3 passed, 150 deselected |

SC-016 / SC-017 use the full gates listed above. The historical baseline capture is
a completed pre-change operation, not rerun against changed code. The end-to-end
quickstart now uses the tabular fixture, which was verified with real models.

The implementation skill's after-hook check found no `.specify/extensions.yml`;
there are no registered post-implementation hooks to dispatch.

## Historical baseline conflict: T029 / SC-010

The pre-approval comparison used `evidence/baseline-dmrst-current`, the immutable
`gumrrg-eb1d5745f3a1` release in the local model cache, and CPU. Its result is:

```text
analytically_equivalent: false
analytical: 1131
contract_field_rename: 32
derived_digest: 37
execution: 40
```

Every analytical difference at that historical checkpoint fell into these two repairs:

| Record | Source identity / anchor identity fields | Table representation fields |
| --- | ---: | ---: |
| `prepare-doclang_xml` | 581 | 416 |
| `prepare-docling_json` | 116 | 0 |
| `prepare-markdown` | 18 | 0 |
| Total | 715 | 416 |

`SourceArtifact.from_path` previously changed the origin from URI to local file after
computing its identity without recomputing that identity. The repaired constructor
validates and hashes the actual final fields. All 715 identity differences are the
source summaries and their matching anchor references.

DocLang table construction previously treated unanchored wrapped XML text, row markers,
and location elements as extra cells, assigning guessed row/column positions and sometimes
overwriting real coordinates. Tables now contain only source-anchored cells. Wrapped
content remains in the complete inventory, is linked to its originating cell, and is
included in the projection's derivation instead of repeated as another cell. For the
rectangular upstream fixture, the source's three tables have 6, 9, and 9 cells, not
14, 18, and 19. New tests fail on the old behavior and pass on the repair.

No additional prepared-text, tree, edge, or other analytical differences were reported by
that baseline run. Its actual verdict was **failure**. At that point the existing
approved capacity-field rename did not cover the later correctness repairs.

## Owner-approved comparison repair

The owner subsequently approved the source-based verification solution and instructed
implementation. FR-005 and SC-010 now distinguish approved, independently verified
corrections from unexplained regressions; they do not call changed records equivalent.
The historical baseline files have not been overwritten or recaptured.

`tools/production_boundary/baseline_corrections.py` separately verifies identities and
DocLang tables. The identity proof recomputes the URI-origin and final local-file IDs
from the same immutable source. The table proof reads coordinates directly from XML,
reconstructs the historical faulty representation, and accepts only the exact corrected
representation with its source-bound inventory evidence. Current-output invariants also
reject an unchanged historical bug, such as a stale anchor ID or an unrepaired table.

This independent check exposed one further part of the table defect: `<srow>` is a
section-row header, not a separator. The current
[DocLang structural-element specification](https://github.com/doclang-project/doclang/blob/6d3b3d3c195d1f63333c5c5fcba8da17937a33bd/spec.md#srow)
defines it explicitly. Harvesting now gives it its own text and cell coordinates;
table construction marks it as a header. Both raw and wrapped-text regression tests
failed before the fix and pass after it. The comparator proves those exact header
additions from XML, rather than accepting arbitrary inventory changes.

The real CPU/model-backed comparison command from the quickstart returned exit 0:

```text
equivalent: false
analytically_equivalent: false
no_unexplained_regressions: true
source_identity_correction: 715
doclang_table_correction: 437
contract_field_rename: 32
derived_digest: 37
execution: 41
analytical_differences: {}
```

The table count is now 437 rather than 416 because section-row headers are correctly
represented. Execution count increased by one because the comparator now inspects full
records even when their stored semantic digests match. A stale digest can no longer hide
changed contents. Missing JSON fields and changed JSON types are also compared explicitly.

Focused verification: **61 passed in 18.12 seconds**, comprising both comparator test
modules and `tests/ingest/test_table_linearisation.py`. Deliberate corruptions include
IDs, stale references, source name, text, cell geometry, spans, headers, links, missing
and extra cells, section-row headers, inventory changes and an altered historical table.
Real CLI tests prove exit 0 for verified corrections, exit 1 for a stale digest or missing
record, and byte-for-byte preservation of the supplied baseline directory.

An intermediate full run was interrupted after production changed during execution:
3 failed, 1,266 passed, 54 skipped, 339.68 seconds. Its subprocesses observed the new
section-row implementation while the parent retained earlier imports. It is not final
verification. The unchanged tests subsequently passed in the fresh focused run and the
final full run: **1,713 passed, 56 skipped, 411.90 seconds**. The subsequent smoke run
passed: **41 passed, 54 skipped, 42.51 seconds**.

## Upstream format currency

Docling Core 2.94.1 and DocLang 0.7.3 were checked against current upstream package
versions during implementation. The current DocLang `main` commit was rechecked as
`6d3b3d3c195d1f63333c5c5fcba8da17937a33bd`; all **42** upstream valid fixture names and
SHA-256 byte hashes match the local fixtures and manifest. The DocLang table repair uses
the current format's cell markers, not XML-child indices as invented geometry.

## Documentation and graph maintenance

README, project briefing, architecture rules, active production-ingest/API/boundary docs,
and Feature 017's current contracts and quickstart were updated. Historical forensic
reports, prior plans, and captured evidence retain their historical names; they are not
current import instructions. No compatibility imports were retained in production code.

The Markdown gate exposed formatting defects in the repository Graphify skill files.
Their formatting was repaired without changing the extraction procedure. The earlier
AST-only `graphify-code` update succeeded: 12,288 nodes, 25,668 edges, 1,156 communities.
It reported changed community labels; no paid semantic labeling or extraction was run.
This is graph maintenance, not evidence that tests pass.

The final verification-repair AST update reported 12,336 nodes, 25,804 edges and
1,138 communities. Community names changed; no paid semantic labeling was performed.

## Full-file review scope

The Feature 017 spec, plan, tasks, research, data model, both contract documents, and
quickstart were read in full. The final repair review also read these complete files:

- `rdam/contracts.py`, `rdam/_llm.py`, `rdam/rst/provider.py`, and `rdam/toulmin/provider.py`;
- `rdam/ingest/prepare.py`, `_harvest.py`, `projection.py`, `subdivision.py`, `policy.py`,
  `requirements.py`, `capabilities.py`, and the preparation/capability contracts;
- `tools/production_boundary/rst_baseline.py`;
- `tools/production_boundary/baseline_corrections.py` and both baseline-comparator
  test modules, plus the extended table-linearisation tests;
- the changed projection-contract, table-linearisation, source-form, RST-provider,
  Toulmin-provider, LLM-boundary, cache, machine-contract, shared-runtime, and adversarial
  test files, plus their shared machine fixture definitions;
- README, CLAUDE, architecture rules, and the three active production API/ingest/boundary
  documents updated by this feature.

Search hits were used to locate files; final findings above are based on those complete
reads and the named executable checks, not on the Graphify map alone.

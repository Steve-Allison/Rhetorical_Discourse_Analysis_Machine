# Python 3.14 production-code audit

**Repository:** Rhetorical Discourse Analysis Machine
**Scope:** every Python source file under `rdam/`
**Audit date:** 2026-09-03
**Mode:** completed production review and full implementation pass

## Executive verdict

The implementation pass is complete. All **12 P1 remediation groups**, all **15 P2 groups**, and the P3 Python 3.14 modernization backlog were implemented across the production package, with focused regressions and whole-suite validation. The original findings remain below as the evidence record; this outcome section is the authoritative current status.

The production package now passes strict Pyright, the ordinary Ruff gate, the expanded Python 3.14 modernization gate, the complete test suite, the production boundary scan, format conformance, preparation performance thresholds, and real Chromium PNG/PDF rendering. The only incomplete release-level proof is a fresh wheel/sdist build: the repository's build command correctly refuses the intentionally dirty implementation worktree. Existing `dist/6.0.0` artifacts validate, but they predate this implementation and are not evidence for the changed source.

## Implementation outcome

### Correctness and contract repairs

- Fixed source/public-surface root resolution, removed CWD-dependent checkpoint discovery, and made dotenv capability discovery side-effect-free with `dotenv_values`.
- Repaired sentence-boundary tensor assignment, gold-only metric bookkeeping, zero-denominator behavior, BERT right-span slicing, final-window entity propagation, classifier bias wiring, and pointer-segmenter construction/device compatibility in both parser families where applicable.
- Preserved parallel RST/eRST edges with keyed `MultiDiGraph` export and made frozen/public mappings deeply immutable.
- Made viewer import/render failures typed, bounded by readiness timeouts, and resource-safe. The real-browser acceptance probe additionally exposed and fixed two latent defects: the generated page omitted the `inner_canvas` root expected by jsPlumb, and PDF crop CSS generated an empty page.
- Removed no-op/dead production surface, moved promotion-only evidence to `workbench`, normalized provider text validation, and retained checkpoint/state-dict topology. A typing regression that briefly changed duplicate `ModuleList` registration was caught by the production smoke suite and fixed before final verification.

### Performance and Python 3.14 work

- Replaced repeated sentence/EDU/inventory/anchor scans with monotonic cursors and indexes; cached provenance; indexed DocLang sibling paths and IBIS lookups; used `deque`, `pairwise`, `batched`, iterator pipelines, and tensor broadcasting where they materially improve the implementation.
- Replaced recursion at public deep-tree serialization/remapping boundaries with iterative traversals and explicit cycle/shared-node checks.
- Centralized device/dtype behavior and the shared metric kernel while preserving parser-family architecture and released state-dict keys.
- Enabled strict Pyright for all of `rdam/`, added narrow third-party stubs, expanded the production modernization gate, removed all quoted annotations, and introduced no `from __future__ import annotations`, checker suppressions, or blanket exclusions.

### Final verification evidence

| Check | Actual result |
|---|---|
| `pixi run typecheck` | `0 errors, 0 warnings, 0 informations` under strict mode |
| `pixi run lint` | `All checks passed!` |
| `pixi run lint-production-modern` | `All checks passed!` |
| Suppression/future-annotations scan | no matches under `rdam/` |
| Focused provenance/provider/contracts/performance | `66 passed, 1 deselected in 4.31s` |
| Complete suite | `1540 passed, 56 skipped in 251.44s` |
| Production API contract | `397 passed in 21.20s` |
| RST format suite | `242 passed in 5.23s` |
| Preparation performance thresholds | `3 passed in 2.76s` |
| Viewer/audit regressions after renderer repair | `54 passed in 3.03s` |
| Shared-runtime coverage | `96 passed`; `298` statements and `96` branches at `100.00%` |
| Shared-runtime mutation gate | `6/6` critical mutants killed |
| Production boundary | `valid: true`; `144/144` modules scanned; no violations |
| Real async renderer | PNG `13,780` bytes; PDF `18,921` bytes; rendered PDF nonblank at `1212 x 768` |
| `pixi run build-production` | blocked as designed: `RuntimeError: production artifacts require a completely clean worktree` |
| Existing artifact validation | `valid: true`, but applies to the pre-implementation `dist/6.0.0` artifacts only |

DocLang currency was checked against upstream 0.7.3, the current specification, and the upstream valid-fixture inventory. The repository pin/lock and `schematron-saxon` extra remain current, and all 41 local `.dclg` fixture names match upstream.

## Scope and evidence

### Complete-read coverage

I read all **137 Python files / 35,861 lines** under `rdam/` in full. The directory ledger is:

| Production area | Files read in full |
|---|---:|
| `rdam/` root | 7 |
| `rdam/dung/` | 3 |
| `rdam/ibis/` | 3 |
| `rdam/pdtb/` | 3 |
| `rdam/sdrt/` | 3 |
| `rdam/toulmin/` | 3 |
| `rdam/walton/` | 3 |
| `rdam/rst/` root | 10 |
| `rdam/rst/contracts/` | 7 |
| `rdam/rst/dmrst_parser/` (including `src/parser/`) | 11 |
| `rdam/rst/doclang/` | 4 |
| `rdam/rst/english/` | 4 |
| `rdam/rst/erst/` | 11 |
| `rdam/rst/graph/` | 2 |
| `rdam/rst/hierarchical/` | 2 |
| `rdam/rst/ingest/` (including contracts) | 25 |
| `rdam/rst/markdown/` | 2 |
| `rdam/rst/model_loading/` | 3 |
| `rdam/rst/ontology/` | 3 |
| `rdam/rst/relations/` | 2 |
| `rdam/rst/rstviewer/` | 6 |
| `rdam/rst/segmentation/` | 2 |
| `rdam/rst/universal_parser/` (including `src/parser/`) | 12 |
| `rdam/rst/utils/` | 6 |
| **Total** | **137** |

I also read the complete project instructions, `CLAUDE.md`, `pyproject.toml`, and the code/architecture/command/no-assumptions rules before assessing the source.

### Baseline gates actually run

| Check | Actual result |
|---|---|
| `pixi run lint` | `All checks passed!` |
| `pixi run typecheck` | `0 errors, 0 warnings, 0 informations` |
| `pixi run test` | `1348 passed, 134 deselected in 35.68s` |
| `pixi run -e default production-boundary` | `valid: true`, `production_modules: 137`, `scanned_files: 137`, `violations: []`, `artifact_receipts: []` |

These results prove the existing gates pass. They do **not** disprove the findings below: several defects sit on configurations or edge cases absent from the selected test set, while the current Ruff and Pyright configurations omit checks that would expose much of the modernization backlog.

### Additional diagnostics and probes

- Extended Ruff (`UP,SIM,PERF,C4,PIE,RUF`) found **216** diagnostics, of which 79 are safe auto-fixes under that invocation.
- Ruff annotations (`ANN`) found **280** diagnostics: 151 missing argument annotations, 51 missing return annotations across function kinds, and 78 explicit `Any` uses.
- Python 3.14 modernization found **38 quoted annotations** (`UP037`). No `from __future__ import annotations` exists under `rdam/`, which is correct for this project.
- A tensor probe matching the sentence-boundary expression proved `logits[sent_breaks][0] = -300.0` leaves the original tensor unchanged; `logits[sent_breaks, 0] = -300.0` updates it.
- Path probes proved `erst/environment.py` and `ingest/public_surface.py` resolve `parents[2]` to the package directory `.../rdam`, not the repository root. The real quickstart exists at repository level, while the path the validator checks does not.
- An import-order probe started with `PYTORCH_ENABLE_MPS_FALLBACK` absent and showed it was set only after `rdam.rst` had already imported PyTorch.

Python recommendations were checked against the current [Python 3.14 annotation semantics](https://docs.python.org/3.14/reference/compound_stmts.html#annotations), [`itertools`](https://docs.python.org/3.14/library/itertools.html), and [`typing.override`](https://docs.python.org/3.14/library/typing.html#typing.override) documentation. Immutability findings account for Pydantic's documented [faux immutability](https://docs.pydantic.dev/latest/concepts/models/#faux-immutability): `frozen=True` prevents rebinding fields but does not freeze nested dictionaries or lists.

## Finding taxonomy

- **P1 — correctness/contract:** an accepted input can produce wrong output, a validator can certify something it did not inspect, or a public/configuration contract is false.
- **P2 — material maintainability/performance:** avoidable asymptotic work, resource-lifetime risk, incomplete typing at a production boundary, or architectural duplication likely to cause drift.
- **P3 — mechanical modernization:** low-risk idiom, clarity, allocation, or checker improvement. Small does not mean optional; these are grouped so they can be completed mechanically.

## P1 — correctness and contract findings

### P1.1 Public-surface documentation validation currently passes without validating documentation

**Evidence:** `rdam/rst/ingest/public_surface.py:185-194` resolves `parents[2]` to `.../rdam`, then looks for `rdam/specs/004-production-api-contract/quickstart.md`. If that wrong path is absent, line 189 returns `True`. The repository-level quickstart exists.

**Impact:** every documentation anchor can be reported valid even if it is missing or stale. This is a false-positive certification gate.

**Action:** resolve the repository root explicitly (or inject it), and make absence of the authoritative quickstart a validation failure rather than success. Prefer a package-resource manifest if installed-wheel validation must work without repository docs; do not silently conflate source-tree and installed-package modes.

**Acceptance:** tests must prove (a) a real anchor passes, (b) a nonexistent anchor fails, (c) a missing authoritative file fails in source mode, and (d) installed-package mode has a separately explicit policy.

### P1.2 The default eRST environment root is the package directory, not the repository

**Evidence:** `rdam/rst/erst/environment.py:38-48` uses `Path(__file__).resolve().parents[2]`, which evaluates to `.../rdam`; it therefore looks for `rdam/.env`, not `<repository>/.env`. `rdam/rst/erst/checkpoint.py:377-392` also resolves the fallback `models/erst_scorer_bundle` relative to the caller's current working directory.

**Impact:** the same installed code has different capability depending on the invocation directory, and repository-local credentials/checkpoints are missed by the documented default.

**Action:** remove repository discovery from installed production behavior. Resolve configuration in this order: explicit argument, explicit environment variable, then a stable user-local default if the product actually wants one. If source-checkout convenience remains, derive the true root through one tested helper and never use caller CWD.

**Acceptance:** run the same capability probe from repository root and an unrelated temporary directory; results must match. Test explicit path, environment path, absent path, and invalid manifest.

### P1.3 Sentence-boundary enforcement is a no-op in both neural segmenters

**Evidence:** `rdam/rst/dmrst_parser/src/parser/segmenters.py:503-510` and `rdam/rst/universal_parser/src/parser/segmenters.py:505-512` assign through chained advanced indexing: `logits[sent_breaks][0] = -300.0`. Advanced indexing creates a copy. The audit probe observed `chained_assignment_changed=False`.

**Impact:** configurations that require sentence boundaries do not enforce them, potentially placing EDU boundaries across sentences or training/evaluating a different objective than configured.

**Action:** assign on the original tensor (`logits[sent_breaks, 0] = ...`) after validating indices and intended class semantics. Use a dtype-aware finite floor rather than a magic constant where appropriate.

**Acceptance:** unit tests must inspect logits before softmax and prove every requested boundary is constrained, non-boundary rows are unchanged, duplicate/empty indices behave deliberately, and float16/bfloat16/float32 all remain finite.

### P1.4 Metric bookkeeping is wrong and empty inputs can divide by zero in both parser families

**Evidence:**

- `rdam/rst/dmrst_parser/src/parser/metrics.py:163-174` and `rdam/rst/universal_parser/src/parser/metrics.py:170-181` assign a gold-only count to `cur_goldenno` but append the untouched `cur_golden_n` (zero) to per-document results.
- `rdam/rst/universal_parser/src/parser/metrics.py:152` uses substring membership (`not in "none"`) rather than inequality.
- `rdam/rst/dmrst_parser/src/parser/metrics.py:193-227` and `rdam/rst/universal_parser/src/parser/metrics.py:200-235` guard only `n_sys`; segmentation and gold denominators can still be zero.
- `rdam/rst/universal_parser/src/parser/metrics.py:41-46` prints internal state to stdout and re-raises from a blanket `Exception`.

**Impact:** macro metrics undercount gold-only documents; empty/single-EDU evaluation can crash; library calls can leak debug output.

**Action:** implement one shared, typed metric kernel used by both model families. Represent the no-tree state with an enum/sentinel rather than casing-sensitive strings. Define zero-denominator semantics once (normally 0.0 except explicitly documented perfect-empty comparisons), and raise a contextual parse exception without printing.

**Acceptance:** table-driven tests must cover both-empty, predicted-only, gold-only, one-EDU, empty segmentation, mixed case, and ordinary parses; compare micro and macro results against hand-computed fixtures.

### P1.5 BERT discourse-unit encoding ignores the requested right boundary

**Evidence:** `rdam/rst/dmrst_parser/src/parser/parsing_net.py:862-894` and `rdam/rst/universal_parser/src/parser/parsing_net.py:885-917` compute `right = edu_breaks[right_b]` but slice the right unit as `embeddings[middle + 1 :, :]`. The calculated `right` is unused.

**Impact:** for any non-terminal subspan, relation classification includes embeddings from later, unrelated EDUs. This changes inference mathematics relative to the requested span and can contaminate both training and inference for `du_encoding_kind="bert"`.

**Action:** slice `middle + 1 : right + 1`. Do not alter learned architecture or weights; this is restoration of the declared span boundary.

**Acceptance:** use position-coded embeddings and several nested spans to assert exact left/right tensors; add parity tests for the whole-document terminal span and regression tests for non-terminal spans in both families.

### P1.6 UniRST drops entity inputs from the final long-document window

**Evidence:** `rdam/rst/universal_parser/src/parser/modules.py:320-368` sends entity IDs/positions in the first and middle window branches, but the last-window branch at lines 342-344 calls the transformer with token IDs only.

**Impact:** entity-aware encoders receive inconsistent signatures across windows; the last section loses entity information or can fail for models requiring entity tensors.

**Action:** factor one window-encoding helper that selects, clips, and rebases entities for every window, including the last. Avoid three divergent branches.

**Acceptance:** a fake transformer must record every call for a sequence spanning at least three windows; verify entity IDs and rebased positions for first, middle, and final windows, including entities crossing padding boundaries.

### P1.7 `classifier_bias` is accepted and stored but ignored

**Evidence:** DMRST stores the argument at `rdam/rst/dmrst_parser/src/parser/parsing_net.py:110`, but constructs classifiers with `bias=True` at lines 185-200. UniRST repeats the defect at `rdam/rst/universal_parser/src/parser/parsing_net.py:124` and lines 231-250.

**Impact:** model configuration and reconstructed checkpoint architecture can disagree. A caller cannot create the requested bias-free classifier, and the constructor receipt is false.

**Action:** pass `classifier_bias` through every classifier construction. Validate checkpoint compatibility before loading state; if released checkpoints require bias, encode that in their manifest/config rather than overriding the caller silently.

**Acceptance:** instantiate both values in both families and assert the presence/absence of the bilateral bias parameter and successful loading of matching fixture state dictionaries.

### P1.8 DMRST's pointer-segmenter option cannot be constructed as declared

**Evidence:** `rdam/rst/dmrst_parser/src/parser/parsing_net.py:121-125` constructs `PointerSegmenter` without an attention model. Its default is `None` (`segmenters.py:13-27`), while `PointerAtten` rejects anything except `Biaffine` or `Dotproduct` (`modules.py:406-421`). The segmenter's GRU is also created without `device=`, and `EncoderRNN` calls `test_segment_loss(..., cur_sent_break)` while `PointerSegmenter.test_segment_loss` accepts only one argument (`segmenters.py:66`).

**Impact:** an advertised DMRST configuration fails during construction or invocation and can create mixed-device modules.

**Action:** either make pointer segmentation a real supported configuration (explicit attention argument, unified segmenter protocol, correct device placement) or remove it from the accepted production configuration. Do not retain a dead option.

**Acceptance:** parameterize construction and one forward segmentation over every accepted `segmenter_type` on CPU and the available accelerator; invalid names must fail at the boundary.

### P1.9 NetworkX export loses parallel primary/secondary relations

**Evidence:** `rdam/rst/graph/export.py:11-85` builds `nx.DiGraph` and adds primary and secondary edges by endpoint pair. A later edge with the same ordered endpoints overwrites the earlier edge's attributes.

**Impact:** valid eRST multigraph information is silently lost in a public export format.

**Action:** return `nx.MultiDiGraph` and key each edge by stable `edge_id`. If a simple graph projection is useful, expose it under a separately named, explicitly lossy function.

**Acceptance:** construct an analysis with one primary and at least two secondary edges sharing endpoints; round-trip/export assertions must retain every edge ID, kind, signal, and confidence.

### P1.10 Viewer import/render errors are swallowed and resources can leak

**Evidence:**

- `_rs3tohtml_with_db` ignores the `str | None` result from `import_document` (`rdam/rst/rstviewer/main.py:76-84`); `import_document` returns an error string for malformed RS3 (`rstweb_sql.py:136-149`).
- Sync PNG, async PNG, and async PDF rendering swallow `PlaywrightTimeoutError` and continue (`main.py:526-532`, `569-575`, `622-628`).
- browser/context closure is not protected by `finally` in those paths (`main.py:514-543`, `555-597`, `611-666`).

**Impact:** malformed input can proceed into misleading secondary failures; timed-out pages can be captured as incomplete artefacts; exceptions after launch can leave browser processes/resources alive.

**Action:** raise a typed RS3 import error immediately; treat page readiness timeout as a render failure with the requested timeout in context; use nested async/sync context managers or `try/finally` for context/browser lifetime. Replace fixed waits with an explicit graph-ready predicate.

**Acceptance:** malformed RS3, navigation timeout, screenshot/PDF exception, and success tests must all prove the correct exception and exactly-once closure of page/context/browser.

### P1.11 Public and immutable-looking objects expose mutable state

**Evidence:**

- `Machine` annotates a mutable local dictionary as `Mapping` and returns it directly (`rdam/machine.py:63-74`). A caller can mutate it at runtime.
- `FormatRstAnalysis` is a frozen, slotted dataclass but contains mutable `dict` fields (`rdam/rst/contracts/analysis.py:186-196`).
- `RS4Document` is frozen/slotted but contains mutable relation/signal dictionaries (`rdam/rst/erst/rs4.py:54-64`).
- cached `OntologyLockData` exposes mutable dictionaries from a process-global `@cache` result (`rdam/rst/ontology/loader.py:28-42`).
- `RelationCompatibilityProfile` is frozen but exposes `by_signal: dict` (`rdam/rst/erst/candidates.py:17-24`).

**Impact:** consumers can invalidate machine boundaries or mutate supposedly stable cached ontology/configuration data for every later request in the process.

**Action:** make defensive copies at construction and expose `MappingProxyType`/`Mapping`, or model the data as tuples of immutable entries where serialization matters. For Pydantic wire contracts, use tuple fields and explicit serializers if contract arrays must remain arrays. Immutability must be deep enough for the documented guarantee.

**Acceptance:** mutation attempts through every public property must fail without altering later instances; serialization output must remain contract-compatible.

### P1.12 Capability discovery mutates process environment and parses dotenv incompletely

**Evidence:** `_llm.py:113-151` hand-parses `.env`, writes keys into `os.environ`, and calls that mutating loader from `unavailable_reason`, whose docstring calls capability discovery side-effect-free. The hand parser cannot correctly implement the installed `python-dotenv` grammar (escaped values, inline comments, multiline forms, interpolation).

**Impact:** asking what is available changes later process behavior and can misread a valid local configuration.

**Action:** inspect dotenv with `dotenv_values` without mutating process state during capability discovery. Load explicitly only at provider construction/execution if desired. Centralize supported provider/key resolution and cache only non-secret, stable discovery metadata.

**Acceptance:** snapshot `os.environ` before/after capability discovery; it must be identical. Add official dotenv syntax fixtures and prove no secret value appears in repr, logs, failure parameters, or serialized receipts.

## P2 — material modernization and performance findings

### P2.1 Device/dtype resolution is duplicated and wrong for MPS

`rdam/rst/segmentation/transformer_segmenter.py:48-73` and `rdam/rst/erst/neural_scorer.py:129-154` use `torch.cuda.is_bf16_supported()` to choose an MPS dtype, and silently turn unknown dtype strings into float32. Centralize a typed resolver by actual device type; reject unknown strings. Test CPU/MPS/CUDA probes without requiring all hardware. Also route parser imports through `_torch_runtime`: current `parser.py` and both predictors import PyTorch before `_torch_runtime` can set the MPS fallback (`parser.py:1-10`, both `predictor.py:1-15`).

### P2.2 Recursive processing is used at unbounded public/input boundaries

Recursive walks appear in `annotation_rst.py:97-112,195-207,256-279`, `utils/serialization.py:33-71`, `utils/serialization_pydantic.py:44-76`, `utils/du_converter.py:184-235`, `ingest/validation.py:200-211`, `sdrt/graph.py:96-112,206-220`, and bottom-up parser tree helpers. The declared neural parser capacity of 512 EDUs limits some paths, but serialized/imported/user-created graphs are not uniformly bounded. Convert external validation/serialization walks to explicit stacks with color/state maps; retain recursion only where a validated maximum makes it provably safe. Add a 1,500-node skewed-tree test and explicit cycle tests.

### P2.3 Evidence construction repeatedly scans sentences and leaves

`rdam/rst/base_predictor.py:626-714` assigns each token by scanning sentence ranges and then scanning all leaves, with another fallback scan. This is approximately `O(tokens × (sentences + EDUs))`. Use monotonic interval cursors or `bisect` over validated, sorted boundaries and a direct leaf interval index. Preserve exact coordinate behavior with property tests before benchmarking.

### P2.4 Ingest preparation repeatedly scans its complete inventory

`rdam/rst/ingest/prepare.py:413-544` repeatedly uses `next`/comprehensions over the full inventory to resolve parents, children, linked items, and table anchors. Build immutable `item_by_id`, `children_by_parent`, and anchor indexes once per preparation. Benchmark flat, deeply nested, and table-heavy inventories; acceptance should demonstrate near-linear scaling while preserving semantic digests.

### P2.5 Ingest enrichment and parser-result anchoring rebuild sets/maps inside nested loops

`rdam/rst/ingest/enrichment.py:174-257` scans structural segments for each token/anchor and rebuilds token maps per anchor. `rdam/rst/ingest/parser_result.py:601-734` repeatedly constructs token-ID sets and scans EDUs/tokens for nodes, edges, decisions, and signals. Hoist stable indexes, use interval/bisect traversal for ordered segments, and calculate token sets once. Require byte-identical canonical serialization and a benchmark across 1k/10k/100k tokens.

### P2.6 Duplicate-chain validation is quadratic

`rdam/rst/ingest/validation.py:492-527` walks predecessor chains independently for every duplicate. Use a single color/memoized-root pass so each duplicate link is visited once. Test long valid chains, a self-cycle, a long cycle, and a missing predecessor.

### P2.7 eRST candidate generation recomputes node/signal membership and materializes the whole quadratic space

`rdam/rst/erst/candidates.py:116-318` repeatedly derives node token membership while combining node pairs and signals. `rdam/rst/english/erst/completer.py:96-208` scores in batches but retains every candidate, probability, and logit in memory for the trace. Pre-index token/node/signal relationships. Then decide explicitly whether complete candidate evidence is a mandatory output contract: if yes, use an on-disk/spooled trace for large documents; if no, version a bounded summary contract. Do not silently truncate. Benchmark candidate count, peak RSS, and wall time as node count grows.

### P2.8 BiMPM allocates repeated full tensor copies

`rdam/rst/dmrst_parser/src/parser/bimpm.py:149-169` constructs lists of the same tensors and stacks them across matching perspectives/sequence length. Express these operations with `unsqueeze`, broadcasting, and `expand` where safe. This can materially reduce accelerator memory without changing inference maths. Acceptance requires numerical equivalence (including gradients where training remains supported) and peak-memory measurements on representative released checkpoints.

### P2.9 Batch construction eagerly duplicates every field into separate chunk lists

DMRST `predictor.py:200-242` and UniRST `predictor.py:487-548` materialize six/seven full lists of chunks before zipping them. Iterate `itertools.batched`/slices by one shared range and construct each `Data` batch once; compute progress total with ceiling division. Also replace `[{}] * len(texts)` at DMRST line 278 and UniRST line 656 with a typed `None` placeholder plus a final completeness assertion—the current dictionaries alias even though today's code overwrites every slot.

### P2.10 Bottom-up parsing uses `pop(0)`

`rdam/rst/universal_parser/src/parser/parsing_net_bottom_up.py:160,241,246` shifts a list repeatedly. Use `collections.deque.popleft()` or an integer cursor. Add an action-sequence parity test before benchmarking long EDU sequences.

### P2.11 DocLang local paths are quadratic in same-name siblings

`rdam/rst/doclang/loader.py:70-91` builds a same-tag sibling list and searches `.index(cur)` for each element. Carry occurrence counts during traversal or pre-index sibling ordinals. **Before implementing this change, reverify the current DocLang specification and upstream valid fixtures as required by the project rule; this audit did not change the adapter.**

### P2.12 Provider declarations repeatedly hash source files and query package metadata

`source_identity()` and `_package_version()` repeat the same disk/metadata work in `dung/provider.py:46-61`, `ibis/provider.py:39-52`, `pdtb/provider.py:58-73`, `sdrt/provider.py:56-71`, `toulmin/provider.py:65-78`, and `walton/provider.py:77-90`. These values are process-invariant. Add `@cache`, or better, consolidate the six structurally identical provider-provenance helpers in one internal module. Do not cache secret/configuration availability.

### P2.13 IBIS derives indexes repeatedly

`rdam/ibis/grammar.py` performs repeated linear node/edge lookup while building the deliberation map, and `from_payload` invokes attachment validation after construction even though `__post_init__` already validates. Build local immutable indexes once per operation and remove the duplicate complete validation. Test duplicate IDs, missing endpoints, cycles, and byte-identical payload output.

### P2.14 Viewer rendering combines repeated SQLite connections with monolithic string construction

`rdam/rst/rstviewer/rstweb_sql.py` opens a connection per small query, while `rstviewer/main.py:76-494` performs many queries and builds one large HTML/JavaScript string through repeated concatenation. Pass one render-scoped connection/read model through layout, and separate typed layout calculation from template rendering. This is a local single-process design—no pool/service layer is warranted. Snapshot representative HTML/PNG geometry before changing it.

### P2.15 Serialization and Turtle export repeat whole-output work

`rdam/rst/contracts/serialization.py:36-52` calls `dataclasses.asdict`, which recursively deep-copies, then recursively traverses the copy again. Walk dataclass `fields()` directly. `rdam/rst/graph/export.py:182-213` filters the entire accumulated Turtle line list after each edge, producing quadratic work, and only partially escapes literals (`:167-170`). Append optional lines conditionally and use an RDF-aware literal encoder/library. Verify quotes, backslashes, tabs, control characters, Unicode, and parse the generated Turtle in tests. The placeholder `example.org` ontology/base URIs must be resolved against the canonical ontology authority before changing them; do not invent replacements.

## P3 — complete mechanical modernization backlog

These changes are individually small and should be completed after the P1 fixes, in reviewable rule groups rather than one opaque auto-fix commit.

### P3.1 Expand the Ruff gate to the project's actual standard

Current configuration (`pyproject.toml:136-145`) selects only `E,F,B,W,BLE`. The audit's extended run found:

| Rule | Count | Recommended disposition |
|---|---:|---|
| `UP037` quoted annotations | 38 | Remove; Python 3.14 lazy annotations make the quotes unnecessary. Do not add the future import. |
| `RUF059` unused unpacked variables | 24 | Name deliberately or use starred placeholders; inspect for lost values first. |
| `RUF052` used dummy variables | 24 | Rename to express meaning. |
| `RUF022` unsorted `__all__` | 18 | Auto-fix after confirming public order is not documented. |
| `PERF401` manual list construction | 17 | Convert to comprehensions only where readability improves and side effects are absent. |
| `RUF067` non-empty `__init__` modules | 13 | Keep intentional public façades; configure explicit per-file exceptions with reasons rather than blanket silence. |
| `SIM108` ternary candidates | 9 | Apply only to genuinely clearer expressions. |
| `SIM201` negated equality | 7 | Replace with `!=`. |
| `UP032` old string formatting | 6 | Use f-strings. |
| `C408/C416/C419/C420/C409` collection construction | 17 | Mechanical simplification. |
| `SIM102/SIM114/SIM105/SIM113/SIM118/SIM115/SIM300` | 17 | Review and simplify; `SIM115` is also a resource-lifetime issue. |
| `RUF031/RUF023/RUF055/RUF039/RUF007/RUF005/RUF069/PIE810` | 15 | Apply by rule with targeted tests. |
| Ambiguous Unicode (`RUF001/2`) | 11 | Preserve intentional mathematical typography; replace confusable punctuation in executable/user-facing strings. |

Recommended gate set: add `UP`, `PERF`, `C4`, `PIE`, and selected `SIM`/`RUF` rules, with narrowly documented per-file ignores only where semantics/readability require them. Do not mass-enable fixes and assume green means correct.

### P3.2 Turn Pyright strictness into reality

`pyproject.toml:157-179` sets Python 3.14 but does not set `typeCheckingMode = "strict"`; this explains how large neural modules with untyped call surfaces still produce a zero-warning run. Ruff found 280 annotation issues, concentrated in the DMRST/UniRST parser internals and viewer SQL/layout code.

Action:

1. add strict mode for `rdam/`;
2. type one coherent boundary at a time (model configuration, batch `Data`, segmenter protocol, classifier protocol, viewer SQL rows);
3. replace `Any` with structural protocols, typed dictionaries/dataclasses, or library types where knowable; and
4. never suppress a real issue with `type: ignore` or a broad config exclusion.

Acceptance is `0 errors, 0 warnings, 0 informations` **under strict mode**, plus unchanged tests and model smoke checks.

### P3.3 Use Python 3.14/stdlib idioms already chosen by the project

- Replace `zip(self.spans, self.spans[1:], strict=False)` with `itertools.pairwise(self.spans)` in `rdam/pdtb/relations.py:116`.
- Replace `max([len(x) ...])` with a generator in both `modules.py` files; use `output.new_zeros(...)` instead of constructing CPU tensors and moving them.
- Replace `sum([int(v) ...])`-style temporaries and unnecessary `list(set(...))`/`.keys()` calls exposed by the Ruff groups.
- Add `@override` to concrete implementations of declared base/protocol methods where runtime verification helps catch drift.
- Use direct, unquoted self-references under Python 3.14 for all 38 `UP037` locations.
- Replace runtime `assert` used for input/config validation (`utils/du_converter.py:16`; neural module break/order checks) with typed exceptions. Keep assertions only for genuinely impossible internal states, with an invariant message.
- Make `str2bool` (`base_predictor.py:22-28`) reject unknown strings instead of converting every typo to `False`; define the accepted tokens explicitly.

### P3.4 Remove dead, duplicate, or misleading surface

- `_verify_inventory` and `_structure_path` in `rdam/rst/ingest/_harvest.py:596,958` have no callers under `rdam/` or `tests/`; remove them after confirming they are not intentionally public.
- `ProductionIngestor.analyse(... diagnostic_policy=...)` at `ingest/service.py:268-277` never reads the argument. Either wire it into the exact failure-serialization boundary or remove/deprecate the parameter; do not keep a no-op public argument.
- `PromotionReceipt` is exported by `rdam.rst.model_loading` but has no production/test consumer outside its definition/export. Reassess whether it belongs in production under the project's no-release-theatre rule; retain only runtime model-integrity contracts that serving actually needs.
- Remove duplicate cue-processing paths in `relations/primer.py` and duplicate source/version boilerplate across the six LLM-backed providers.
- `toulmin/argument.py` checks for missing warrant after the contract has already made a warrant non-empty; remove unreachable validation after proving the schema invariant.

### P3.5 Normalize small public-contract inconsistencies

- Toulmin and Walton reject only `None` text while SDRT/PDTB reject blank text; define one shared non-empty-text boundary for all raw-text LLM providers.
- `parse_documents` creates `DiscourseMarkerPrimer` inside the per-document loop and records one averaged batch duration as each document's parsing time (`rst/parser.py:501-572`). Reuse the stateless primer and label batch-average timing honestly, or capture per-item timing only if it can actually be measured.
- `rstviewer/rstweb_classes.py` has a frozen segment value containing a mutable token list; use a tuple. Rename internal `NODE` to `Node` with a compatibility alias only if it is genuinely public.
- `walton/schemes.py` declares a `Final[Mapping]` backed by a mutable dictionary; expose an immutable mapping.
- `erst/checkpoint.py` and other broad `except Exception` blocks should catch expected data/IO/schema failures and let programming errors propagate with context.

## Architectural opportunities (large, deliberate changes)

These are worth considering, but should not be mixed into the correctness patch set.

### A. Split runtime eRST contracts from workbench/training evidence

`rdam/rst/contracts/erst.py` contains serving-time candidate/score/decoder evidence alongside training-selection, private-corpus, evaluation, and promotion structures. Audit every runtime import, retain the minimal checkpoint/runtime manifest and inference evidence in `rdam/`, and move experimental/training-only contracts to `workbench/`. This preserves the protected production/workbench boundary without changing trained architecture.

**Decision criterion:** if a class is required to validate or interpret an installed production checkpoint, it stays in production; if it only describes candidate selection, private corpora, experiments, or promotion process, it moves.

### B. Consolidate the two parser-family infrastructure implementations

DMRST and UniRST contain near-duplicate `modules.py`, `segmenters.py`, `metrics.py`, batching, and parsing-net logic. The duplicated defects above demonstrate real drift cost. Extract shared, fully typed infrastructure only where behavior is genuinely identical: metric kernel, segmenter protocol/implementations, device/dtype resolution, window slicing, batch iteration, and immutable `Data` transport. Keep family-specific architecture, relation inventories, trained dimensions, and inference maths separate.

**Decision criterion:** extraction must pass state-dict key compatibility tests and numerical parity on released fixtures. Do not rename model parameters or alter layer topology merely for elegance.

### C. Replace the viewer's database-shaped render pipeline with a typed in-memory layout

The renderer imports one document into temporary SQLite and then immediately queries it many times to calculate a static layout. A typed in-memory RS3 document/layout model would remove database churn, make invariants testable, and sharply simplify HTML generation. Preserve the editor-style SQL module only if mutation APIs remain a real supported product surface.

**Decision criterion:** render snapshots and geometry tests must prove parity before deleting the SQLite path.

## What is already modern and should be preserved

The report is not a recommendation to rewrite working modern code. Notable strengths include:

- PEP 695 type aliases/generics in strict contracts;
- widespread frozen, slotted dataclasses for value types (after deep-mutability gaps are fixed);
- discriminated Pydantic unions and strict `extra="forbid"` contracts;
- `Protocol`/`runtime_checkable` boundaries for parsers, providers, and adapters;
- structural pattern matching where it clarifies provider/family dispatch;
- `itertools.batched` already used in evidence batching;
- `zip(..., strict=True)` used at coordinate-sensitive joins;
- `datetime.now(UTC)`, `pathlib`, `@cache`, `@torch.inference_mode`, and atomic cache replacement;
- explicit transient retry ownership and attempt accounting in `_llm.py`; retain this rather than replacing it with opaque SDK retries;
- the production-boundary scanner, which currently confirms no `rdam/` import of offline/dev/workbench packages.

Also preserve the synchronous notebook bridge in `rdam/rst/__init__.py` unless replacement tests prove equivalent behavior under a running event loop. Its thread executor is solving a real sync/async compatibility problem, not merely using an old idiom.

## Implementation sequence

### Wave 0 — pin every demonstrated defect with a failing regression test

**Touches:** tests only.
**Success criteria:** one focused failing test for P1.1 through P1.10, plus mutation tests for P1.11 and environment-side-effect tests for P1.12. Each test must fail for the stated reason on current code.

### Wave 1 — repair correctness without architecture changes

**Touches:** public-surface/environment resolution; both metrics files; both segmenters; both parsing nets/modules; graph export; viewer resource/error handling; no-op bias/policy arguments.
**Success criteria:** Wave 0 tests pass; released-checkpoint fixture inference remains numerically identical except where the test proves current behavior wrong; NetworkX retains parallel edges; render failures are typed and leak-free.

### Wave 2 — make contracts and configuration truthful

**Touches:** machine registry, cached ontology/config mappings, frozen contracts, LLM dotenv discovery, device/dtype resolver, pointer configuration.
**Success criteria:** public mutation attempts fail; capability checks do not change `os.environ`; every accepted configuration constructs and runs, every rejected value fails at the boundary; source/wire serialization remains compatible or is explicitly versioned.

### Wave 3 — remove repeated asymptotic work

**Touches:** ingest prepare/enrichment/parser-result/validation, `BasePredictor`, eRST candidates/completer, batching, BiMPM, DocLang paths, IBIS, viewer, graph serialization.
**Success criteria:** semantic digests and canonical serialized outputs are identical on the existing corpus; benchmark tables include input size, wall time, and peak RSS/device memory; scaling curves demonstrate the intended complexity improvement rather than only a tiny-fixture speedup.

### Wave 4 — enforce Python 3.14 quality mechanically

**Touches:** Ruff/Pyright configuration and the files each enabled rule exposes.
**Success criteria:** strict Pyright is clean; the selected extended Ruff rules are clean without blanket suppressions; all 38 quoted annotations are removed; no future-annotations import is added; all existing gates remain green.

### Wave 5 — make the three architectural decisions separately

**Touches:** production/workbench eRST boundary, shared parser infrastructure, viewer architecture.
**Success criteria:** each decision has its own plan, compatibility constraints, benchmarks, and migration tests. Do not combine these into a single modernization branch.

## Required final verification for an implementation pass

At minimum, run and report the actual output of:

```text
pixi run lint
pixi run typecheck
pixi run test
pixi run test-all
pixi run -e default production-boundary
pixi run build-production
pixi run validate-production-artifacts
pixi run -e production production-clean-install
```

Add targeted model-fixture checks for both DMRST and UniRST configurations touched, renderer PNG/PDF checks where Playwright is available, strict Turtle parsing, deep-tree stress tests, and before/after benchmarks for every performance claim. A clean foundational gate is necessary but not sufficient: model parity, output-contract fidelity, installed-wheel behavior, and performance evidence must be reported separately.

## Bottom line

The correct strategy is **repair first, then consolidate, then mechanize**. The codebase already uses many Python 3.14-era techniques well; the gap is inconsistency. Fix the 12 P1 groups before broad auto-modernization, because several apparently stylistic smells (`RUF059`, chained indexing, unused constructor arguments, string sentinels) are exposing real wrong-result paths. Once those are pinned and repaired, the P2 index work and strict Ruff/Pyright rollout can be completed without obscuring semantic changes.

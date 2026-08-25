# Finding-to-Evidence Matrix

This matrix is the pre-edit ownership gate. “Owner” is the concrete implementation boundary in this
solo repository. Task IDs refer to `tasks.md`.

| ID | Defect | Owner / tasks | Required regression evidence | Release gate |
|---|---|---|---|---|
| F-01 | False projection text/spans | `_rst_common/_flatten.py`, format mappers; T008-T012 | Nested round-trip + Parseval + eRST consumer + hierarchy tests | G-FORMAT |
| F-02 | DocLang metadata contamination | `doclang/harvester.py`; T015-T017 | Current `description` fixture plus nested head/tail matrix | G-DOCLANG |
| F-03 | Wrong software version | `_rst_common/_runtime.py`, `parser.py`; T013-T014 | Distribution metadata integration test at 4.0.0 | G-PROVENANCE |
| F-04 | Silent corpus drops and candidate split leakage | `erst/corpus.py`, train script; T027-T032 | Malformed-source fail-closed and document/hash-disjoint official split tests | G-CORPUS |
| F-05 | DocLang page/group option divergence | `doclang/eligibility.py`, boundaries; T015-T018 | Option matrix across harvest/page/group/heading/fallback | G-DOCLANG |
| F-06 | 338 hidden type errors | both parser `src` trees and `pyproject.toml`; T045-T047 | Independent baseline then full-tree Pyright zero | G-STATIC |
| F-07 | Python 3.14 TorchScript/vulnerable torch | dependency pins and eRST model imports; T005, T041, T049 | warnings-as-errors import/neural/CPU/MPS; clean audit | G-RUNTIME, G-AUDIT |
| F-08 | SEP used as lexical end | `erst/neural_scorer.py`; T037-T038 | Exact fast-token boundary indexes padded/unpadded | G-ERST |
| F-09 | Global warning/logger suppression | package init and originating configs; T048-T049 | Exhaustive suppression scan + warnings-as-errors import/tests | G-RUNTIME |
| F-10 | Markdown false-green scope | `pyproject.toml`, authoritative Markdown; T050-T052 | Tracked-file manifest and full intended lint pass | G-DOCS |
| F-11 | Vulnerable setuptools | build pin/lock; T005, T066 | `pip-audit` and fresh archive build/inspection | G-AUDIT, G-BUILD |
| F-12 | `.dclg.xml`/count drift | fixtures/tests/docs; T019-T020 | Exact upstream-name set equality and derived count | G-DOCLANG |
| N-01 | Cache omits source basename | `_rst_common/_cache.py`; T021-T023 | Equal bytes/different names yield distinct provenance/cache entries | G-CACHE |
| N-02 | Cache schema does not invalidate false entries | cache identity + envelope versions; T007, T022 | Pre-bump fixture cache miss | G-CACHE |
| N-03 | Training/inference candidate generators differ | `erst/candidates.py`, completer/train; T025-T026, T033 | Candidate identity property tests across all modes | G-ERST |
| N-04 | Gold affects candidate existence/negative truncation | same; T025-T026, T033 | Gold-shuffle invariance and complete evaluation-space test | G-ERST |
| N-05 | DAG/degree/distance/ancestry/primary filters violate eRST | `erst/decoder.py`; T034-T036 | Cyclic/non-projective/concurrent/reverse/primary-overlap conformance matrix | G-ERST |
| N-06 | Signal heuristic is insufficient and non-overlapping | `erst/signals.py`; T024-T026 | Current type/subtype coverage and overlapping-anchor tests | G-SIGNAL |
| N-07 | Coarse-only relation labels | candidate/scorer/ontology boundary; T039-T040 | Raw inventory preservation and reversible ontology projection tests | G-SCORER |
| N-08 | No candidates/zero steps/missing checkpoint can succeed | corpus/train receipt; T031-T032, T042 | Explicit failure tests for each empty/missing state | G-TRAIN |
| N-09 | `model.pt` is incomplete/unloadable/unsafe | `erst/checkpoint.py`; T041-T044 | Complete safetensors member/hash/strict reload parity tests | G-BUNDLE |
| N-10 | Parser can create random eRST heads | `parser.py`, completer; T043-T044 | Invalid/raw/missing checkpoint capability-error tests | G-BUNDLE |
| N-11 | External evidence gate incorrectly blocks local implementation | research contracts/docs; T054-T057 | Internal scorer/protocol tests and executable runner with no external permission field | G-COMPARISON |
| N-12 | No completed technology comparison or model selection | experiment pipeline; T054-T064 | All mandatory implementations/receipts, statistics, and one-time final evaluation | G-COMPARISON |
| N-13 | Implicit `.env` discovery fails on Python 3.14 | `erst/environment.py`; T006 | Explicit-root canonical/fallback/no-log tests | G-SECRETS |
| N-14 | Slow/tokenizer warning paths | tokenizer bundle/import boundaries; T037, T041, T049 | Fast-token parity and full warnings-as-errors matrix | G-RUNTIME |
| N-15 | No package/archive/clean-machine proof | release verifier; T065-T071 | Archive manifest, clean install, representative persisted outputs | G-RELEASE |
| N-16 | Graphify package/skill drift and lossy raw extraction | Graphify release evidence; T070 | Exact package/skill version parity plus raw-extraction and persisted-graph integrity diagnostics | G-RELEASE |

## Gate definitions

- **G-FORMAT**: all three wire-schema and downstream semantic tests pass.
- **G-DOCLANG**: current spec/validator/upstream fixture set and option parity pass.
- **G-PROVENANCE**: installed 4.0.0 and source revision are distinct and correct.
- **G-CACHE**: basename/schema/options identity and stale-cache miss tests pass.
- **G-SIGNAL / G-ERST / G-CORPUS / G-SCORER / G-TRAIN**: formal conformance, complete candidates,
  governed document splits/raw labels/repository scorer, and fail-closed receipts pass.
- **G-BUNDLE**: safetensors completeness, hashes, strict reload, capability boundary, and parity pass.
- **G-STATIC / G-RUNTIME / G-DOCS**: zero type/lint/suppression/warning debt and complete doc scope.
- **G-COMPARISON**: internal scorer/protocol validation, complete mandatory implementations,
  reference/candidate runs, calibration, statistics, and one-time final evaluation all pass; no
  external artifact controls implementation permission.
- **G-AUDIT / G-BUILD / G-SECRETS / G-RELEASE**: no actionable audited vulnerability, forbidden
  archive member, secret disclosure, Graphify version/integrity defect, or undisclosed failed/skipped
  exact-candidate check.

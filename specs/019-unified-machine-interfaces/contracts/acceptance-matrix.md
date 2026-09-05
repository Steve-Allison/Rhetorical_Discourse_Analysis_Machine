# Acceptance Matrix

**Status**: Required implementation checks; none is marked passed by this plan.

P = direct Python; C = installed CLI subprocess; H = real loopback HTTP.
Fixtures live under tests/interfaces/fixtures/ unless a native suite owns them.
All internal execution is real. External-boundary fixtures do not prove live
model quality; model-backed rows remain separate and cannot pass by skipping.

| ID | Inputs / variation | Required observable result | Route |
|---|---|---|---|
| A01 | Help/version/schema/capabilities with no credentials/weights | Zero model construction, weight load or network; all seven boundaries discoverable | P/C/H as applicable |
| A02 | Strict request/config codecs; binary DocLang archive | Byte/metadata identity round trip; reject unknown versions/keys, duplicate keys, bad Unicode/base64/non-finite numbers | P/C/H |
| A03 | text, edus, markdown, docling_json, doclang_xml, doclang_archive | Correct inventory, retained content, warnings and projection mappings for each form | P/C/H |
| A04 | Several techniques with shared/distinct requirements | Exactly one inventory and one projection per distinct requirement; preparation remains model-free | P/C/H |
| A05 | Explicit order and duplicate/unknown selections | One outcome per requested boundary in order; invalid selection rejected before inference | P/C/H |
| A06 | RST tree and eRST graph, real local artifacts | Both addressable as RST outcome; complete native candidates/decisions/scores retained | P/C/H; model-backed |
| A07 | All four LLM techniques, fixed external responses | Real provider/schema/source validation; canonical analytical parity with declared execution exclusions only | P/C/H |
| A08 | Focused opted-in actual model/source cases | Source support and native meanings checked; concrete errors fixed; unavailable checks reported | Real providers + cold critique |
| A09 | Valid Dung/IBIS, structured-only and mixed inputs | No invented prose/structure; deterministic identity; native semantics intact | P/C/H |
| A10 | Missing/malformed structure and retained upstream success | Correct unavailable/failed outcomes; carried success cannot improve new completion status | P/C/H |
| A11 | Inconsistent/forged lineage; retained eRST vs requested RST | Reject before execution; no inferred derivation | P/C/H |
| A12 | Shared/per-technique/model/policy precedence and cache variations | Effective values reach actual providers; schema/policy/envelope/config identity prevents stale hits | P/C/H |
| A13 | Complete/partial/unsuccessful/internal failure | CLI 0/3/4/1 respectively; HTTP 200 for aggregates, 500 for defect; Python defect propagates | P/C/H |
| A14 | CLI input modes, literal dash paths, stdin ownership, duplicate flags | Unambiguous acquisition; usage errors exit 2 with safe stderr, no inference | C |
| A15 | Existing/symlink/hardlink/input-alias output; force; publication failure | No unintended clobber; atomic valid output or preserved prior bytes; no error JSON overwrites result | C |
| A16 | Broken pipe, Ctrl-C, disk failure, partial-result publication failure | Documented exit precedence; no claim of atomic pipes or hard thread cancellation | C |
| A17 | HTTP invalid Host/Origin/media/framing/body size/deadline | Documented rejection, no model call; distinguish pre-ASGI parser response from canonical application error | H |
| A18 | Busy POST, disconnect and concurrent discovery | One admitted POST; discovery stays responsive; slot retained until running work finishes | H |
| A19 | Historical aggregate/native v1; missing required digests | Historical meanings/digests preserved; damaged artifacts rejected; no invented origin/assessments/status | P/C/H |
| A20 | All AI guide formalisms, failed/unavailable and historical entries | Present pointers resolve; no confidence/truth/consensus invention; corrected states explained inline | P/C/H |
| A21 | Full/subset selection and summary on a saved aggregate | Original status/context retained; exact selected native bytes; every exclusion named; zero inference/acquisition | P/C/H |
| A22 | Every NI-01–NI-04 case in native-integrity.md | Reproduced prior defects are corrected; valid/uncertain/historical behavior remains distinct | Native + P/C/H |
| A23 | Fresh wheel: core, core+http, formats, formats+http | Correct optional boundaries, schema/help consistency, real rdam entry point; rdam-rst absent | Installed P/C/H |
| A26 | Genuine irrelevant quotes, wrong speaker, negation, modality, reconstruction and missing context | Mandatory adversarial assertions pass through real providers; valid spans do not mask semantic errors | Native + P/C/H; model-backed |
| A28 | Changed implementation, tests and actual outputs | Cold critic identifies concrete defects and test gaps; substantiated findings repaired and regression-tested | Cold critique + executed tests |

## Evidence rules

Count inventory/provider calls using real profiling/instrumentation of executed
code or public declaration-based integration providers; do not monkeypatch
Machine/ProductionIngestService into returning canned successful aggregates.
Production parity specifically uses production providers. Test failures at truly
external boundaries (filesystem publication/network responses) separately.

Every normative field/CLI option gets positive and negative cases via a
parameterized inventory in tests/interfaces/test_contract_inventory.py; A12/A14
are not satisfied by testing one representative flag. All six forms need real
fixtures; all seven boundaries need real-provider coverage. Cross-product
expansion is required where a source form changes projection/evidence behavior,
not an invented environment matrix for its own sake.

A24, A25 and A27 were withdrawn by the owner's simplification instruction.
[analytical-quality.md](analytical-quality.md) specifies focused semantic checks
and cold critique, not a reference/scoring system. One real-provider run may
supply native outputs for inspection and transport replay; replay proves
preservation, not another model run.
Live interface calls may vary and cannot be equated by deleting semantic fields.

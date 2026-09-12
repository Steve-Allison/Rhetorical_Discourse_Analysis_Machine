# Implementation tasks

- [x] T001 Record baseline and both constitutional checks in baseline.md; create CSM feature artifacts.
- [x] T002 Compile manifest-driven typed Central projection in tools/compile_concept_index.py; package and validate rdam/concepts/index.py.
- [x] T003 Implement immutable contracts and complete surface accounting in rdam/concepts/contracts.py and surfaces.py.
- [x] T004 Implement deterministic lexical matching, supplied candidates and evidence reuse validation in rdam/concepts/linker.py.
- [x] T005 Verify ontology/matching/Unicode/evidence and all six source forms in tests/concepts.
- [x] T006 Expose shared Python/CLI/HTTP operations, JSON schemas and self-contained JSONL export; verify parity and rejection.
- [x] T007 Implement CSM manifest resolver and plate adapter with exact locator reconciliation.
- [x] T008 Persist reviewed mentions through CSM typed authoring; retrieval 5.3 schema/readers/validators/docs; verify no automatic promotion or historical invention.
- [x] T009 Add downstream consumer and native-evidence join example; verify real exported inputs.
- [x] T010 Freeze evaluation corpus/independent expected annotations before running experiment.
- [x] T011 Run isolated docling-nlp 1.4.0 comparison, verify offset units, and report all requested measurements/recommendation.
- [x] T012 Run RDAM/CSM required checks, local package/install integration, documentation checks and graph refresh; record actual results.

## Verification outcome

All implementation and verification commands have been executed and their actual
results are recorded in verification.md. The authorized normal dependency/RST lock
cutover passed installation, real model compatibility and dynamic preflight. Full
CSM tests produced 1141 passes and one subsequently repaired test expectation; the
repair passed its four-test module rerun. Paid provider checks remain skipped.
Corpus CI still reports 92 errors and 73 warnings, including historical evidence
under the previous lock. A checked verification task does not mean corpus CI passed.
Source plates and authored wiki content were preserved; corpus migration was not run.

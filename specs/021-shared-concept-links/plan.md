# Implementation plan

Approved scope: [specification](spec.md). Python 3.14, existing Pydantic/canonical hashes,
shared ingestion, standard local files. No runtime model or additional production dependency.

| Phase | Files | Completion criterion |
|---|---|---|
| A | specs/021-shared-concept-links; CSM feature specification | Baseline revisions/dirty state retained; constitutional design checks recorded |
| B | rdam/concepts/index.py; tools/compile_concept_index.py; rdam/resources/concept-index.json | All declared domains compile; malformed references fail |
| C | rdam/concepts/contracts.py, surfaces.py, linker.py; tests/concepts | Exact mentions/candidates across six source forms; stale evidence rejected |
| D | rdam/concepts/serialization.py; rdam/cli.py, http.py; schemas | Python/CLI/HTTP parity and schema rejection |
| E | CSM src/csm/central_ontology.py, authoring, source bridge, schemas/retrieval.py, retrieval_projector.py | Reviewed plate evidence persists through actual authoring and retrieval 5.3 |
| F | workbench/experiments/concept_linking | Fixed annotations, reproducible isolated 1.4.0 comparison and measured recommendation |
| G | tests, affected docs, examples, package builds, graph outputs | Actual required check results and installed CSM consumption reported |

## Constitution check

RDAM constitution 2.0.0: design passes evidence-before-claims (tests and measured
experiment), production quality (strict typed public contracts), solo-local simplicity
(no services/cache/database), honest verification (real operations), and canonical
contracts (Central-only meaning, generated projection). The explicitly approved package
is a shared analytical utility, not an eighth technique. Existing native outputs remain
separate. Implementation conformity is pending verification, not certified by this plan.

## Execution

A precedes B; B precedes C/D; E consumes C/D; F uses C. G closes all phases.
Preserve current uncommitted Feature 020 work and CSM Feature 014 work. No branches,
commits, corpus writes or publication are required to implement this plan.

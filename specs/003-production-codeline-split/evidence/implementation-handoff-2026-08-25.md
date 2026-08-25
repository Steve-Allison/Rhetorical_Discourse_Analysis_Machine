# Feature 003 implementation handoff — 2026-08-25

## Confirmed outcome

Create a smaller importable `isanlp_rst` production distribution for real RST/eRST analysis. Keep corpus preparation, training, evaluation, benchmarking, experiments, research, and model creation/promotion in one repository-only offline workbench. Feature 002 production ingest remains independent and production-owned.

## Implemented and observed

- Production/offline source moves are complete for evaluation, segmentation training, eRST training/corpus/sampling, both parser-family corpus managers/builders, trainers, config readers, and run orchestration.
- Production `ParserInput` retains restricted legacy released-inventory reconstruction without importing corpus/training modules.
- Root Pixi has independently solved `production` and `offline` environments; the nested research Pixi files are removed.
- Setuptools publishes only `isanlp_rst`; wheel and sdist inspection found zero forbidden members.
- eRST bundle creation is offline-only; production retains validation/loading.
- Strict general model manifest, validation, atomic promotion, receipt, and rejection tests are implemented.
- Five cached released models were APFS-cloned, fully rehashed, and promoted to `/Users/steveallison/.cache/isanlp_rst/model-releases`; all five loaded on CPU with zero offline modules imported. Receipts: `model-promotion-receipts.json`.
- Detached pre-split HEAD `0781304` CPU/MPS parity baseline is recorded. Current CPU and MPS comparisons both returned `differences: []`, `valid: true`.
- Fresh artifact hashes: wheel `d6fc3320170bfbb0a32143277cf51fa1cc665b64059f11b305b12247da6eb9e1`; sdist `323be9bd26f77fc97e6bf9aa1e29ac8cea3d9ba49ba3787288a91f436dc36207`.
- Exact wheel installed outside the repository and performed a real promoted gumrrg parse; import resolved from temporary `site-packages`; offline modules remained absent.
- Checks observed: Ruff clean; Pyright `0 errors, 0 warnings`; non-slow suite `864 passed, 73 deselected`; boundary `valid: true` in about 0.8 seconds; promotion suite `6 passed`.

## Convergence findings appended to tasks.md

Implement T048–T054, then rerun convergence:

1. Exhaustive/ambiguity-failing ownership authority and negative tests.
2. Truly production-only exact-wheel acceptance across every required runtime route.
3. Reject loose direct `Parser(model_dir=...)`; verified releases must be the sole local-model route.
4. Integrate exact wheel/sdist receipts into the completion boundary command.
5. Extend parity to provenance, serialization/reload, and optional-format behavior.
6. Start each offline command to a bounded point or record strict quarantine evidence.
7. Independently prove core-only and formats-enabled production installs without offline packages.

## Remaining completion work

- Implement T048–T054 using the existing confirmed design; no new scope decision is needed.
- Run the 73 slow tests and all final gates after the convergence edits.
- Rebuild one final wheel/sdist only after all code and packaged README edits stop.
- Write `evidence/completion.md` with exact final hashes and outputs.
- Mark tasks complete only after their evidence is observed.
- Run `speckit-converge` again until it reports zero gaps.

## Current repository state

All working-tree changes belong to this feature. The current branch remains `master`; do not discard or reset them. The temporary detached baseline worktree may remain registered outside the repository and is not production evidence after the recorded parity capture.

# Feature 004 convergence handoff — 2026-08-31

## Purpose

Resume a fresh, evidence-first review of the remainder of Feature 004 after the
production and ModernBERT code changed. The requested outcome is an exact account
of what Feature 004 still needs implemented. This handoff records only the
starting state and the approved review procedure; it does not certify any changed
code, model release, experiment, task, or distribution artifact.

## Verified starting state

Verified on 2026-08-31 by running `git status --short --branch`,
`git log -5 --oneline --decorate`, `git diff --stat`, `git diff --name-only`, and
`git ls-files --others --exclude-standard` from the repository root.

- Branch: `master`.
- HEAD: `ef56bf0` (`fix: isolate DocLang archive acceptance fixture`).
- Tracking state: `master...origin/master [ahead 6]`.
- Tracked working-tree changes: 19 files, reported by `git diff --stat` as 632
  insertions and 284 deletions.
- The checkout is not a release candidate merely by virtue of these files being
  present. No quality, semantic, promotion, artifact, or receipt conclusion has
  been made in this handoff.

Modified tracked paths reported by Git:

```text
isanlp_rst/annotation_rst.py
isanlp_rst/ingest/identity.py
isanlp_rst/parser.py
isanlp_rst/transformer_parser/model.py
isanlp_rst/transformer_parser/span_encoder.py
scripts/bench.py
scripts/benchmark_modernbert.py
scripts/docling_long_input_determinism.py
scripts/docling_rst_quality_check.py
scripts/train_modernbert_treebank.py
specs/004-production-api-contract/evidence/source-release-gates.json
specs/004-production-api-contract/tasks.md
tests/unit/test_discourse_unit.py
workbench/corpus/dmrst/data.py
workbench/corpus/unirst/data.py
workbench/experiments/central_ledger.jsonl
workbench/experiments/central_ledger.py
workbench/smoke.py
workbench/training/modern/train_tree_parser.py
```

Material untracked areas reported by Git include:

```text
dist/5.0.0/
models/model-releases/modernbert-v1-e5ea56cd620f/
models/modernbert_v1/
specs/004-production-api-contract/evidence/source-release.json
specs/005-modernbert-production-release/
tests/unit/test_gum_dataset.py
tests/unit/test_parsing_net_stability.py
workbench/experiments/runs/20260830_190321_ModernBERT_base_fe95e0/
workbench/experiments/runs/20260830_232045_ModernBERT_base_6fe05f/
workbench/experiments/runs/20260830_235331_ModernBERT_base_9b82f2/
workbench/experiments/runs/20260831_002811_ModernBERT_base_29b22a/
workbench/promotion/modernbert.py
workbench/training/modern/gum_dataset.py
```

The model directories listed by Git contain configuration, tokenizer, relation
inventory, and manifest paths. This handoff has not verified their contents,
membership, weight presence, digests, runtime loading, evaluation evidence, or
promotion status.

## Prior conclusions that must be reverified

Do not carry any earlier conclusion forward as current fact, including:

- whether T136-T145 remain the correct unfinished task set;
- whether Feature 005 satisfies any Feature 004 prerequisite;
- whether the training and evaluation pipeline now uses genuine gold evidence;
- whether any experiment receipt describes the bytes actually produced;
- whether either ModernBERT directory is complete, immutable, promoted, or
  executable;
- whether the existing wheel and sdist correspond to the changed source;
- whether previously persisted Feature 004 gate evidence remains valid;
- whether previously checked Feature 004 tasks still satisfy their acceptance
  criteria after the changed production code.

Each point requires current source, data, artifact, manifest, runtime, and test
evidence before a conclusion is written.

## Approved fresh-session review plan

1. Read `AGENTS.md`, `CLAUDE.md`, every applicable `.claude/rules/*.md`, and the
   complete `speckit-converge` skill before review actions.
2. Read Feature 004 `spec.md`, `plan.md`, `tasks.md`, referenced design artifacts,
   and the constitution completely. Read all Feature 005 artifacts completely
   before treating Feature 005 as a dependency or authority.
3. Snapshot the current Git state and distinguish tracked, untracked, generated,
   model, experiment, evidence, and distribution material. Preserve all existing
   user changes.
4. Read every changed or newly relevant implementation and test file completely.
   Inspect actual model-release members and experiment records rather than
   inferring completion from directory or filename presence.
5. Reconcile all unfinished Feature 004 tasks and re-audit completed tasks whose
   evidence or implementation may have been invalidated by the changes. Map every
   finding to its Feature 004 requirement, success criterion, acceptance scenario,
   plan decision, or constitution principle.
6. Run focused read-only Pixi checks where inspection alone cannot prove current
   behaviour. Do not edit application code during this review.
7. Present a severity-graded convergence table before writing tasks. Append only
   verified remaining work as a new convergence phase in Feature 004 `tasks.md`.
8. Run `speckit-analyze` after any task append and report its actual result.

## Success criteria for the review

- Every remaining Feature 004 obligation is either proved implemented, represented
  by a traceable actionable task, or explicitly identified as external evidence
  that was not verified.
- Previously checked tasks are not accepted solely because their checkboxes remain
  checked.
- No Feature 005, model, experiment, wheel, sdist, receipt, or gate claim exceeds
  the evidence inspected in the fresh session.
- No application code is changed by the review.
- The report lists every authoritative file read completely and every command used
  as runtime evidence.

## Next instruction

After `/clear`, resume with:

```text
Resume the Feature 004 convergence review from
specs/004-production-api-contract/evidence/convergence-handoff-2026-08-31.md.
```

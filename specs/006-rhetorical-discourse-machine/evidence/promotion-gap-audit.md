# Evidence: Promotion Evidence Gap Audit

**Task**: T007 | **Contract**: [../contracts/promotion-evidence.md](../contracts/promotion-evidence.md)
**Requirements**: FR-027, SC-006 | **Date**: 2026-09-01 | **Repository commit**: `28f3779`

Declared input to the workbench-promotion-system feature. FR-027 forbids presuming
existing artifacts complete; this audit reads the promotion machinery in full and states
what it does and does not record, per evidence class.

## Files read in full

| File | Lines | Role |
|---|---|---|
| `workbench/promotion/modernbert.py` | 116 | ModernBERT candidate validation, manifest preparation, promotion entry |
| `workbench/promotion/promote.py` | 169 | Manifest authoring (`write_candidate_manifest`) and atomic store publication (`promote_model_release`) |
| `workbench/experiments/central_ledger.py` | 159 | Append-only experiment/run ledger |
| `pyproject.toml` | 202 | `promote-model` task at `:184` |

`promote-model = "python -m workbench.promotion.promote"` (`pyproject.toml:184`) invokes
`promote.py:main` (`:153-162`), which requires `--candidate` and `--store` and prints a
`PromotionReceipt` as JSON. It runs promotion of an **already-manifested** candidate; it
performs no evidence evaluation of any kind.

## Per-class verdict

| Evidence class | Verdict | Basis |
|---|---|---|
| **Output quality** | **LACKS** | Nothing in the flow evaluates or gates on quality. `write_candidate_manifest` accepts `evaluation_evidence: str \| None` (`promote.py:37`) and stores it verbatim into the manifest (`:79`) — an opaque, unvalidated, unstructured string. As audited, `modernbert.py:66-72` sourced it from `training_receipt.json` if present and **otherwise defaulted to the hardcoded literal `"GUM-12.1.0 Parseval evaluation verified"`** — a claim of verification asserted with no evaluation performed. That fallback is **removed in this feature** (see cross-cutting gap 4): absence of a receipt now yields `evaluation_unavailable_reason`. What remains lacking is unchanged in kind — promotion still proceeds regardless of the evidence's content; no metrics, no gold-data declaration, no baseline, no uncertainty or statistical comparison — none of FR-022's empirical requirements are checked. |
| **Calibration** | **LACKS** | No confidence or probability calibration appears in any of the three files. The manifest schema exposes no field for it; nothing declares calibration explicitly absent, which the contract permits as the alternative. |
| **Latency & resources** | **LACKS** | No timing or resource measurement anywhere in the promotion path. `ExperimentRecord.eval_metrics` (`central_ledger.py:50`) is a free-form `dict[str, Any]` that *could* carry latency figures, but nothing requires, validates, or reads them for a promotion decision. |
| **Runtime & packaging compatibility** | **PARTIAL** | Present: `compatibility_range` (`promote.py:33`, set to `">=5.0.0,<6.0.0"` at `modernbert.py:80`) and `runtime_contract` (`:79`, `"isanlp_rst.parser/modernbert-v1"`) are recorded in the manifest, and `validate_model_release` is invoked three times — on the candidate (`promote.py:112`), on the copy (`:133`), and on the published release (`:137`). Missing: nothing *executes* the release in the production environment topology, and nothing checks the contract's import-time clause (no downloads, no expensive initialization). The separate `production-smoke` / `production-clean-install` tasks (`pyproject.toml:114`, `:116`) do exercise a clean-room install, but they are not wired into promotion and their result is not recorded in the receipt or manifest. |
| **Provenance** | **PARTIAL — the strongest class** | Present and genuinely rigorous for *artifact* identity: per-file `sha256` and `size_bytes` for every member (`promote.py:60-68`), symlink rejection (`:50-51`, `:115-116`), exact role inventory with a hard mismatch error (`:54-59`), `source_model_identity` / `source_revision` from `isanlp_rst.model_authority` (`modernbert.py:81-82`), `created_at`, `producer_version`, canonical-JSON manifest hashing, copy-verify-rename atomic publication with a manifest-hash equality check (`:133-135`), and destination immutability (`:118-119`). Separately, `CentralExperimentLedger.record_run` (`central_ledger.py:91-143`) captures `git_commit`, `dataset_digest`, `hyperparameters`, `checkpoint_digest`, and artifact paths. Missing: **the two halves are not linked.** No field in `ModelReleaseManifest` references a ledger `run_id`, and no ledger record references a `release_id`. FR-023 requires the exact evaluated *corpus partitions* be identifiable from the promotion decision; today one must join the two records by hand, and `dataset_digest` names a dataset, not a partition split. |
| **Licensing** | **PARTIAL** | Present: `licence` and `use_restrictions` are mandatory manifest fields (`promote.py:34-35`, `:77-78`). Missing: there is no *decision* that the licence permits the intended production use — the contract's actual requirement. `modernbert.py:83-84` hardcodes `licence="Apache-2.0"` and `use_restrictions=()` for every ModernBERT candidate without deriving either from the candidate's real provenance or evaluating fitness. The repository's own CC BY-NC precedent (`LICENSE_MODELS`) is exactly the case this would need to catch, and would not. |

## Cross-cutting gaps

1. **No PromotionDecision entity exists.** The contract's §Decision record requires
   candidate identity, per-class evidence, an outcome in
   `promote | withhold | replace | retire`, and a recommendation. The code has
   `PromotionReceipt` (`promote.py:138-147`), which records only that a copy succeeded:
   `candidate_path`, manifest hashes, `verified_files`, `promoted_at`,
   `producer_version`, `succeeded`. There is **no representation of a negative outcome
   at all** — `withhold`, `replace`, and `retire` are unmodelled, so a decision not to
   promote leaves no artifact.
2. **No candidate comparison.** US4 scenario 2 requires multiple candidates for one
   technique be compared on the same declared partitions, metrics, resource
   measurements, and licensing criteria. Nothing in the flow compares anything.
3. **Promotion is not gated on evidence.** The single guard is structural completeness —
   `config.json`, `model.safetensors`, `relation_inventory.json` must exist
   (`modernbert.py:32-37`). This is precisely the failure mode the contract names in its
   opening line: "Installation success, a green engineering test, or the existence of
   artifacts is never promotion evidence."
4. **A destructive side effect in the evidence path — FIXED in this feature.** As
   audited, `modernbert.py:70` called `receipt_file.unlink()`, deleting the training
   receipt after copying it into the manifest string, and `:72` fell back to the
   hardcoded literal `"GUM-12.1.0 Parseval evaluation verified"` when no receipt
   existed — a verification claim with no evaluation behind it. **That literal is in a
   real promoted release**: `models/model-releases/modernbert-v1-e5ea56cd620f/release-manifest.json`
   carries it verbatim as its `evaluation_evidence`. Fixed forward under the project's
   fix-forward rule: a candidate without a receipt now declares
   `evaluation_unavailable_reason` (the manifest contract's honest alternative,
   `release.py:78-79`), and a receipt is moved beside the candidate as
   `<candidate>.training_receipt.json` instead of deleted. Three tests in
   `tests/offline/test_model_promotion.py` pin both behaviours. The manifest regeneration
   at `:63-64` is retained — a manifest is derived data. The already-promoted
   `e5ea56cd620f` release is immutable and keeps its fabricated string; it must be treated
   as **evidence-less** by the promotion-system feature, not re-read as verified.

## SC-006 status

SC-006 requires 100% of promoted providers to carry separate software-compatibility and
output-quality evidence, plus licensing and exact artifact identity. Today: artifact
identity is strong, compatibility is partial, licensing is a hardcoded constant, and
output quality is absent. **SC-006 is not met by the existing flow** and is correctly
the workbench-promotion-system feature's work.

## Note on live runs

Read-only audit. No file under `workbench/` was written, and no promotion, training, or
evaluation was executed — the FR-026 constraint protecting the live task-636 ModernBERT
run was honoured throughout.

# Feature 008: Workbench Promotion System

**Status**: implemented 2026-09-02 | **Authority**: [006 promotion-evidence contract](../006-rhetorical-discourse-machine/contracts/promotion-evidence.md), [006 data model §PromotionDecision](../006-rhetorical-discourse-machine/data-model.md), [006 promotion-gap audit](../006-rhetorical-discourse-machine/evidence/promotion-gap-audit.md) (the declared input) | **Owner ruling**: "build it all" (2026-09-02)

## What was built

| Requirement | Artifact | Proof |
|---|---|---|
| `PromotionDecision` entity: candidate identity, six evidence classes evaluated separately, outcome `promote \| withhold \| replace \| retire`, recommendation with strengths and limitations (FR-021, FR-023, US4) | `machine/rdam/promotion.py` — in the *machine* package so a promoted artifact's decision can be read by production code without importing the workbench (FR-006) | `tests/machine/test_promotion.py` |
| **The gate is structural**: `promote`/`replace` cannot be constructed unless every class is admissible; "installation success, a green engineering test, or the existence of artifacts is never promotion evidence" has no field to be entered in | `PromotionDecision.outcome_is_admissible` validator; `admissible_outcomes` | `test_promote_without_a_baseline_is_unconstructible`, `test_unmeasured_quality_never_promotes`, `test_licence_that_forbids_the_use_blocks_promotion` |
| Output-quality rules by technique kind (FR-022): empirical needs gold data, theory-appropriate measurements, a baseline the candidate exceeds, and uncertainty; formal needs correctness arguments and property tests | `EmpiricalQualityEvidence`, `FormalQualityEvidence`, `UnmeasuredQuality` | `test_not_exceeding_the_baseline_stays_in_the_workbench`, `test_formal_technique_needs_arguments_and_property_tests` |
| Candidate comparison on identical partitions, metrics, and licensing criteria (US4 scenario 2) | `compare_candidates` refuses anything not like-for-like | `TestComparison` |
| Workbench ledger and publication | `workbench/promotion/decision.py` — append-only `workbench/promotions/<technique>/<decision_id>.json`; `publish_decision` writes `<store>/<release_id>.promotion.json` beside (never inside) the immutable release; `pixi run promotion-record` | `tests/offline/test_model_promotion.py` |
| ModernBERT promotion requires a `promote`/`replace` decision naming the exact artifact digest; the decision's canonical JSON *is* the manifest's `evaluation_evidence`; the receipt is preserved, never deleted | `workbench/promotion/modernbert.py`; `pixi run promote-modernbert --decision <json>` | `test_modernbert_promotion_requires_a_promote_decision`, `…_embeds_the_decision_and_publishes_it_beside_the_release`, `…_refuses_a_decision_about_another_artifact` |
| Existing artifacts assessed, not presumed (FR-027) | Retroactive decisions for all three ModernBERT releases in `workbench/promotions/rst/`, each value cited to committed evidence | Verdicts below |

## The retroactive verdicts (2026-09-02)

| Release | Outcome | Deficient classes | Decisive fact |
|---|---|---|---|
| `modernbert-v1-a52b70fbc1a3` (float32, the trained model) | **withhold** | output quality, calibration, latency, licensing | Genuinely evaluated on GUM-12.1.0 — and **test full F1 0.198 (span 0.336) against the archived `gumrrg` release's published 0.487 (span 0.674)** in `README.md`'s performance table; below the repository's own benchmark-script literals too (0.428, 0.465). No uncertainty; calibration and latency unmeasured; no owner licence ruling for the derived weights. |
| `modernbert-v1-462d68b82eae` (float16, promoted 2026-09-02 07:30) | **withhold** | all but provenance | Manifest records "no training receipt and no evaluation evidence supplied". Converted weights were never evaluated. |
| `modernbert-v1-e5ea56cd620f` (removed from the repository store by `c025fdb`; in the user cache) | **retire** | output quality, calibration, latency, licensing | Its only "evidence" is the fabricated literal `"GUM-12.1.0 Parseval evaluation verified"`. |

**Consequence the owner must rule on**: under this contract the machine has **no promoted
RST model**. The RST provider adapter (feature 009) reads the published decision beside
the release it is configured with and reports the RST capability `unavailable(withheld)`
or `unavailable(retired)` accordingly — honestly, never a stub. Two paths restore an
`available` RST capability: (a) train a candidate that exceeds the archived baseline on
the same partition with a confidence interval, measure calibration and latency, and
record a licence ruling; or (b) the owner records a `promote` decision by *supplying*
the missing evidence — the gate does not accept an override without it, by design.

## Not in this feature

Automated collection of latency/calibration evidence (the decision records them; the
tools that measure them are workbench work per technique). The stale
`scripts/benchmark_modernbert.py` baseline literals (lines 236-237) are cited as what
they are — unreferenced — and not corrected here.

## Gates

See [evidence/gates.md](evidence/gates.md).

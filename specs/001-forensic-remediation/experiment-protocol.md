# Frozen eRST Experiment Protocol

**Protocol status**: Design-frozen and execution-blocked before test data access. T053 resolved the
exact GUM V9.2.0 corpus and released baseline code but found no public official scorer artifact to
parity-test. `config/erst/baseline-authority-gum-v9.2.0.json` therefore has
`ready_for_reproduction=false`; no runtime `ExperimentProtocol` may authorize a training, screening,
test, test2, champion, or promotion run until a new validated authority receipt resolves both scorer
identity and parity.

## Authorities and isolation

- Corpus: GUM V12.1.0, commit `22fdf87f9c71c96bcc771461d06e689b1f90020d`.
- Partitions: exact `splits.md` at that commit; document IDs and source hashes must be disjoint.
- Scoring: exact released eRST scorer resolved and hashed in T053; report secondary Span, direction
  (the paper's Nuclearity column), Relation, and Full.
- Candidate generator, signal detector, raw label inventory, ontology projection, and decoder each
  have content hashes in the protocol.
- Training and tuning processes mount only train/dev manifests. Test/test2 paths are not CLI options,
  environment values, imports, or accessible objects in those processes.
- Final evaluation requires a valid `ChampionManifest` hash and writes a durable one-time receipt.

## Reproduced baseline gate

Architecture comparisons are blocked until `google/electra-base-discriminator` at
`1ae76a97c7e84a4e640876a07453fccd636f0667` is reproduced with the paper serialization:

- raw relation hypothesis and compatible-label inventory;
- existing primary relation when present;
- left/right direction and head-EDU distance;
- source/target node or head/sentence spans as specified;
- the target signal marked in text without erasing other signals.

Run seeds 17, 29, 42, 73, and 101 in gold-primary/gold-signal and predicted-primary/predicted-signal
settings. The mean gold/gold scores must each lie in:

| Metric | Published | Allowed interval |
|---|---:|---:|
| Span | 0.389 | [0.369, 0.409] |
| Relation | 0.205 | [0.185, 0.225] |
| Full | 0.184 | [0.164, 0.204] |

Failure stops model selection and triggers corpus/scorer/preprocessing/model diagnosis.

## Mandatory systems

1. Published signal-marked ELECTRA cross-encoder.
2. Existing dual-encoder/bilinear/structural system, corrected only for shared candidates/boundaries.
3. Structural-only calibrated classifier.
4. Text-only cross-encoder.
5. ModernBERT-base and ModernBERT-large signal-aware cross-encoders (two explicit runs).
6. XLM-RoBERTa-large HiDAC-style hierarchical adapter plus contrastive objective.
7. Qwen3-4B DeDisCo-style decoder with parameter-efficient adapters and explicit no-edge outcome.
8. Edge-featured graph-attention system fusing the strongest text representation and complete primary
   tree.
9. Signal-plus-rule deterministic baseline matching the paper's candidate strategy.

No system may be dropped. A verified Python-3.14/MPS, memory, licence, or correctness incompatibility
is represented as a failed run receipt, not deletion. A final literature scan may add but not replace.

## Screening and finalist protocol

- Screening seeds: 17, 42, 73.
- Identical train/dev candidates, scorer, split hashes, raw labels, hardware measurement, and maximum
  optimization budget per model class.
- Dev-only threshold and temperature calibration.
- Every system within 0.02 absolute dev Full of the leading mean becomes a finalist.
- Finalist seeds: 17, 29, 42, 73, 101.
- Hyperparameter searches have a declared finite search space and selection rule stored before runs.
- Test/test2 metrics are unavailable during screening/tuning.

## Required ablations

For every applicable finalist, run controlled removal or substitution of:

- signal marking;
- structural features;
- primary-path encoding;
- sentence/document context;
- graph fusion;
- training hard negatives;
- calibration;
- raw relation labels versus coarse ontology labels.

Each ablation changes exactly one declared factor and reuses candidate/split/scorer inputs.

## Statistical analysis

- Pairing unit: document.
- Statistic: candidate system minus strongest reproduced baseline for official metrics.
- Resamples: 10,000 paired bootstrap samples with a frozen statistic RNG seed.
- Confidence: two-sided 95% percentile interval.
- Multiple comparisons: Holm correction across promoted-system claims.
- Persist document-level score vectors and their hashes so intervals can be recomputed.

## Calibration and decoding

- Tune edge threshold and temperature on dev only.
- Report ECE using protocol-frozen binning and Brier score on identical complete candidate sets.
- The decoder applies formal validity constraints only; thresholding/calibration selects among valid
  candidate predictions.
- CPU and MPS probabilities may differ within declared floating tolerance but decoded edge identities,
  raw labels, directions, and signal associations must be numerically equivalent.

## Resource measurement

- Hardware receipt names machine model, OS, CPU, memory, PyTorch, Transformers, thread settings, and
  power mode when observable.
- Latency: warm-up excluded; p50/p95 across the same document sequence and batch settings.
- Memory: OS peak resident set size is the <=24 GB promotion measure; MPS current/driver allocated
  memory is recorded separately.
- Longest test document must complete without candidate truncation, OOM, or fallback that changes the
  graph.

## Promotion decision

All conditions are conjunctive:

1. mean dev Full improvement >=0.02 over the strongest reproduced baseline;
2. Holm-corrected paired-bootstrap 95% lower bound >0;
3. untouched test Full improvement >=0.01;
4. test Span, direction, and Relation regressions each <=0.005;
5. ECE <=0.05 and Brier no worse than baseline;
6. longest test document completes without truncation/OOM;
7. peak RSS <=24 GB;
8. MPS p95 <=2x ELECTRA;
9. within 0.005 Full ties, selected system is faster and smaller;
10. CPU/MPS decoded graphs are equivalent.

If any condition fails, `PromotionDecision.outcome` is `no_promotion`, canonical checkpoint is null,
and allowed claims exclude “SOTA”, “state of the art”, “champion”, and “best”.

## Test integrity

- The champion selection hash is produced before final evaluation.
- Final evaluation may be run once for that champion/protocol pair.
- A failed final gate is not followed by retuning or evaluating another candidate on test.
- test2 remains a separately reported out-of-domain result and cannot select the champion.
- All failures, interrupted runs, zero-step runs, missing checkpoints, and skipped model components are
  retained in the experiment index.

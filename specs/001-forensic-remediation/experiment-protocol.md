# Frozen eRST Technology Comparison Protocol

**Protocol status**: Design-corrected; implementation and execution incomplete.

The comparison is governed entirely by repository-owned contracts. No external scorer, benchmark
artifact, publication, or reproduction result may grant or deny permission to implement a system.
Selection is fail-closed only at the point of naming a canonical checkpoint: incomplete evidence
prevents selection, never implementation.

## Internal authorities and isolation

- Corpus: private GUM V12.1.0 at commit `22fdf87f9c71c96bcc771461d06e689b1f90020d`.
- Partitions: exact `splits.md` at that commit; document IDs and source hashes must be disjoint.
- Scoring: `isanlp_rst.eval.erst_scorer.ErstScorer`, validated by frozen synthetic and corpus-level
  contract tests for secondary Span, direction, Relation, and Full.
- Candidate generator, signal detector, raw label inventory, ontology projection, and decoder each
  carry content hashes in the executable protocol.
- Training and tuning processes receive only train/dev manifests. Test/test2 paths are absent from
  their CLI options, environment inputs, imports, and runtime objects.
- Final evaluation requires a valid `ChampionManifest` hash and writes a durable one-time receipt.

## Required executable boundaries

The current repository does not yet implement all boundaries in this section; their absence is
remaining work, not a blocked or successful outcome.

- `ExperimentProtocol`: immutable inputs, revisions, hashes, systems, seeds, resource definitions,
  ablations, selection thresholds, and test-isolation policy.
- `ExperimentRunReceipt`: architecture/config hash, seed, partitions, hardware/software identity,
  positive step counts, checkpoint/prediction hashes, metrics, calibration, resources, and failures.
- `StatisticalComparison`: paired document vectors, deterministic 10,000-resample bootstrap,
  confidence interval, and Holm-corrected comparisons.
- `ChampionManifest`: dev-only selection identity and evidence hashes.
- `FinalEvaluationReceipt`: one-time untouched test/test2 evaluation bound to the champion hash.
- `SelectionDecision`: one evidence-backed result per selection threshold and either `selected` or
  `no_selection`.

## Reference systems

The comparison starts with repository-owned reference implementations, not external reproduction:

1. existing dual-encoder, bilinear, and structural scorer;
2. structural-only calibrated classifier;
3. text-only cross-encoder;
4. ELECTRA signal-aware cross-encoder;
5. signal-plus-rule deterministic baseline.

Every reference uses identical candidate identity, partitions, scorer, seeds, and resource
measurement. A failed reference run is retained as a failed receipt and does not prevent other
systems from being implemented or evaluated.

## Candidate systems

1. ModernBERT-base signal-aware cross-encoder;
2. ModernBERT-large signal-aware cross-encoder;
3. XLM-RoBERTa-large hierarchical adapter with contrastive objective;
4. Qwen3-4B parameter-efficient generative edge decoder with explicit no-edge outcome;
5. edge-featured graph-attention fusion using the strongest completed text representation and the
   complete primary tree.

No system may be silently dropped. A local Python 3.14, MPS, memory, licence, tokenizer, or
correctness incompatibility requires a complete incompatibility receipt after the implementation was
attempted far enough to prove the constraint.

## Screening and finalist protocol

- Screening seeds: 17, 42, and 73.
- Identical train/dev candidates, scorer, split hashes, raw labels, hardware measurement, and finite
  optimization budget per comparable model class.
- Threshold and temperature calibration use dev only.
- Every system within 0.02 absolute dev Full of the leading mean becomes a finalist.
- Finalist seeds: 17, 29, 42, 73, and 101.
- Hyperparameter searches have a finite declared space and deterministic selection rule stored before
  runs.
- Test/test2 metrics remain unavailable during implementation, screening, and tuning.

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

Each ablation changes one declared factor and reuses candidate, split, and scorer inputs.

## Statistical analysis

- Pairing unit: document.
- Statistic: candidate system minus the strongest completed repository baseline.
- Resamples: 10,000 paired bootstrap samples with a frozen statistic RNG seed.
- Confidence: two-sided 95% percentile interval.
- Multiple comparisons: Holm correction across candidate-selection comparisons.
- Persist document-level score vectors and hashes so every interval is reproducible.

## Calibration, decoding, and resources

- Tune edge threshold and temperature on dev only.
- Report ECE with protocol-frozen binning and Brier score on identical complete candidate sets.
- The decoder applies only the governed graph-validity constraints; thresholding and calibration
  select among valid candidate predictions.
- CPU and MPS probabilities may differ within declared floating tolerance, but decoded edge
  identities, raw labels, directions, and signal associations must be equivalent.
- Record warm-up-excluded p50/p95 latency, OS peak resident set size, MPS allocator memory, machine
  identity, OS, CPU, memory, PyTorch, Transformers, thread settings, and observable power mode.
- The longest test document must complete without candidate truncation, OOM, or graph-changing
  fallback.

## Canonical checkpoint selection

All conditions are conjunctive:

1. mean dev Full improvement at least 0.02 over the strongest completed repository baseline;
2. Holm-corrected paired-bootstrap 95% lower bound above zero;
3. untouched test Full improvement at least 0.01;
4. test Span, direction, and Relation regressions each at most 0.005;
5. ECE at most 0.05 and Brier no worse than the baseline;
6. longest test document completes without truncation or OOM;
7. peak RSS at most 24 GB;
8. MPS p95 at most twice the reference cross-encoder;
9. within 0.005 Full ties, select the faster and smaller system;
10. CPU/MPS decoded graphs are equivalent.

If any condition fails, the decision is `no_selection`, the canonical checkpoint is null, and the
complete comparison evidence remains available. A failed selection does not retroactively satisfy
missing architecture, run, ablation, calibration, or statistical work.

## Test integrity

- The champion selection hash is produced before final evaluation.
- Final evaluation may run once for that champion/protocol pair.
- A failed final gate is not followed by retuning or evaluating another candidate on test.
- test2 is reported separately and cannot select the champion.
- Failures, interrupted runs, zero-step runs, missing checkpoints, and incompatible components remain
  in the experiment index.

# Corpus and Experiment Contract

- Corpus loading is fail-closed by default and always returns validated receipt evidence internally.
- Official GUM partitions are assigned by document ID before candidates are flattened.
- Documents and source SHA-256 values are disjoint across train/dev/test/test2.
- Candidate existence is identical across partitions and inference for identical document/config
  inputs; gold labels only annotate candidates after generation.
- Training may sample hard negatives. Dev/test/test2 always retain the complete licensed candidate
  space.
- Training/tuning processes receive no test/test2 path or data handle.
- The repository scorer contract and reference runs precede finalist selection. A failed run produces
  a durable failure receipt but never blocks implementation of another required system.
- The champion manifest is derived only from train/dev evidence. Its hash authorizes one final test
  evaluation.
- Every successful run requires non-zero data, candidates, steps, checkpoint, predictions, and scorer
  output. Missing components are errors, not empty successes.
- No external publication, scorer, checkpoint, or reproduction artifact controls implementation
  permission.

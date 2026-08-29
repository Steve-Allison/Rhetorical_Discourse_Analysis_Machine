# Offline workbench

This is the single offline ownership surface for corpus preparation, training, evaluation, benchmarking, and local model promotion. It imports the installed `isanlp_rst` production package and production-owned contracts; production never imports this package.

## Subsystems

- `workbench/corpus/`: GUM and RST corpus reading, validation, and candidate sampling.
- `workbench/training/`: Training recipes for DMRST, UniRST, and eRST neural scorers.
- `workbench/evaluation/`: Parseval evaluation, treebank metrics, and confidence calibration.
- `workbench/research/`: Evidence-first architecture comparison trial harness and technology matrix.
- `workbench/promotion/`: Gated model packaging, manifest generation, and promotion receipts.
- `workbench/corpora/`: Local gold reference treebanks (GUM 12.1.0, RST-DT, DISRPT).
- `workbench/hashing.py`: High-throughput BLAKE3 and NIST SHA-256 hybrid cryptographic hashing engine.

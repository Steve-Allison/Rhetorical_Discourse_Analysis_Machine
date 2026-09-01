# CLI Contracts: ModernBERT Production Release

## 1. Training CLI Contract (`scripts/train_modernbert_treebank.py`)

### Synopsis

```bash
python scripts/train_modernbert_treebank.py [OPTIONS]
```

### Arguments & Flags

- `--corpus-dir PATH`: Directory containing GUM treebank (`workbench/corpora/gum-v12.1.0/`). Default: `workbench/corpora/gum-v12.1.0/`.
- `--epochs INT`: Number of full training epochs over the 211 training documents. Default: `3`.
- `--batch-size INT`: Document batch size. Default: `1`.
- `--grad-accum INT`: Gradient accumulation steps. Default: `16`.
- `--lr FLOAT`: Peak learning rate for AdamW optimizer. Default: `2e-5`.
- `--device {auto,mps,cuda,cpu}`: Hardware target. Default: `auto`.
- `--output-dir PATH`: Directory for best model checkpoint. Default: `models/modernbert_v1`.
- `--seed INT`: Master random seed. Default: `42`.

### Expected Output

- Generates `models/modernbert_v1/model.safetensors`, `training_receipt.json`.
- Appends run receipt to `workbench/experiments/central_ledger.jsonl`.
- Returns exit code `0` on success, non-zero on error.

---

## 2. Promotion CLI Contract (`workbench/promotion/modernbert.py`)

### Synopsis

```bash
python -m workbench.promotion.modernbert [OPTIONS]
```

### Arguments & Flags

- `--candidate-dir PATH`: Candidate model directory. Default: `models/modernbert_v1`.
- `--in-tree-store PATH`: In-tree release directory. Default: `models/model-releases`.
- `--user-cache-store PATH`: Local cache release directory. Default: `~/.cache/isanlp_rst/model-releases`.
- `--force`: Overwrite existing release if present.

### Expected Output

- Generates `release-manifest.json` with SHA-256 file hashes.
- Copies release package to dual stores.
- Validates manifest using `validate_model_release()`.
- Emits promoted `release_id` (e.g. `modernbert-v1-0d9aa6d57ace`).
- Returns exit code `0` on success.

---

## 3. Benchmark CLI Contract (`scripts/benchmark_modernbert.py`)

### Synopsis

```bash
python scripts/benchmark_modernbert.py [OPTIONS]
```

### Arguments & Flags

- `--release-id STR`: Promoted release ID to benchmark.
- `--model-store PATH`: Path to model release store. Default: `models/model-releases`.
- `--split {test,test2,all}`: Partition to evaluate. Default: `all`.
- `--device {auto,mps,cuda,cpu}`: Compute device. Default: `auto`.

### Expected Output

- Outputs micro-averaged Parseval scores (Span, Nuclearity, Relation, Full F1).
- Outputs per-relation breakdown table across 15 coarse relations.
- Appends benchmark results to `workbench/experiments/central_ledger.jsonl`.

---

## 4. Clean-Room Boundary Certification Contract (`tools/production_boundary/clean_install.py`)

### Synopsis

```bash
python tools/production_boundary/clean_install.py --wheel PATH --model-store PATH --release-id STR --full
```

### Invariants

- Must run in isolated `production` Pixi environment.
- Sets `ISANLP_RST_NETWORK_DISABLED=1`.
- Tests plain text, Docling AST (`*.docling.json`), DocLang XML (`*.dclg`), and Markdown.
- Emits JSON with `{"valid": true}` and returns exit code `0`.

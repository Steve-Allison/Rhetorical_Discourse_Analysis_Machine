# Quickstart: ModernBERT Pure Transformer Discourse Parser

**Purpose**: Runnable validation scenarios that verify the feature end-to-end from training through release promotion, independent benchmarking, and clean-room certification.

**Prerequisites**:

- Pixi environment initialized: `pixi run install`
- GUM 12.1.0 dataset present: `workbench/corpora/gum-v12.1.0/`

---

## Scenario 1: Model Training & Parseval Checkpointing

Train `PureTransformerParsingNet` on the authoritative 301-document GUM 12.1.0 dataset with gradient accumulation ($K=16$) and dynamic Parseval validation:

```bash
pixi run python scripts/train_modernbert_treebank.py \
    --epochs 3 \
    --device auto \
    --output-dir models/modernbert_v1
```

**Expected Outcome**:

- Training completes $\le 15$ minutes per epoch on Apple Silicon Metal (MPS).
- Evaluates Dev partition after each epoch, saving `models/modernbert_v1/model.safetensors` on new best Full F1.
- Final Dev Parseval scores satisfy: Span F1 $\ge 82.0\%$, Nuclearity F1 $\ge 68.0\%$, Relation F1 $\ge 55.0\%$, Full F1 $\ge 52.0\%$.
- Appends training receipt to `workbench/experiments/central_ledger.jsonl`.

---

## Scenario 2: Release Packaging & Dual-Store Promotion

Package candidate weights, configurations, and tokenizers into immutable release bundles with cryptographic SHA-256 digests:

```bash
pixi run python -m workbench.promotion.modernbert \
    --candidate-dir models/modernbert_v1
```

**Expected Outcome**:

- Creates `release-manifest.json` under contract `"isanlp_rst.parser/modernbert-v1"`.
- Mirrors package to `models/model-releases/<release_id>` and `~/.cache/isanlp_rst/model-releases/<release_id>`.
- Validates all file SHA-256 byte digests with zero errors.

---

## Scenario 3: Independent Held-Out Benchmarking

Evaluate the promoted model against held-out GUM in-domain test (32 docs) and out-of-domain GENTLE test2 (26 docs):

```bash
pixi run python scripts/benchmark_modernbert.py \
    --release-id <promoted_release_id>
```

**Expected Outcome**:

- Loads model via `Parser.from_model_release()`.
- Calculates micro-averaged Parseval metrics across Span, Nuclearity, Relation, and Full tree criteria.
- Emits per-relation precision, recall, and F1 across all 15 coarse relations.

---

## Scenario 4: Clean-Room Release Boundary Certification

Certify that `isanlp_rst 5.0.0` installs into an isolated clean-room environment and performs inference across all supported formats with external network access disabled:

```bash
pixi run -e production python tools/production_boundary/clean_install.py \
    --wheel dist/5.0.0/isanlp_rst-5.0.0-py3-none-any.whl \
    --root . \
    --model-store models/model-releases \
    --release-id <promoted_release_id> \
    --full
```

**Expected Outcome**:

- Verifies zero dev/offline dependencies in `production` environment.
- Tests raw text, Docling AST (`*.docling.json`), DocLang XML (`*.dclg`), and Markdown with `ISANLP_RST_NETWORK_DISABLED=1`.
- Emits JSON result with `"valid": true` and exit code `0`.

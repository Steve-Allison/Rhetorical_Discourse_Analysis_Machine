# Data Model & Schema Contracts: ModernBERT Production Release

## 1. Core Data Entities

### 1.1 Elementary Discourse Unit (EDU)

- **Fields**:
  - `edu_id`: `int` (0-indexed integer identifying the EDU within the document).
  - `start_char`: `int` (0-indexed start character offset in raw text).
  - `end_char`: `int` (0-indexed end character offset in raw text).
  - `text`: `str` (the substring content of the EDU).
  - `token_start`: `int` (start index in the subword token sequence).
  - `token_end`: `int` (end index in the subword token sequence).
- **Validation Rules**:
  - `start_char < end_char`
  - `0 <= token_start <= token_end < 8192`
  - Contiguous non-overlapping EDUs across the document.

### 1.2 Discourse Unit Tree Node (`DiscourseUnit`)

- **Fields**:
  - `id`: `int` (unique node identifier).
  - `left`: `DiscourseUnit | None` (left child node; `None` for leaf EDUs).
  - `right`: `DiscourseUnit | None` (right child node; `None` for leaf EDUs).
  - `relation`: `str` (coarse relation label for satellite nodes; `"root"` for root node).
  - `nuclearity`: `str` (`"nucleus"` or `"satellite"`).
  - `start`: `int` (inclusive start character offset of the span).
  - `end`: `int` (exclusive end character offset of the span).
  - `text`: `str` (span text content).
- **Validation Rules**:
  - Binary tree invariant: exactly two children (`left` and `right`) for branch nodes, 0 for leaf nodes.
  - Spans must satisfy `left.start == node.start` and `right.end == node.end`.
  - Nuclearity configuration must be one of `NS` (left nucleus, right satellite), `SN` (left satellite, right nucleus), or `NN` (multi-nuclear).

---

## 2. Taxonomy & Class Inventories

### 2.1 Coarse Relation Taxonomy (15 Classes)

| Index | Coarse Relation | Fine-Grained GUM Labels |
| :---: | :--- | :--- |
| 0 | `adversative` | `adversative-antithesis`, `adversative-concession`, `adversative-contrast` |
| 1 | `attribution` | `attribution-positive`, `attribution-negative` |
| 2 | `causal` | `causal-cause`, `causal-result` |
| 3 | `context` | `context-background`, `context-circumstance` |
| 4 | `contingency` | `contingency-condition` |
| 5 | `elaboration` | `elaboration-additional`, `elaboration-attribute`, `elaboration-part-whole` |
| 6 | `evaluation` | `evaluation-comment` |
| 7 | `explanation` | `explanation-evidence`, `explanation-justify`, `explanation-motivation` |
| 8 | `joint` | `joint-list`, `joint-other`, `joint-sequence`, `joint-disjunction` |
| 9 | `mode` | `mode-manner`, `mode-means` |
| 10 | `organization` | `organization-heading`, `organization-phatic`, `organization-preparation` |
| 11 | `purpose` | `purpose-goal`, `purpose-attribute` |
| 12 | `restatement` | `restatement-partial`, `restatement-repetition` |
| 13 | `same-unit` | `same-unit` |
| 14 | `topic` | `topic-question`, `topic-solutionhood` |

### 2.2 Nuclearity Classes (3 Classes)

| Index | Class | Structure | Description |
| :---: | :---: | :---: | :--- |
| 0 | `NS` | Nucleus-Satellite | Left child is Nucleus, Right child is Satellite |
| 1 | `SN` | Satellite-Nucleus | Left child is Satellite, Right child is Nucleus |
| 2 | `NN` | Multi-Nuclear | Both Left and Right children are Nuclei |

---

## 3. Supervised Target Tensors

For an $N$-EDU document:

- **`gold_splits`**: `torch.FloatTensor` of shape `(1, N, N)` where `gold_splits[0, i, j] = 1.0` if span $[i, j]$ is an active constituent in the gold tree, else `0.0`.
- **`gold_nucs`**: `torch.LongTensor` of shape `(1, N, N)` where `gold_nucs[0, i, j] \in {0, 1, 2}` if span $[i, j]$ is an internal constituent branch, else `-100`.
- **`gold_rels`**: `torch.LongTensor` of shape `(1, N, N)` where `gold_rels[0, i, j] \in {0..14}` if span $[i, j]$ is an internal constituent branch, else `-100`.

---

## 4. Release Manifest Schema (`release-manifest.json`)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "ModelReleaseManifest",
  "type": "object",
  "required": [
    "schema_version",
    "release_id",
    "model_task",
    "architecture",
    "runtime_contract",
    "compatibility_range",
    "source_model_identity",
    "source_revision",
    "licence",
    "use_restrictions",
    "created_at",
    "producer_version",
    "files"
  ],
  "properties": {
    "schema_version": { "type": "string", "const": "isanlp_rst_model_release/v1" },
    "release_id": { "type": "string", "pattern": "^modernbert-v1-[0-9a-f]{12}$" },
    "model_task": { "type": "string", "const": "rst_tree_parsing" },
    "architecture": { "type": "string", "const": "PureTransformerParsingNet" },
    "runtime_contract": { "type": "string", "const": "isanlp_rst.parser/modernbert-v1" },
    "compatibility_range": { "type": "string" },
    "source_model_identity": { "type": "string" },
    "source_revision": { "type": "string" },
    "licence": { "type": "string" },
    "use_restrictions": { "type": "array", "items": { "type": "string" } },
    "created_at": { "type": "string", "format": "date-time" },
    "producer_version": { "type": "string" },
    "files": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["path", "role", "size_bytes", "sha256"],
        "properties": {
          "path": { "type": "string" },
          "role": { "type": "string", "enum": ["encoder_config", "parser_state", "relation_inventory", "tokenizer", "model_card"] },
          "size_bytes": { "type": "integer", "minimum": 1 },
          "sha256": { "type": "string", "pattern": "^[0-9a-f]{64}$" }
        }
      }
    }
  }
}
```

---

## 5. Scientific Ledger Record (`central_ledger.jsonl`)

Each line in `workbench/experiments/central_ledger.jsonl` is a JSON record with:

- `timestamp`: ISO-8601 UTC string.
- `run_id`: Unique identifier for the training/benchmark session.
- `git_commit`: 40-character hexadecimal Git commit hash.
- `pixi_lock_hash`: SHA-256 hash of `pixi.lock`.
- `device`: String identifier (`"mps"`, `"cuda:0"`, `"cpu"`).
- `pytorch_version`: String (`"2.13.0"`).
- `hyperparameters`: Dictionary of learning rate, batch size, gradient accumulation steps, epochs, weights.
- `metrics`: Dictionary of Dev/Test micro-averaged Parseval scores (Span, Nuclearity, Relation, Full F1) and per-relation breakdown.

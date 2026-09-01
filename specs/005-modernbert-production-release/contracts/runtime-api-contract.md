# Runtime API Contracts: ModernBERT Production Release

## 1. High-Level Model Loader (`isanlp_rst.parser.Parser`)

### Factory Method: `from_model_release`

```python
@classmethod
def from_model_release(
    cls,
    release_id: str,
    *,
    model_store: str | Path | None = None,
    device: str | torch.device | None = None,
) -> Parser: ...
```

- **Parameters**:
  - `release_id`: Explicit release identifier (e.g. `"modernbert-v1-0d9aa6d57ace"`).
  - `model_store`: Optional explicit filesystem directory. If `None`, searches standard stores (`models/model-releases/` then `~/.cache/isanlp_rst/model-releases/`).
  - `device`: Optional device specification. If `None`, autodispatches to `mps` on Apple Silicon, `cuda` if available, or `cpu`.
- **Preconditions**:
  - Valid `release-manifest.json` exists in the resolved release directory.
  - SHA-256 byte digests for all files match `release-manifest.json`.
- **Postconditions**:
  - Returns initialized `Parser` wrapping `PredictorModernBERT`.
  - Zero network calls made when files exist in `model_store`.

---

## 2. Low-Level Predictor (`isanlp_rst.transformer_parser.predictor.PredictorModernBERT`)

### Method: `__call__`

```python
def __call__(
    self,
    text: str | None = None,
    edus: list[tuple[int, int]] | None = None,
    tokens: list[str] | None = None,
    docling_doc: Any | None = None,
    doclang_doc: Any | None = None,
) -> DiscourseUnit: ...
```

- **Inputs**: Raw string, pre-segmented character spans, or structured document ASTs.
- **Output**: Root `DiscourseUnit` with complete binary tree hierarchy and character span alignments.
- **Performance**: Predicts full document binary tree in $< 100\text{ ms}$ on Apple Silicon MPS.

# IsaNLP RST Parser

![Python](https://img.shields.io/badge/python-3.14%2B-blue) ![License](https://img.shields.io/badge/license-MIT_(code)_/_CC_BY--NC_4.0_(weights)-orange) ![Apple Silicon](https://img.shields.io/badge/Apple_Silicon-MPS-blueviolet)

End-to-end Rhetorical Structure Theory (RST) parser. Predicts discourse trees from raw text or pre-segmented EDUs across 11 languages via the `unirst` multilingual model, plus three monolingual / bilingual models (`rstdt`, `gumrrg`, `rstreebank`). Pixi-managed, MPS-aware, with real tests and CI.

## Table of contents

- [Performance](#performance)
- [Installation & quick start](#installation--quick-start)
- [Production package and offline workbench](#production-package-and-offline-workbench)
- [Visualising the RST tree](#visualising-the-rst-tree)
- [Advanced usage](#advanced-usage)
- [Extended RST (eRST) graph decoding](#extended-rst-erst-graph-decoding)
- [Hierarchical long document parsing](#hierarchical-long-document-parsing)
- [Production source ingest](#production-source-ingest)
- [Quality diagnostics](#quality-diagnostics)
- [Evaluation & metrics](#evaluation--metrics)
- [Project status & licence](#project-status--licence)
- [Citation](#citation)

## Performance

The parser achieves strong end-to-end performance across standard RST corpora.

**Supported languages (`unirst`):** English (eng), Czech (ces), German (deu), Basque (eus), Persian (fas), French (fra), Dutch (nld), Brazilian Portuguese (por), Russian (rus), Spanish (spa), Chinese (zho).

<details>
<summary><b>Click to view detailed end-to-end performance metrics</b></summary>

| Tag / Version | Languages | Train Data | Test Data | Seg | S | N | R | Full |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `rstdt` | eng | eng.rst.rstdt | eng.rst.rstdt | 97.8 | 75.6 | 65.0 | 55.6 | 53.9 |
| `gumrrg` | eng, rus | eng.erst.gum, rus.rst.rrg | eng.erst.gum | 95.5 | 67.4 | 56.2 | 49.6 | 48.7 |
| | | | rus.rst.rrg | 97.0 | 67.1 | 54.6 | 46.5 | 45.4 |
| `rstreebank` | rus | rus.rrt | rus.rst.rrt | 92.1 | 66.2 | 53.1 | 46.1 | 46.2 |
| `unirst` | all | all | ces.rst.crdt | 94.5 | 59.1 | 41.2 | 28.6 | 28.0 |
| | | | deu.rst.pcc | 96.5 | 67.3 | 47.4 | 34.1 | 32.1 |
| | | | eng.erst.gum | 95.3 | 67.3 | 55.6 | 48.5 | 47.4 |
| | | | eng.rst.oll | 92.5 | 55.7 | 39.0 | 27.5 | 26.3 |
| | | | eng.rst.rstdt | 98.1 | 76.7 | 65.5 | 55.2 | 53.6 |
| | | | eng.rst.sts | 91.2 | 43.3 | 31.3 | 19.4 | 18.7 |
| | | | eng.rst.umuc | 88.8 | 52.6 | 40.6 | 26.2 | 25.8 |
| | | | eus.rst.ert | 92.5 | 66.0 | 50.3 | 34.9 | 34.7 |
| | | | fas.rst.prstc | 94.7 | 63.0 | 50.2 | 40.8 | 40.7 |
| | | | fra.sdrt.annodis | 91.3 | 58.6 | 48.9 | 30.6 | 30.3 |
| | | | nld.rst.nldt | 98.0 | 61.8 | 49.8 | 36.8 | 35.8 |
| | | | por.rst.cstn | 93.9 | 68.4 | 52.8 | 44.9 | 44.5 |
| | | | rus.rst.rrg | 96.4 | 67.4 | 54.0 | 46.3 | 45.1 |
| | | | rus.rst.rrt | 90.7 | 63.0 | 49.0 | 42.3 | 42.2 |
| | | | spa.rst.rststb | 93.4 | 63.5 | 50.3 | 36.0 | 36.0 |
| | | | spa.rst.sctb | 85.5 | 55.1 | 46.8 | 39.1 | 39.1 |
| | | | zho.rst.gcdt | 93.0 | 64.5 | 50.7 | 45.9 | 44.6 |
| | | | zho.rst.sctb | 95.4 | 67.5 | 51.5 | 39.9 | 39.9 |

Full per-corpus UniRST metrics: [`docs/metrics/UniRST_Metrics.md`](docs/metrics/UniRST_Metrics.md).

</details>

## Installation & quick start

### 1. Install

For production analysis in this checkout, use the independently solved production environment:

```bash
git clone https://github.com/Steve-Allison/isanlp_rst.git
cd isanlp_rst
pixi install -e production
pixi run -e production production-smoke
```

Alternative (raw venv / pip):

```bash
pip install git+https://github.com/Steve-Allison/isanlp_rst.git

# DocLang, Docling, and Markdown source adapters are production capabilities
# supplied by the optional `formats` extra:
pip install "isanlp_rst[formats] @ git+https://github.com/Steve-Allison/isanlp_rst.git"
```

Corpus preparation, training, evaluation, benchmarking, and research are intentionally absent from both production installs. Repository development uses the separate offline environment:

```bash
pixi install -e offline
pixi run -e offline offline-smoke
pixi run -e offline test
```

See [Production package and offline workbench](#production-package-and-offline-workbench) for the ownership contract.

#### 2. Command-line interface (`isanlp-rst`)

The package provides a fast, unified CLI for parsing, visualization, and serving:

```bash
# Parse text and display a terminal ASCII discourse tree
isanlp-rst parse --text "ModernBERT provides fast attention. This enables rich discourse parsing." -f tree

# Parse files (Markdown, Docling JSON, DocLang XML, plain text) to structured JSON DAG
isanlp-rst parse report.md -f json -o analysis.json

# Extract Mann & Thompson structural diagnostics
isanlp-rst parse report.txt -f stats

# Render an RS3 XML file as an interactive HTML visualisation
isanlp-rst view document.rs3 --open

# Launch high-throughput local HTTP REST parsing daemon
isanlp-rst serve --host 127.0.0.1 --port 8080

# Inspect environment and hardware backend capabilities
isanlp-rst version
```

### 3. Python API usage

```python
from isanlp_rst import Parser, RstDocument
from isanlp_rst.utils.analysis import tree_stats

# Initialise SOTA ModernBERT parser (downloads weights on first call, autodispatches to MPS/CUDA)
parser = Parser(family="modernbert", device="auto")

text = """
On Saturday, in the ninth edition of the T20 Men's Cricket World Cup, Team India won against South Africa by seven runs.
The final match was played at the Kensington Oval Stadium in Barbados. This marks India's second win in the T20 World Cup.
Virat Kohli top-scored with 76 runs, followed by Axar Patel with 47 runs.
"""

# 1. Direct RST tree parsing
tree = parser.parse_tree(text)
print(tree)
stats = tree_stats(tree)
print(f"Tree Depth: {stats['depth']}, Leaves: {stats['n_leaves']}")

# 2. Canonical structured document analysis (RstAnalysis DAG)
doc = RstDocument.from_text(text, document_id="cricket_match_001")
analysis = parser.parse_document(doc)
print(f"Discourse Nodes: {len(analysis.nodes)}")
print(f"Primary Edges:   {len(analysis.primary_edges)}")
```

#### Device selection (`device=`)

`device=` chooses the compute backend (default `"auto"`):

- `"auto"` (default) → CUDA if present, else MPS on Apple Silicon, else CPU
- `"cpu"` → CPU
- `"mps"` → Apple Silicon Metal backend (accelerated FP32/BF16)
- `"cuda"` / `"cuda:N"` → specific NVIDIA GPU (raises if CUDA is unavailable)

PyTorch has no MPS kernel for `torch.linalg.qr` (used by `torch.nn.init.orthogonal_` during weight init). The parser routes this via CPU automatically — no env-var hacks required.

#### Mixed precision (`dtype=`)

Forward passes go through `torch.autocast`, so the model runs in `float32`, `float16`, or `bfloat16` without changing the trained weights:

```python
import torch

parser = Parser(hf_model_version="gumrrg", device="auto", dtype=torch.bfloat16)  # also accepts 'bf16', 'fp16', 'fp32'
```

Default is `float32` on every device. On Apple Silicon (M-series, PyTorch 2.11) at ~1k-char inputs, `float32` beats `bfloat16` / `float16` for every published model — per-op autocast dispatch overhead dominates the matmul speedup at this scale. On large-batch CUDA workloads with native bf16 (Hopper / Ada Tensor Cores), `bfloat16` is likely faster — measure with `pixi run -e offline bench` before pinning a choice.

Tree topology and EDU segmentation are bit-equivalent across all three dtypes for every published model; relation labels are not — on a near-tied node, reduced precision (bf16/fp16) can flip the argmax without any structural change. See [`tests/test_integration.py`](tests/test_integration.py) for the equivalence suite.

##### Apple Silicon perf (M-series, PyTorch 2.11, ~1k char input)

| Model | CPU fp32 | MPS fp32 | MPS bf16 | MPS fp16 |
|---|---|---|---|---|
| `gumrrg` | 143 ms | **120 ms** | 156 ms | 157 ms |
| `rstdt` | 168 ms | **123 ms** | 161 ms | 165 ms |
| `rstreebank` | 113 ms | **59 ms** | 94 ms | 94 ms |
| `rrtrrg` | 118 ms | **61 ms** | 104 ms | 95 ms |
| `unirst` | **127 ms** | 153 ms | 218 ms | 221 ms |

The 18-corpus `unirst` model is faster on CPU than on MPS — multi-corpus classifier dispatch costs more than MPS's matmul speedup recovers. Run `pixi run -e offline bench --version unirst` on your hardware to verify before pinning a device choice for that model.

#### Verifying on NVIDIA CUDA hardware

CI runs on macOS Apple Silicon with **Python 3.14** (pixi lock). Package metadata declares `requires-python >= 3.14`. The CUDA dispatch path isn't exercised in CI. To verify on an NVIDIA host:

```bash
pixi run -e offline cuda-smoke
```

The script confirms `torch.cuda.is_available()`, loads DMRST and UniRST on `cuda:0`, parses a sample text, and round-trips a `parse_from_edus` call. Exits non-zero on any failure.

### 3. Understanding the output

The parser returns an RST tree with a recursive `DiscourseUnit` structure. Each node carries:

```python
{
 'id': 21,
 'left':  (id=14, start=1,   end=323),  # child node refs
 'right': (id=20, start=324, end=570),
 'relation':    'elaboration',           # rhetorical relation
 'nuclearity':  'NS',                    # NS / NN / ""
 'entropy':     0.92,                    # split entropy
 'start':       1,                       # original-text character offset
 'end':         570,
 'text':        "On Saturday, ... took two wickets."
}
```

Leaves are EDUs; internal nodes are relations. Every node has `start` / `end` in **original-text character coordinates**.

---

## Visualising the RST tree

### 1. Save to RS3

```python
res["rst"][0].to_rs3("filename.rs3")
```

Open `filename.rs3` in external tools like **RSTTool** or **rstWeb** for editing.

### 2. Inline render (Jupyter / Colab)

```python
import io, contextlib
import isanlp_rst

buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    isanlp_rst.render("filename.rs3")

# For Google Colab, sync the cell height:
# isanlp_rst.render("filename.rs3", colab=True)
```

<img src="examples/example-inline.png" alt="Illustration of the parsing visualisation" width="600">

### 3. Export to PNG or PDF

Requires Playwright:

```bash
pip install playwright
playwright install chromium
```

```python
import isanlp_rst

isanlp_rst.to_png("filename.rs3", "filename.png")
isanlp_rst.to_pdf("filename.rs3", "filename.pdf")
```

<img src="examples/example-image.png" alt="Illustration of English parsing" width="600">

---

## Advanced usage

### Parsing pre-segmented EDUs

```python
my_edus = ["On Saturday, Team India won against South Africa.", "The final match was played in Barbados."]

res = parser.from_edus(my_edus)
```

### Memory management for large datasets

When parsing many documents, the resulting `DiscourseUnit` trees can consume significant memory — each node stores its corresponding text span.

```python
res["rst"][0].clear_textfields()  # drop .text on every node, keep structure
# ... pickle / store ...
res["rst"][0].fill_textfields(full_text)  # repopulate later
```

**Note:** `.to_rs3()` on a tree with cleared text fields will fail.

---

## Extended RST (eRST) graph decoding

Beyond standard hierarchical trees, `isanlp_rst` supports **Extended RST (eRST)** graph structures with non-projective secondary discourse relations and discourse signals (as in GUM eRST / RS4 XML):

- **Faithful RS4 XML Reader & Writer** (`isanlp_rst.erst.rs4`): Native serialization for segments, multinuclear groups, secondary edges (`<secedge>`), and signaling tokens (`<signal>`).
- **Neural Secondary Edge Scorer** (`isanlp_rst.erst.neural_scorer.NeuralSecondaryEdgeScorer`): Learned bilinear / MLP scorer for candidate secondary discourse relations.
- **Formally constrained secondary-edge decoder**
  (`isanlp_rst.erst.decoder.ErstSecondaryEdgeDecoder`): applies sufficient-signal, no-self-loop,
  no-invented-node, and no-duplicate-directed-pair constraints. Cycles, crossing edges, reverse
  directions, unrestricted degree, and overlap with primary edges remain valid eRST structures.

```python
from isanlp_rst.erst import RS4Reader, rs4_to_document_and_analysis

rs4 = RS4Reader.read_file("document.rs4")
doc, analysis = rs4_to_document_and_analysis(rs4, document_id="document")
# analysis.formalism: OutputFormalismEnum.ERST_GRAPH
# analysis.secondary_edges: tuple of SecondaryRelationEdge
# analysis.signals: tuple of DiscourseSignal
```

---

## Hierarchical long document parsing

For long documents exceeding single-window transformer limits, `isanlp_rst.hierarchical.stitcher.MacroMicroStitcher` provides two-stage macro/micro document stitching:

1. **Micro-Stage**: Parses individual sections / paragraphs into coherent local RST subtrees.
2. **Macro-Stage**: Predicts high-level discourse relations across section roots.
3. **Stitching**: Glues local trees into a globally consistent, root-to-leaf discourse tree without recursion limits or offset drifts.

---

## Production source ingest

`isanlp_rst.ingest` is the single production boundary for analysing real-world
source material. It accepts plain text, exact pre-segmented EDUs, Markdown,
DoclingDocument JSON, and DocLang XML or `.dclx` archives. There are no separate
format parse functions, result envelopes, policies, or caches.

```python
from pathlib import Path

from isanlp_rst import Parser
from isanlp_rst.ingest import AUTHORED_PROSE_V1, ProductionIngestor, SourceArtifact

parser = Parser.from_model_release(
    Path("/absolute/path/to/model-releases"),
    "gumrrg-eb1d5745f3a1",
    family="dmrst",
    device="auto",
)
ingestor = ProductionIngestor(parser=parser)

artifact = SourceArtifact.from_path(Path("report.md"))
result = ingestor.analyse(
    artifact,
    policy=AUTHORED_PROSE_V1,
    cache_dir=Path("/absolute/path/to/cache"),
)
```

The default policy inventories the complete valid source first, then admits
authored headings, prose, meaningful list items, and authored turns to primary
RST analysis. Tables, code, formulas, raw markup, pictures, metadata, fields,
and assets remain retained side channels. Machine-generated picture
descriptions, notes, navigation, furniture, backgrounds, and invisible content
are excluded from primary RST but remain receipted. No caller-supplied format
switch can silently widen that policy.

`result` is a strict `ProductionAnalysisResult` containing the prepared
document, complete dispositions and receipts, the coherent `RstAnalysis`, and
native source anchors. Before consuming the tree, require all four coverage
measures to be complete:

```python
assert result.preparation_receipt.inventory_coverage == 1.0
assert result.preparation_receipt.primary_source_coverage == 1.0
assert result.preparation_receipt.prepared_text_coverage == 1.0
assert result.preparation_receipt.analysis_anchor_coverage == 1.0
```

An input with no eligible authored discourse returns
`analysis_status == "empty_primary_discourse"`, a complete inventory and
disposition receipt, and no fabricated RST tree. Long sources are partitioned
at document structure and parser-capacity boundaries, analysed recursively, and
stitched into one anchored result; they are not truncated or rejected by a
format-specific character ceiling.

Ambiguous JSON, XML, text, extensionless, or byte inputs require an explicit
`SourceForm`. DocLang always runs current XSD and Schematron validation;
Docling JSON always runs current `docling-core` model validation. Cache identity
includes the raw source contract, preparation policy and implementation,
released model bytes, and result schema. Corrupt or contradictory cache entries
fail closed.

The full contract and examples are in
[`docs/production-source-ingest.md`](docs/production-source-ingest.md).

---

## Quality diagnostics

`pixi run -e offline rst-diag <paths>` analyses any mix of `.md`,
`*.docling.json`, `*.dclg`, `*.dclg.xml`, and `*.dclx` sources through one
canonical ingestor and one shared model load. It emits:

- **joint ratio** — share of relations labelled joint / same-unit / organization (high = rhetorically thin chaining)
- **tree skew** — max depth ÷ log₂(EDUs) (≫ 1 = degenerate chain)
- **prepared characters and segments** — the exact primary RST material
- **all four coverage ratios** — inventory, primary source, prepared text, and analysis anchors

Use it to inspect result quality and source-accounting integrity. `--json` gives
machine-readable output; `--model-version`, `--device`, and `--dtype` select the
shared parser.

---

## Production package and offline workbench

`isanlp_rst` is the importable production product. It contains raw/pre-segmented RST inference, typed contracts, model validation/loading, eRST runtime completion, canonical source ingest, and rendering. Its wheel and source distribution exclude corpus builders, trainers, evaluators, research harnesses, tests, scripts, experiment data, Gold Set content, and model candidates.

`workbench` is the repository-only surface for corpus preparation, training, evaluation, and local model promotion. `workbench.research` remains a repository-only research implementation but runs in the same root `offline` Pixi environment. Production never imports either namespace.

The causal checks are:

```bash
pixi run -e production production-smoke
pixi run -e offline production-boundary
pixi run -e offline offline-smoke
```

The full ownership and migration map is in [`docs/production-offline-boundary.md`](docs/production-offline-boundary.md). Production source ingest remains production functionality because it prepares real source material for analysis; training-corpus preparation, evaluation, and Gold Set assessment remain offline.

---

## Evaluation & metrics

Evaluation is offline-only. Standard/soft Parseval and the eRST scorer live under `workbench.evaluation.rst`; they are available in `pixi run -e offline ...` workflows and are not installed into consumer projects.

---

## Project status & licence

This repository is Steve Allison's evolution of the IsaNLP RST Parser. The original RST research code and the trained model weights are by Elena Chistova; the MIT-licensed source code carries her copyright. This repository adds pixi-managed builds, a pytest test suite, GitHub Actions CI, MPS / Apple-Silicon support, mixed-precision dispatch, and ongoing roadmap work (see `docs/plans/`).

- **Source code:** MIT — see [`LICENSE`](LICENSE). Copyright Elena Chistova 2020; Steve Allison contributions also under MIT.
- **Model weights** (downloaded from `tchewik/isanlp_rst_v3` on HuggingFace): **CC BY-NC 4.0 — research and non-commercial use only.** See [`LICENSE_MODELS`](LICENSE_MODELS). Commercial use requires either retraining weights under a permissive licence or replacing the models entirely.

Issues and pull requests: please open them on `Steve-Allison/isanlp_rst`. For questions about the underlying RST research, see Elena Chistova's papers cited below.

---

## Citation

The published model weights are by Elena Chistova. If you use them in research, please cite:

For `rstdt`, `gumrrg`, and `rstreebank`:

```bibtex
@inproceedings{chistova-2024-bilingual,
 title = "Bilingual Rhetorical Structure Parsing with Large Parallel Annotations",
 author = "Chistova, Elena",
 booktitle = "Findings of the Association for Computational Linguistics ACL 2024",
 month = aug,
 year = "2024",
 address = "Bangkok, Thailand and virtual meeting",
 publisher = "Association for Computational Linguistics",
 url = "https://aclanthology.org/2024.findings-acl.577",
 pages = "9689--9706"
}
```

For `unirst`:

```bibtex
@inproceedings{chistova-2025-bridging,
  title = "Bridging Discourse Treebanks with a Unified Rhetorical Structure Parser",
  author = "Chistova, Elena",
  booktitle = "Proceedings of the 6th Workshop on Computational Approaches to Discourse, Context and Document-Level Inferences (CODI 2025)",
  month = nov,
  year = "2025",
  address = "Suzhou, China",
  publisher = "Association for Computational Linguistics",
  url = "https://aclanthology.org/2025.codi-1.17/",
  pages = "197--208"
}
```

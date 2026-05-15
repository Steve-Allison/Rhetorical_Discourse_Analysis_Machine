![Python](https://img.shields.io/badge/python-3.10%2B-blue) ![License](https://img.shields.io/badge/license-MIT_(code)_/_CC_BY--NC_4.0_(weights)-orange) ![Apple Silicon](https://img.shields.io/badge/Apple_Silicon-MPS-blueviolet)

# IsaNLP RST Parser

End-to-end Rhetorical Structure Theory (RST) parser. Predicts discourse trees from raw text or pre-segmented EDUs across 11 languages via the `unirst` multilingual model, plus three monolingual / bilingual models (`rstdt`, `gumrrg`, `rstreebank`). Pixi-managed, MPS-aware, with real tests and CI.

### Table of contents

- [Performance](#performance)
- [Installation & quick start](#installation--quick-start)
- [Visualising the RST tree](#visualising-the-rst-tree)
- [Advanced usage](#advanced-usage)
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

Full per-corpus UniRST metrics: [`UniRST_Metrics.md`](UniRST_Metrics.md).

</details>

## Installation & quick start

### 1. Install

The recommended path is pixi (provisions Python + all dependencies + the `iinemo/isanlp` runtime into a locked env):

```bash
git clone https://github.com/Steve-Allison/isanlp_rst.git
cd isanlp_rst
pixi install
```

Alternative (raw venv / pip):

```bash
pip install git+https://github.com/iinemo/isanlp.git    # required runtime dep
pip install git+https://github.com/Steve-Allison/isanlp_rst.git
```

### 2. Basic usage

```python
from isanlp_rst.parser import Parser

# Choose a model version
version = 'gumrrg'  # one of: 'gumrrg', 'rstdt', 'rstreebank', 'rrtrrg', 'unirst'

# Initialise the parser (downloads weights from HF on first call)
parser = Parser(hf_model_name='tchewik/isanlp_rst_v3',
                hf_model_version=version,
                cuda_device=0)  # -1 = CPU

text = """
On Saturday, in the ninth edition of the T20 Men's Cricket World Cup, Team India won against South Africa by seven runs.
The final match was played at the Kensington Oval Stadium in Barbados. This marks India's second win in the T20 World Cup,
which was co-hosted by the West Indies and the USA between June 2 and June 29.

After winning the toss, India decided to bat first and scored 176 runs for the loss of seven wickets.
Virat Kohli top-scored with 76 runs, followed by Axar Patel with 47 runs. Hardik Pandya took three wickets,
and Jasprit Bumrah took two wickets.
"""

res = parser(text)  # res['rst'] contains the binary discourse tree
print(vars(res['rst'][0]))
```

For the multilingual `unirst` model, specify the relation inventory:

```python
parser = Parser(hf_model_name='tchewik/isanlp_rst_v3',
                hf_model_version='unirst',
                cuda_device=0,
                relinventory='eng.erst.gum')  # see UniRST_Metrics.md for options
```

#### Loading from a local checkpoint

For offline / air-gapped use, point `Parser` at a directory containing the checkpoint:

```python
# Family auto-detected:
#   data_manager_*.pickle or config.json with `data.corpora`  -> UniRST
#   relation_table.txt                                        -> DMRST
parser = Parser(model_dir='/path/to/checkpoint', cuda_device=0)

# Override auto-detection:
parser = Parser(model_dir='/path/to/checkpoint', family='dmrst', cuda_device=0)
```

#### Apple Silicon (MPS)

`cuda_device=N` auto-selects the best available GPU backend:

- NVIDIA CUDA host → `cuda:N`
- Apple Silicon (no CUDA) → `mps` (integer ignored; MPS exposes a single device)
- No GPU available → `RuntimeError` (use `cuda_device=-1` for CPU)

PyTorch has no MPS kernel for `torch.linalg.qr` (used by `torch.nn.init.orthogonal_` during weight init). The parser routes this via CPU automatically — no env-var hacks required.

#### Mixed precision (`dtype=`)

Forward passes go through `torch.autocast`, so the model runs in `float32`, `float16`, or `bfloat16` without changing the trained weights:

```python
import torch
parser = Parser(hf_model_version='gumrrg', cuda_device=0,
                dtype=torch.bfloat16)   # also accepts 'bf16', 'fp16', 'fp32'
```

Default is `float32` on every device. On Apple Silicon (M-series, PyTorch 2.11) at ~1k-char inputs, `float32` beats `bfloat16` / `float16` for every published model — per-op autocast dispatch overhead dominates the matmul speedup at this scale. On large-batch CUDA workloads with native bf16 (Hopper / Ada Tensor Cores), `bfloat16` is likely faster — measure with `pixi run bench` before pinning a choice.

Tree structure is bit-equivalent across all three dtypes for every published model — see [`tests/test_integration.py`](tests/test_integration.py) for the equivalence suite.

##### Apple Silicon perf (M-series, PyTorch 2.11, ~1k char input)

| Model | CPU fp32 | MPS fp32 | MPS bf16 | MPS fp16 |
|---|---|---|---|---|
| `gumrrg` | 143 ms | **120 ms** | 156 ms | 157 ms |
| `rstdt` | 168 ms | **123 ms** | 161 ms | 165 ms |
| `rstreebank` | 113 ms | **59 ms** | 94 ms | 94 ms |
| `rrtrrg` | 118 ms | **61 ms** | 104 ms | 95 ms |
| `unirst` | **127 ms** | 153 ms | 218 ms | 221 ms |

The 18-corpus `unirst` model is faster on CPU than on MPS — multi-corpus classifier dispatch costs more than MPS's matmul speedup recovers. Run `pixi run bench --version unirst` on your hardware to verify before pinning a device choice for that model.

#### Verifying on NVIDIA CUDA hardware

CI runs on macOS Apple Silicon, so the CUDA dispatch path isn't exercised in CI. To verify on an NVIDIA host:

```bash
pixi run cuda-smoke
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
res['rst'][0].to_rs3('filename.rs3')
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
my_edus = [
    "On Saturday, Team India won against South Africa.",
    "The final match was played in Barbados."
]

res = parser.from_edus(my_edus)
```

### Memory management for large datasets

When parsing many documents, the resulting `DiscourseUnit` trees can consume significant memory — each node stores its corresponding text span.

```python
res['rst'][0].clear_textfields()   # drop .text on every node, keep structure
# ... pickle / store ...
res['rst'][0].fill_textfields(full_text)   # repopulate later
```

**Note:** `.to_rs3()` on a tree with cleared text fields will fail.

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

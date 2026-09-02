# Rhetorical Discourse Analysis Machine (`rdam`)

![Python](https://img.shields.io/badge/python-3.14%2B-blue) ![License](https://img.shields.io/badge/license-MIT_(code)_/_CC_BY--NC_4.0_(archived_weights)-orange) ![Apple Silicon](https://img.shields.io/badge/Apple_Silicon-MPS-blueviolet)

A permanently analysis-only machine that runs several discourse and argumentation
techniques natively, side by side, without collapsing them into a common formalism. One
distribution, one package, every technique a sub-package:

| Sub-package | Technique | What it does |
|---|---|---|
| `rdam` | the machine | provider and formalism declarations, explicit capability states, one outcome per requested technique, and the evidence-gated `PromotionDecision` every provider is bound by |
| `rdam.rst` | RST / eRST | the ModernBERT discourse parser (Steve Allison's evolution of Elena Chistova's IsaNLP RST Parser), canonical source ingest for text, EDUs, Markdown, Docling JSON, and DocLang, eRST completion, the RS3 viewer, and the `rdam-rst` command |
| `rdam.dung` | Dung abstract argumentation | grounded, complete, preferred, and stable extensions of a supplied argument–attack framework, exact by construction |
| `rdam.ibis` | IBIS | issue–position–argument structures validated under the gIBIS link grammar and organised into a deliberation map |

Techniques without a promoted provider (SDRT, Toulmin, Walton, PDTB) are reported by the
machine as `unavailable(no_promoted_implementation)`; there are no stubs. The machine
serves one person on one local machine. Pixi-managed, MPS-aware, Apple-Silicon-first,
real test suite, real CI.

## Table of contents

- [Installation](#installation)
- [The machine](#the-machine)
- [Capability comes from evidence](#capability-comes-from-evidence)
- [RST: command line](#rst-command-line)
- [RST: Python API](#rst-python-api)
- [RST: production source ingest](#rst-production-source-ingest)
- [RST: visualising a tree](#rst-visualising-a-tree)
- [RST: extended RST, long documents, diagnostics](#rst-extended-rst-long-documents-diagnostics)
- [Production package and offline workbench](#production-package-and-offline-workbench)
- [Archived research parser families](#archived-research-parser-families)
- [Project status & licence](#project-status--licence)
- [Citation](#citation)

## Installation

In this checkout, use the independently solved production environment:

```bash
git clone https://github.com/Steve-Allison/isanlp_rst.git
cd isanlp_rst
pixi install -e production
pixi run -e production production-import-check
```

Or install the distribution into any Python 3.14 environment:

```bash
pip install "rdam @ git+https://github.com/Steve-Allison/isanlp_rst.git"

# Markdown, Docling JSON, and DocLang source adapters are production capabilities
# supplied by the optional `formats` extra:
pip install "rdam[formats] @ git+https://github.com/Steve-Allison/isanlp_rst.git"
```

No model weight ships in the wheel. RST inference needs an immutable local model release
(`models/model-releases/<release_id>/` with its manifest); this repository's store holds
`modernbert-v1-a52b70fbc1a3` and `modernbert-v1-462d68b82eae`.

Corpus preparation, training, evaluation, benchmarking, and research are intentionally
absent from both production installs. Repository development uses the `default`
environment:

```bash
pixi install
pixi run test
```

## The machine

```python
from pathlib import Path

from rdam import AggregateRequest, Machine, ResultOutcome, SourceIdentity, StructuredInput, Technique
from rdam.dung import DungProvider
from rdam.ibis import IbisProvider
from rdam.rst.provider import RstProvider

machine = Machine(
    [
        RstProvider(store=Path("models/model-releases"), release_id="modernbert-v1-a52b70fbc1a3"),
        DungProvider(),
        IbisProvider(),
    ]
)

# One explicit capability state per technique; reporting capability loads nothing.
for capability in machine.capabilities().techniques:
    print(capability.technique.value, capability.capability)

# One explicit outcome per requested technique: ResultOutcome, UnavailableOutcome, or FailedOutcome.
aggregate = machine.analyse(AggregateRequest.for_text("Because it rained, the match stopped.", (Technique.RST,)))
outcome = aggregate.outcome_for(Technique.RST)
if isinstance(outcome, ResultOutcome):
    print(outcome.result.payload["kind"])  # the provider's own outcome envelope, verbatim

# Formal techniques take a supplied structure, never text.
framework = {"arguments": ["a", "b", "c"], "attacks": [["a", "b"], ["b", "c"]]}
request = AggregateRequest(
    source=SourceIdentity.from_bytes(b"framework", media_type="application/json"),
    text=None,
    techniques=(Technique.DUNG,),
    structured_inputs=(StructuredInput(technique=Technique.DUNG, payload=framework),),
)
dung = machine.analyse(request).outcome_for(Technique.DUNG)
if isinstance(dung, ResultOutcome):
    print(dung.result.payload["extensions"]["grounded"])  # ['a', 'c']
```

The machine never retries, never suppresses one technique's failure behind another's
success, and never derives a Dung framework or an IBIS structure from text: a text-only
request for those techniques is `unavailable(missing_structured_input)`, not a failure.

## Capability comes from evidence

A provider is `available` only under a `PromotionDecision` whose outcome is `promote` or
`replace`, and such a decision cannot be constructed unless every evidence class —
output quality (empirical or formal), calibration, latency, compatibility, provenance,
licensing — is admissible. Decisions are recorded in `workbench/promotions/<technique>/`
and bound to the exact artifact they evaluated:

- `rdam.dung` and `rdam.ibis` package their decision beside their code, bound to the
  digest of their own source files. Both are `available` today.
- `rdam.rst` reads the decision published beside the configured model release
  (`<store>/<release_id>.promotion.json`) and checks its artifact digest against the
  release manifest before any inference. Every stored ModernBERT release currently
  fails the gate (for `modernbert-v1-a52b70fbc1a3`: test full F1 0.198 against the
  archived `gumrrg` model's 0.487), so the machine reports RST **`unavailable(withheld)`**
  until the owner rules otherwise. The `rdam.rst` parser façade and command below still
  load those releases for local use; the gate governs the machine, not the parser.

## RST: command line

```bash
# Canonical analysis of text, or of a Markdown / Docling JSON / DocLang / plain-text file
rdam-rst parse --text "Because it rained, the match stopped." \
    --model-store models/model-releases --release-id modernbert-v1-a52b70fbc1a3
rdam-rst parse report.md --model-store models/model-releases --release-id modernbert-v1-a52b70fbc1a3 \
    --output analysis.json          # RFC 8785 canonical JSON, the same bytes the Python API serializes
rdam-rst parse report.md ... --format summary   # presentation-only counts

# Model-free capability discovery (add --model-store/--release-id for the configured parser)
rdam-rst capabilities

# Loopback-only HTTP projection of the same contract
rdam-rst serve --model-store models/model-releases --release-id modernbert-v1-a52b70fbc1a3 --port 8080

rdam-rst version
```

## RST: Python API

```python
from pathlib import Path

from rdam.rst import Parser, RstDocument
from rdam.rst.utils.analysis import tree_stats

parser = Parser.from_model_release(
    Path("models/model-releases"),
    "modernbert-v1-a52b70fbc1a3",
    family="modernbert",
    device="auto",  # CUDA if present, else MPS on Apple Silicon, else CPU
)

text = "On Saturday, Team India won against South Africa by seven runs. The final was played in Barbados."

# 1. DiscourseUnit tree, every node in original-text character coordinates
tree = parser(text)["rst"][0]
stats = tree_stats(tree)
print(stats["depth"], stats["n_leaves"])

# 2. Pre-segmented EDUs (the leaves round-trip exactly)
tree = parser.from_edus(["On Saturday, Team India won against South Africa by seven runs.", "The final was played in Barbados."])["rst"][0]

# 3. Canonical structured analysis (RstAnalysis: nodes, primary edges, optional eRST secondary edges)
analysis = parser.parse_document(RstDocument.from_text(text, document_id="cricket"), output="rst_tree")
print(len(analysis.nodes), len(analysis.primary_edges))
```

### Device and precision

`device=` accepts `"auto"`, `"cpu"`, `"mps"`, `"cuda"`, `"cuda:N"`, or a `torch.device`.
PyTorch has no MPS kernel for `torch.linalg.qr` (used during weight initialisation);
the parser routes it through CPU automatically.

`dtype=` (`torch.bfloat16`, `torch.float16`, or the strings `bf16` / `fp16` / `fp32`)
runs the forward pass under `torch.autocast` without changing the trained weights;
the default is `float32` on every device. Tree topology and EDU segmentation are
bit-equivalent across the three dtypes; relation labels on near-tied nodes can flip
under reduced precision. `tests/integration/test_integration.py` is the equivalence
suite.

### Understanding the tree

Each `DiscourseUnit` node carries:

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

Leaves are EDUs; internal nodes are relations. When parsing many documents,
`tree.clear_textfields()` drops the per-node substrings (keep the structure, store it) and
`tree.fill_textfields(full_text)` restores them; `.to_rs3()` needs the text present.

## RST: production source ingest

`rdam.rst.ingest` is the single production boundary for analysing real source material:
plain text, exact pre-segmented EDUs, Markdown, DoclingDocument JSON, and DocLang XML or
`.dclx` archives. There are no separate format parse functions, envelopes, or caches.

```python
from pathlib import Path

from rdam.rst import Parser
from rdam.rst.ingest import ProductionIngestor, SourceArtifact, describe_capabilities, serialize_contract

print(describe_capabilities().semantic.source_forms)  # availability of all six forms, model-free

parser = Parser.from_model_release(Path("models/model-releases"), "modernbert-v1-a52b70fbc1a3", family="modernbert")
ingestor = ProductionIngestor(parser=parser)

outcome = ingestor.analyse(SourceArtifact.from_path(Path("report.md")), cache_directory=Path("cache"))
print(outcome.semantic.status)                 # analysed | empty_primary_discourse
analysis = outcome.semantic.analysis           # the RstAnalysis, or None when nothing authored was found
preparation = outcome.semantic.preparation.semantic
print(preparation.inventory_coverage.covered_units == preparation.inventory_coverage.total_units)
assert outcome.semantic.validation is not None and outcome.semantic.validation.passed
canonical_bytes = serialize_contract(outcome)  # RFC 8785; load_contract() reads it back identically
```

The source is inventoried completely first; the explicit `AUTHORED_PROSE_V1` policy then
admits authored headings, prose, meaningful list items, and authored turns to primary RST
analysis. Tables, code, formulas, raw markup, pictures, metadata, fields, and assets remain
retained side channels; machine-generated descriptions, notes, navigation, furniture,
backgrounds, and invisible content are excluded from primary RST but stay in the receipt.
Every decision is in the preparation outcome, source anchors survive into the analysis,
long sources are subdivided at structure and parser-capacity boundaries and recombined
into one anchored result, and cache identity includes the complete analytical pipeline
fingerprint. Failures are typed, staged, and private by default. The full contract is in
[`docs/production-api-contract.md`](docs/production-api-contract.md) and
[`docs/production-source-ingest.md`](docs/production-source-ingest.md).

## RST: visualising a tree

```python
import rdam.rst as rst

tree.to_rs3("document.rs3")          # RSTTool / rstWeb format
rst.render("document.rs3")           # inline in Jupyter (colab=True syncs the cell height in Colab)
rst.to_html("document.rs3", "document.html")
rst.to_png("document.rs3", "document.png")   # Playwright + Chromium: `playwright install chromium`
rst.to_pdf("document.rs3", "document.pdf")
```

<img src="examples/example-image.png" alt="Illustration of a rendered RST tree" width="600">

## RST: extended RST, long documents, diagnostics

**Extended RST (eRST)** — non-projective secondary relations and discourse signals as in
GUM eRST / RS4: `rdam.rst.erst.rs4` reads and writes RS4 XML (`RS4Reader`, `RS4Writer`,
`rs4_to_document_and_analysis`); `rdam.rst.erst.neural_scorer.NeuralSecondaryEdgeScorer`
scores candidate secondary relations; the decoder in `rdam.rst.erst.decoder` applies
exactly four formal constraints (sufficient signal, no self-loop, both endpoints exist,
no duplicate directed pair). `parser.parse_document(document, output="erst_graph")`
requires a validated eRST completion bundle and refuses, rather than fabricates, without
one.

**Long documents** — `rdam.rst.hierarchical.HierarchicalSectionStitcher(parser).parse_hierarchical(document)`
parses each section into a local tree, parses the macro relations across section roots,
and stitches them into one globally consistent `RstAnalysis`.

**Quality diagnostics** — `pixi run rst-diag <paths> --model-store models/model-releases --release-id <id>`
reports, per source, prepared characters and segments, EDU and relation counts, the
share of thin relations (joint / same-unit / organization), tree skew, and all coverage
ratios; `--json` for machine output.

## Production package and offline workbench

`rdam` is the importable production product. Its wheel and source distribution carry only
the `rdam/` import root and exclude corpus builders, trainers, evaluators, research
harnesses, tests, scripts, experiment data, model candidates, and the vendored ontology
(only the projected framework identities ship).

`workbench/` is the one repository-only surface for corpus preparation, training,
evaluation, research, and promotion. Production never imports it; the check is causal:

```bash
pixi run -e default production-boundary          # import walk from rdam, ownership, dependencies
pixi run -e production production-import-check   # imports the installed distribution, loads no weights
pixi run -e production production-clean-install  # certifies the built wheel in fresh venvs, network off
```

Release: tag `v<version>` (the version in `pyproject.toml`), `pixi run build-production`
(reproducible double build into ignored `dist/<version>/`),
`pixi run validate-production-artifacts`, then the clean install. Every release tool
derives name and version from `pyproject.toml`. The ownership map is in
[`docs/production-offline-boundary.md`](docs/production-offline-boundary.md).

## Archived research parser families

The DMRST and UniRST families (`rstdt`, `gumrrg`, `rstreebank`, `rrtrrg`, `unirst`) are
archived from production: `Parser` refuses their `hf_model_version` values before loading
anything, and their code lives under `workbench/archive/legacy_2021/`. Their published
end-to-end results are kept here as the record they are.

<details>
<summary>Published metrics of the archived families (Seg / S / N / R / Full)</summary>

**Supported languages (`unirst`):** English (eng), Czech (ces), German (deu), Basque (eus), Persian (fas), French (fra), Dutch (nld), Brazilian Portuguese (por), Russian (rus), Spanish (spa), Chinese (zho).

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
Evaluation is offline-only: standard/soft Parseval and the eRST scorer live under
`workbench.evaluation.rst`.

</details>

## Project status & licence

This repository is Steve Allison's evolution of the IsaNLP RST Parser into the
Rhetorical Discourse Analysis Machine. The original RST research code and the archived
research model weights are by Elena Chistova; the MIT-licensed source carries her
copyright. This repository adds the machine, the Dung and IBIS providers, the evidence-gated
promotion system, canonical source ingest, eRST completion, pixi-managed builds, a pytest
suite, GitHub Actions CI, MPS / Apple-Silicon support, and mixed-precision dispatch.

- **Source code:** MIT — see [`LICENSE`](LICENSE). Copyright Elena Chistova 2020 for the
  original parser; Steve Allison's contributions also under MIT.
- **Archived research model weights** (`tchewik/isanlp_rst_v3` on HuggingFace):
  **CC BY-NC 4.0 — research and non-commercial use only.** See
  [`LICENSE_MODELS`](LICENSE_MODELS).
- **ModernBERT releases in `models/model-releases`:** fine-tuned from
  `answerdotai/ModernBERT-base`; each release manifest records its licence and use
  restrictions, and the promotion decision beside it records the evidence verdict.

Issues and pull requests: `Steve-Allison/isanlp_rst`. For questions about the underlying
RST research, see Elena Chistova's papers cited below.

## Citation

The archived research model weights are by Elena Chistova. If you use them in research, please cite:

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

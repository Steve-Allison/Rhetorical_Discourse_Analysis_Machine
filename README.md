# Rhetorical Discourse Analysis Machine (`rdam`)

![Python](https://img.shields.io/badge/python-3.14%2B-blue) ![License](https://img.shields.io/badge/license-MIT_(code)_/_CC_BY--NC_4.0_(archived_weights)-orange) ![Apple Silicon](https://img.shields.io/badge/Apple_Silicon-MPS-blueviolet)

`rdam` runs several discourse and argumentation techniques on one text, natively and
side by side, and reports one explicit outcome per technique. It never collapses them
into a common formalism, never generates or rewrites text, and never says a technique is
available unless recorded evidence says so. It serves one person on one local machine.

```text
                       ┌────────────────────────────────────────────────┐
  text ───────────────▶│  rdam.Machine                                  │
  supplied structures ▶│   capabilities()  one state per technique      │
                       │   analyse()       one outcome per technique    │
                       └───┬──────────────┬──────────────┬─────────────┘
                           ▼              ▼              ▼
                    rdam.rst         rdam.dung       rdam.ibis         (sdrt, toulmin, walton, pdtb:
                    RST / eRST       abstract        gIBIS              unavailable, no provider)
                    DMRST / UniRST   argumentation   link grammar
                    parsers          semantics
```

## Contents

- [What is in the package](#what-is-in-the-package)
- [Design principles](#design-principles)
- [Installation](#installation)
- [Using the machine](#using-the-machine)
- [Capability comes from evidence](#capability-comes-from-evidence)
- [Provider: RST / eRST (`rdam.rst`)](#provider-rst--erst-rdamrst)
- [Provider: Dung abstract argumentation (`rdam.dung`)](#provider-dung-abstract-argumentation-rdamdung)
- [Provider: IBIS (`rdam.ibis`)](#provider-ibis-rdamibis)
- [Repository layout](#repository-layout)
- [Development, gates, and release](#development-gates-and-release)
- [Status and roadmap](#status-and-roadmap)
- [Provenance and licence](#provenance-and-licence)
- [Citation](#citation)

## What is in the package

One distribution, one import package, every technique a sub-package.

| Sub-package | Technique | Provides | State (2026-09-02) |
|---|---|---|---|
| `rdam` | the machine | `Machine`, `AggregateRequest`, typed provider declarations, capability states, native results, outcomes, and the `PromotionDecision` contract | — |
| `rdam.rst` | RST and Extended RST | DMRST and UniRST discourse parsers (Steve Allison's evolution of Elena Chistova's IsaNLP RST Parser), canonical source ingest, eRST completion, the RS3 viewer, the `rdam-rst` command, and the machine adapter | `available` with promoted/redeclared release |
| `rdam.dung` | Dung abstract argumentation | grounded, complete, preferred, and stable extensions of a supplied argument–attack framework, exact by construction | `available` |
| `rdam.ibis` | IBIS | issue–position–argument structures validated under the gIBIS link grammar and organised into a deliberation map | `available` |
| — | SDRT, Toulmin, Walton, PDTB | nothing yet; the machine reports `unavailable(no_promoted_implementation)`. No stubs. | — |

## Design principles

- **Native, side by side.** Each technique keeps its own formalism, relation inventory,
  and result payload. The machine hands a provider's own outcome envelope back verbatim;
  it does not translate RST trees into argument graphs or vice versa.
- **Analysis only.** The machine describes discourse. It has no generation or rewriting
  path, by design and by contract.
- **One outcome per technique, always.** `analyse()` returns exactly one of
  `ResultOutcome`, `UnavailableOutcome(reason)`, or `FailedOutcome(failure)` for every
  requested technique. A failure in one technique never hides a result in another; the
  machine never retries; internal bugs propagate instead of being relabelled.
- **Capability is evidence.** A provider is `available` only under a recorded
  `PromotionDecision` whose evidence is admissible and which names the exact artifact.
  No decision, a withheld decision, or a source change the decision did not evaluate
  all mean `unavailable`, with a stable reason.
- **Structure in, structure out.** Formal techniques (Dung, IBIS) take a supplied
  structure and never extract one from text. A text-only request for them is
  `unavailable(missing_structured_input)`, not a guess.
- **One person, one machine.** No multi-user, distributed, or enterprise machinery.
  Pixi-managed, Apple-Silicon-first, MPS-aware, with a real test suite and CI.

## Installation

In this checkout:

```bash
git clone https://github.com/Steve-Allison/Rhetorical_Discourse_Analysis_Machine.git
cd Rhetorical_Discourse_Analysis_Machine
pixi install -e production
pixi run -e production production-import-check
```

Into any Python 3.14 environment:

```bash
pip install "rdam @ git+https://github.com/Steve-Allison/Rhetorical_Discourse_Analysis_Machine.git"

# Markdown, Docling JSON, and DocLang source adapters are supplied by the `formats` extra
pip install "rdam[formats] @ git+https://github.com/Steve-Allison/Rhetorical_Discourse_Analysis_Machine.git"
```

No model weight ships in the wheel. RST inference uses either published models (e.g. `gumrrg`, `unirst`) or an immutable local model release (`models/model-releases/<release_id>/` or `~/.cache/isanlp_rst/model-releases/<release_id>/` with its manifest); releases include DMRST models (`gumrrg-eb1d5745f3a1`, `rstdt-cc01afde1232`) and UniRST models (`unirst-9407970f1d9d`). Dung and IBIS need nothing beyond the package.

Development uses the `default` environment (`pixi install`, then `pixi run test`).

## Using the machine

```python
from pathlib import Path

from rdam import AggregateRequest, Machine, ResultOutcome, SourceIdentity, StructuredInput, Technique
from rdam.dung import DungProvider
from rdam.ibis import IbisProvider
from rdam.rst.provider import RstProvider

machine = Machine(
    [
        RstProvider(store=Path("models/model-releases"), release_id="gumrrg-eb1d5745f3a1"),
        DungProvider(),
        IbisProvider(),
    ]
)
```

**Capabilities** are reported without loading anything — one state per technique,
including the techniques that have no provider:

```python
for item in machine.capabilities().techniques:
    print(item.technique.value, item.capability)
# rst    UnavailableCapability(reason='withheld')
# pdtb   UnavailableCapability(reason='no_promoted_implementation')
# ...
# dung   AvailableCapability(provider_id='rdam.dung/exhaustive-subset-v1', ...)
# ibis   AvailableCapability(provider_id='rdam.ibis/gibis-grammar-v1', ...)
```

**Text in, one outcome per technique out:**

```python
aggregate = machine.analyse(AggregateRequest.for_text("Because it rained, the match stopped.", (Technique.RST, Technique.SDRT)))
for outcome in aggregate.outcomes:
    print(outcome)                      # ResultOutcome | UnavailableOutcome | FailedOutcome
rst = aggregate.outcome_for(Technique.RST)
if isinstance(rst, ResultOutcome):
    print(rst.result.payload["kind"])  # the RST provider's own outcome envelope, verbatim
```

**Structure in, for the formal techniques:**

```python
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

A malformed structure is a `FailedOutcome` with a stable code and a declared
retryability (`invalid_argumentation_framework`, `not_retryable`); a text-only request
for Dung or IBIS is `UnavailableOutcome(reason='missing_structured_input')`. Every
`AggregateAnalysis` serializes to RFC 8785 canonical JSON with a self-checking
`semantic_digest`.

**Lineage, declared not inferred.** If you built a framework from an earlier RST result,
say so: carry that exact result in the request and name it from the structured input.
The machine re-emits the upstream result untouched, the Dung payload records
`input_origin: explicitly_derived` with the upstream identity, and the aggregate's
`lineage` names both provider identities and the upstream artifact's digest. The
machine never derives one technique's input from another's output itself.

```python
from rdam import UpstreamResultReference

request = AggregateRequest(
    source=rst.result.source,
    text=None,
    techniques=(Technique.DUNG,),
    structured_inputs=(
        StructuredInput(
            technique=Technique.DUNG,
            payload=framework,
            derived_from=UpstreamResultReference(technique=Technique.RST, result_identity=rst.result.semantic_digest),
        ),
    ),
    upstream_results=(rst.result,),
)
print(machine.analyse(request).lineage)
```

## Capability comes from evidence

A `PromotionDecision` (`rdam.promotion`) records six evidence classes — output quality
(empirical, with gold data and baselines, or formal, with correctness arguments and
property tests), calibration, latency and resources, compatibility, provenance, and
licensing — and one of four outcomes: `promote`, `withhold`, `replace`, `retire`. A
`promote` or `replace` decision cannot be constructed unless every class is admissible;
installation success, a green test run, or the existence of an artifact is never
evidence, because there is no field for it.

Decisions live in the workbench ledger `workbench/promotions/<technique>/` and are
bound to the exact artifact they evaluated:

- `rdam.dung` and `rdam.ibis` package their decision beside their code, bound to the
  digest of their own source files. Changing the source without a new decision makes the
  provider `unavailable(no_promoted_implementation)`.
- `rdam.rst` reads the decision published beside the configured model release
  (`<store>/<release_id>.promotion.json`) and checks its artifact digest against the
  release manifest before any inference. A decision cannot be borrowed by a different
  set of weights.

Promoted releases such as `gumrrg-eb1d5745f3a1` and `unirst-9407970f1d9d` provide production
discourse tree parsing through `RstProvider` and `Parser`.

## Provider: RST / eRST (`rdam.rst`)

Rhetorical Structure Theory parsing from raw text or exact pre-segmented EDUs, with
Extended RST (non-projective secondary relations and discourse signals, as in GUM eRST /
RS4) as a second formalism with its own capability state.

### Command line

```bash
# Canonical analysis of text, or of a Markdown / Docling JSON / DocLang / plain-text file
rdam-rst parse --text "Because it rained, the match stopped."
rdam-rst parse report.md --output analysis.json          # RFC 8785 canonical JSON
rdam-rst parse report.md --format summary                # presentation-only counts

rdam-rst capabilities                                    # model-free discovery
rdam-rst serve --port 8080
rdam-rst version
```

`serve` binds only to a loopback host and exposes `POST /analyse`, `GET /capabilities`,
and `GET /health` with the same canonical contract as the command.

### Python

```python
from pathlib import Path

from rdam.rst import Parser, RstDocument
from rdam.rst.utils.analysis import tree_stats

# Load from an immutable model release:
parser = Parser.from_model_release(
    Path.home() / ".cache/isanlp_rst/model-releases",
    "gumrrg-eb1d5745f3a1",
    device="auto",  # CUDA if present, else MPS on Apple Silicon, else CPU
)
# Or initialize from published model weights:
# parser = Parser(hf_model_version="gumrrg", device="auto")

text = "On Saturday, Team India won against South Africa by seven runs. The final was played in Barbados."

tree = parser(text)["rst"][0]                      # DiscourseUnit tree, original-text character offsets
print(tree_stats(tree)["depth"], tree_stats(tree)["n_leaves"])

tree = parser.from_edus(["On Saturday, Team India won against South Africa by seven runs.", "The final was played in Barbados."])["rst"][0]

analysis = parser.parse_document(RstDocument.from_text(text, document_id="cricket"), output="rst_tree")
print(len(analysis.nodes), len(analysis.primary_edges))   # canonical RstAnalysis graph
```

Each `DiscourseUnit` node carries `id`, `left`, `right`, `relation`, `nuclearity`
(`NS` / `SN` / `NN`), `entropy`, `start`, `end`, and `text`; leaves are EDUs. When
holding many trees, `tree.clear_textfields()` drops the substrings and
`tree.fill_textfields(full_text)` restores them.

`device=` accepts `"auto"`, `"cpu"`, `"mps"`, `"cuda"`, `"cuda:N"`, or a `torch.device`.
`dtype=` (`bf16` / `fp16` / `fp32`, or a `torch.dtype`) runs the forward pass under
`torch.autocast`; the default is `float32` everywhere. Tree topology and segmentation are
bit-equivalent across dtypes; relation labels on near-tied nodes can flip under reduced
precision (`tests/integration/test_integration.py` is the equivalence suite).

### Production source ingest

`rdam.rst.ingest` is the one production boundary for real source material: plain text,
exact pre-segmented EDUs, Markdown, DoclingDocument JSON, and DocLang XML or `.dclx`
archives.

```python
from pathlib import Path

from rdam.rst import Parser
from rdam.rst.ingest import ProductionIngestor, SourceArtifact, describe_capabilities, serialize_contract

print(describe_capabilities().semantic.source_forms)   # all six forms and their availability, model-free

parser = Parser.from_model_release(Path.home() / ".cache/isanlp_rst/model-releases", "gumrrg-eb1d5745f3a1")
ingestor = ProductionIngestor(parser=parser)

outcome = ingestor.analyse(SourceArtifact.from_path(Path("report.md")), cache_directory=Path("cache"))
print(outcome.semantic.status)                 # analysed | empty_primary_discourse
analysis = outcome.semantic.analysis           # RstAnalysis, or None when nothing authored was found
preparation = outcome.semantic.preparation.semantic
print(preparation.inventory_coverage.covered_units == preparation.inventory_coverage.total_units)
assert outcome.semantic.validation is not None and outcome.semantic.validation.passed
canonical_bytes = serialize_contract(outcome)  # load_contract() reads it back identically
```

The source is inventoried completely first; the `AUTHORED_PROSE_V1` policy then admits
authored headings, prose, meaningful list items, and authored turns to primary RST
analysis, and keeps tables, code, formulas, raw markup, pictures, metadata, fields,
assets, machine-generated descriptions, notes, navigation, and furniture as receipted
side channels. Source anchors survive into the analysis; long sources are subdivided at
structure and parser-capacity boundaries and recombined into one anchored result; cache
identity includes the complete pipeline fingerprint; failures are typed, staged, and
private by default. Contract: [`docs/production-api-contract.md`](docs/production-api-contract.md),
[`docs/production-source-ingest.md`](docs/production-source-ingest.md).

### Viewer, eRST, long documents, diagnostics

```python
import rdam.rst as rst

tree.to_rs3("document.rs3")                 # RSTTool / rstWeb format
rst.render("document.rs3")                  # inline in Jupyter (colab=True in Colab)
rst.to_html("document.rs3", "document.html")
rst.to_png("document.rs3", "document.png")  # Playwright + Chromium: `playwright install chromium`
rst.to_pdf("document.rs3", "document.pdf")
```

<img src="examples/example-image.png" alt="A rendered RST tree" width="600">

- **eRST**: `rdam.rst.erst.rs4` reads and writes RS4 XML (`RS4Reader`, `RS4Writer`,
  `rs4_to_document_and_analysis`); `rdam.rst.erst.neural_scorer.NeuralSecondaryEdgeScorer`
  scores candidate secondary relations; the decoder in `rdam.rst.erst.decoder` applies
  exactly four formal constraints (sufficient signal, no self-loop, both endpoints exist,
  no duplicate directed pair). `parser.parse_document(document, output="erst_graph")`
  requires a validated eRST completion bundle and refuses without one rather than
  fabricating edges.
- **Long documents**: `rdam.rst.hierarchical.HierarchicalSectionStitcher(parser).parse_hierarchical(document)`
  parses each section, parses the macro relations across section roots, and stitches one
  globally consistent `RstAnalysis`.
- **Diagnostics**: `pixi run rst-diag <paths> --model-store models/model-releases --release-id <id>`
  reports prepared characters and segments, EDU and relation counts, the share of thin
  relations, tree skew, and every coverage ratio per source (`--json` for machine output).

## Provider: Dung abstract argumentation (`rdam.dung`)

Formal evaluation of a supplied argumentation framework under the semantics Dung (1995)
defines. Input is `{"arguments": [...], "attacks": [[attacker, attacked], ...]}`; the
payload returned carries the framework as accepted, `input_origin: supplied`, the
extensions under `grounded`, `complete`, `preferred`, and `stable` semantics, and the
algorithm identity (`exhaustive-subset` v1, capacity 14 arguments).

Complete extensions are found by exhaustive enumeration of every candidate set under the
declared capacity, so the result is exact by construction; grounded is computed
independently by fixed-point iteration and checked against the enumerated complete
extensions. A framework beyond capacity is refused with a typed failure
(`framework_exceeds_declared_capacity`), never approximated. Invariants are tested
exhaustively over all 512 three-argument frameworks and over seeded random frameworks
(`tests/dung`). Semi-stable, ideal, and stage semantics, and larger frameworks, would be a
new candidate with its own decision.

## Provider: IBIS (`rdam.ibis`)

IBIS (Kunz & Rittel 1970) records deliberation as *issues*, *positions*, and
*arguments*. The provider validates a supplied structure under the gIBIS link grammar
(Conklin & Begeman 1988) and returns it organised, judging nothing:

| relation | from | to |
|---|---|---|
| `responds_to` | position | issue |
| `supports`, `objects_to` | argument | position |
| `generalizes`, `specializes`, `replaces` | issue | issue |
| `questions`, `is_suggested_by` | issue | issue, position, argument |

Every position responds to exactly one issue; every argument supports or objects to
exactly one position; ids are unique; self-links are refused. Input is
`{"nodes": [{"id", "kind", "text"}], "links": [{"from", "relation", "to"}]}`; the payload
carries the structure as accepted, `input_origin: supplied`, `extraction: None`, the
grammar id, and a `map` of each issue with its positions and their supporting and
objecting arguments, plus the gaps (issues without positions, positions without
arguments, isolated nodes). The type table is checked exhaustively for all
3 × 3 × 8 kind–kind–relation combinations (`tests/ibis`). Argument strength or
acceptability is the Dung provider's job, not this one's.

## Repository layout

```text
rdam/                        the distribution and import package — the machine
├── contracts.py, machine.py, promotion.py, frameworks.py, serialization.py
├── resources/framework-identities.json   coe: identities projected from the vendored taxonomy
├── rst/                     RST/eRST provider: parser, ingest, erst, rstviewer, cli, provider.py
├── dung/                    semantics.py, provider.py, resources/promotion-decision.json
└── ibis/                    grammar.py, provider.py, resources/promotion-decision.json
ontology/                    vendored Central distribution + the rdam LinkML profile (not shipped)
workbench/                   the one experimentation root: corpora, training, evaluation, research,
                             promotion tooling, and the decision ledger workbench/promotions/
models/model-releases/       immutable local releases, each with its manifest, promotion decision
                             sidecar, and compatibility re-declaration sidecar
tools/production_boundary/   boundary inspection, reproducible build, artifact validation,
                             clean install, classified baseline comparison
tests/  specs/  docs/        verification, decision-closed feature records, documentation
```

Production code never imports `workbench`, and no wheel or sdist member carries anything
outside `rdam/`; `pixi run -e default production-boundary` proves both. Each technique
declares exactly one canonical framework identity from Central's
`coe:artifact/narrative/analytical_frameworks_taxonomy`, referenced and never redefined
(`pixi run ontology-validate`).

## Development, gates, and release

Every Python invocation goes through pixi; the task table in `pyproject.toml` is the
authority (`pixi task list`).

```bash
pixi run lint && pixi run typecheck && pixi run test    # ruff, pyright strict, fast suite
pixi run mdlint                                         # markdownlint over the tracked Markdown
pixi run -e default production-boundary                 # import walk from rdam, ownership, dependencies
pixi run ontology-validate                              # LinkML profile, bindings, projection currency
pixi run smoke                                          # every stored release on every available device
pixi run test-all                                       # everything, including the slow model suites
```

Release: tag the commit `v<version>` (the version declared once in `pyproject.toml`),
then

```bash
pixi run build-production                    # reproducible double build into ignored dist/<version>/
pixi run validate-production-artifacts       # RECORD, metadata, provenance, entry point, public surface
pixi run -e production production-clean-install   # fresh venvs, network off, full acceptance on a release
```

Every release tool derives the distribution name and version from `pyproject.toml`;
`dist/` is never tracked, and the committed record is the evidence JSON under the feature
that made the release. A stored model release runs under a later package line only
through an evidence-backed, manifest-bound compatibility re-declaration
(`pixi run redeclare-compatibility`), never by editing the immutable manifest.
`pixi run rst-baseline compare` proves the RST public contract analytically equivalent
across such changes, classifying every field-level difference before giving a verdict.

## Status and roadmap

Built on 2026-09-02 against the decision-closed architecture in
`specs/006-rhetorical-discourse-machine/`, feature by feature (`specs/007-…` to
`specs/012-…`): the aggregate contract and ontology vendoring, the evidence-gated
promotion system, the RST provider adapter, the repository migration and the
single-package restructure, and the Dung and IBIS providers. Release 6.0.0 is tagged and
certified; the release record is in
[`specs/010-repository-migration/evidence/gates.md`](specs/010-repository-migration/evidence/gates.md).

Persisted contract identifiers (`isanlp_rst.production` 2.0.0, `isanlp_rst.parser/dmrst-v1`,
`isanlp_rst.parser/unirst-v1`) name immutable runtime contracts, not the package.

Provider order thereafter: SDRT, then Toulmin and Walton, then PDTB if ever — each only
once workbench evidence identifies a credible candidate, each with its own
decision-closed feature and its own decision.

## Provenance and licence

This repository is Steve Allison's evolution of the IsaNLP RST Parser into the
Rhetorical Discourse Analysis Machine. The original RST research code and the archived
research model weights are by Elena Chistova; the MIT-licensed source carries her
copyright. The machine, the Dung and IBIS providers, the promotion system, canonical
source ingest, eRST completion, and the build and release tooling are Steve's own code.

- **Source code:** MIT — see [`LICENSE`](LICENSE). Copyright Elena Chistova 2020 for the
  original parser; Steve Allison's contributions also under MIT.
- **Production model weights** (`tchewik/isanlp_rst_v3` on HuggingFace, families
  `rstdt`, `gumrrg`, `rstreebank`, `rrtrrg`, `unirst`): **CC BY-NC 4.0 — research and
  non-commercial use only**, see [`LICENSE_MODELS`](LICENSE_MODELS). These models power
  `PredictorDMRST` and `PredictorUniRST` through `Parser`.
- **Workbench research experiments:** candidate architectures (e.g. ModernBERT) reside
  strictly under `workbench/` and are evaluated against baselines before any promotion.

Issues and pull requests: `Steve-Allison/Rhetorical_Discourse_Analysis_Machine`.

## Citation

The archived research model weights are by Elena Chistova. If you use them in research,
please cite:

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

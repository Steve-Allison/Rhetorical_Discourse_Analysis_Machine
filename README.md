# Rhetorical Discourse Analysis Machine (`rdam`)

![Python](https://img.shields.io/badge/python-3.14%2B-blue) ![License](https://img.shields.io/badge/license-MIT_(code)_/_CC_BY--NC_4.0_(archived_weights)-orange) ![Apple Silicon](https://img.shields.io/badge/Apple_Silicon-MPS-blueviolet)

`rdam` runs thirteen discourse, rhetorical, and argumentation techniques on one source
document, natively and side by side, and reports one explicit outcome per technique
(`rdam/frameworks.py:55-69`, `rdam/composition.py:14-73`). It never collapses them into a
common formalism, never generates or rewrites text, and reports locally checked
prerequisites separately from actual runtime success. It serves one person on one local
machine.

```text
  text / .dclg / .dclx / edus → rdam.ingest (dclq + DocLang 0.9)
                                           ↓
                     complete inventory + LinguisticSubstrate
                                           ↓
  Wave 1: RST · Centering · PDTB · SDRT · Speech Acts · Classical Rhetoric
          Argument Mining · Toulmin · Walton · Pragma-Dialectics · IBIS · ASPIC+
                                           ↓
  Wave 2 (explicit derivations) or supplied AF → Dung (CaDiCaL SAT)
                                           ↓
             separate native outcomes + dclq xpath_alignment
```

## Contents

- [What is in the package](#what-is-in-the-package)
- [Design principles](#design-principles)
- [Installation](#installation)
- [Using the machine](#using-the-machine)
- [Capability and provenance](#capability-and-provenance)
- [Provider: RST (`rdam.rst`)](#provider-rst-rdamrst)
- [Deterministic and dual-mode providers](#deterministic-and-dual-mode-providers)
- [LLM-backed discourse, rhetorical, and argumentation providers](#llm-backed-discourse-rhetorical-and-argumentation-providers)
- [Repository layout](#repository-layout)
- [Development, gates, and release](#development-gates-and-release)
- [Status and roadmap](#status-and-roadmap)
- [Provenance and licence](#provenance-and-licence)
- [Citation](#citation)

## What is in the package

One distribution, one import package, every technique a sub-package (`pyproject.toml:5-48`).

| Sub-package | Technique | Provides | Availability requirement |
|---|---|---|---|
| `rdam` | the machine | Python API, unified `rdam` CLI, optional HTTP API, shared requests, 2-wave derivations, `xpath_alignment`, and native results | — |
| `rdam.ingest` | shared source preparation | `dclq` + DocLang 0.9 complete inventory, `LinguisticSubstrate`, provider projections, source anchors, and receipts | core package |
| `rdam.concepts` | lexical concept linking | exact Rust `ahocorasick_rs` mention links from source surfaces to Central's semantic resources | `available` |
| `rdam.rst` | RST | DMRST and UniRST discourse parsers, the RS3 viewer, and `RstProvider` | configured parser |
| `rdam.centering` | Centering Theory | deterministic `Cb`/`Cp`/`Cf` transitions (Grosz–Joshi–Weinstein) and Barzilay–Lapata entity grid | `available` |
| `rdam.pdtb` | PDTB | PDTB-3 binary discourse relations, all seven relation types, signal spans, and senses | configured language model |
| `rdam.sdrt` | SDRT | validated Asher & Lascarides SDRS graphs with EDUs, CDUs, DISCOR polarity, and right-frontier checks | configured language model |
| `rdam.speech_acts` | Speech Acts | Searle & Vanderveken illocutionary acts, direction of fit, felicity conditions, and uptake links | configured language model |
| `rdam.classical_rhetoric` | Classical Rhetoric | Aristotelian pisteis (`ethos`, `pathos`, `logos`), enthymemes, stasis, kairos, and figures | configured language model |
| `rdam.argument_mining` | Argument Mining | Inference Anchoring Theory (IAT) propositions (`I`-nodes) and `RA`/`CA`/`MA`/`PA` anchors | configured language model |
| `rdam.toulmin` | Toulmin | claims, grounds, warrants, backing, qualifiers, and source-anchored rebuttals | configured language model |
| `rdam.walton` | Walton | 12 typed argumentation scheme instances with premise roles and critical-question states | configured language model |
| `rdam.pragma_dialectics` | Pragma-Dialectics | four dialectical stages, strategic manoeuvring, and ten-rule fallacy violations | configured language model |
| `rdam.ibis` | IBIS | gIBIS deliberation maps — deterministic validation on supplied structures or grounded extraction on source documents | `available` (supplied) / configured language model (text) |
| `rdam.aspic` | ASPIC+ | Modgil & Prakken structured theories, preferences, defeats, and rationality postulates — supplied or extracted | `available` (supplied) / configured language model (text) |
| `rdam.dung` | Dung abstract argumentation | `grounded`, `complete`, `preferred`, and `stable` extensions via bitmask kernel + CaDiCaL 1.9.5 (`cadical-sat-v2`, capacity 128) | `available` (supplied or explicitly derived) |

## Design principles

- **Native, side by side.** Each technique keeps its own formalism, relation inventory,
  and result payload. The machine hands a provider's own outcome envelope back verbatim;
  it does not collapse RST trees, entity grids, rhetorical appeals, and formal attack
  graphs into a merged representation (`rdam/contracts.py:497-513`).
- **Analysis only.** The machine describes discourse. It has no generation or rewriting
  path, by design and by contract.
- **DocLang-native single-stream ingestion.** Sources enter as `.dclg` XML, `.dclx`
  archives, plain text (synthesized into canonical namespaced `<doclang>` XML), or exact
  pre-segmented EDUs (`rdam/ingest/contracts/source.py:17-21`), queried through native
  `dclq` (`LoadedDocument`, `NS`) and validated with `doclang` (`pyproject.toml:44-45`).
  Only non-content `furniture`, chrome, and operational provenance are pruned: prose,
  lists, tables, charts, Mermaid diagrams, VLM `<description>` blocks, speaker `<notes>`,
  and `<track>` turns stay in one unified XPath-anchored substantive stream for centering
  and LLM-backed extractors (`rdam/ingest/requirements.py:10-24`).
- **One outcome per technique, always.** `analyse()` returns exactly one of
  `ResultOutcome`, `UnavailableOutcome(reason)`, or `FailedOutcome(failure)` for every
  requested technique. A failure in one technique never hides a result in another; the
  machine never adds retries; internal bugs propagate instead of being relabelled.
  Native model boundaries retain their explicit bounded retry policies.
- **Capabilities state what was checked.** A provider is `available` when its local
  prerequisites resolve. No remote model probe is performed: credentials or a known model
  name do not prove a remote call will succeed (`model_probe: not_performed`). Otherwise
  it is `unavailable` with one of three stable reasons — `not_implemented`,
  `model_unavailable`, `missing_structured_input` — and never a stub.
- **Explicit formal boundaries and derivations.** `DungProvider` evaluates supplied or
  explicitly derived argumentation frameworks and never guesses an attack graph from raw
  text (`rdam/dung/provider.py:1-7`). Dual-mode `IbisProvider` and `AspicProvider`
  deterministically validate supplied structures when `structured_inputs` are provided and
  perform grounded extraction when given a source document (`rdam/frameworks.py:72-79`).
  When requested via `DerivationSpec` (`--derive`), Wave 2 deterministically compiles
  Wave-1 `aspic`, `argument_mining`, `ibis`, or `toulmin`/`walton` outputs into a Dung
  framework with full `lineage` tracking (`rdam/dung/compilers.py:213-236`).
- **One person, one machine.** No multi-user, distributed, or enterprise machinery.
  Pixi-managed, Apple-Silicon-first, MPS-aware, with a real local test suite.

## Installation

In this checkout:

```bash
git clone https://github.com/Steve-Allison/Rhetorical_Discourse_Analysis_Machine.git
cd Rhetorical_Discourse_Analysis_Machine
pixi install -e production
pixi run -e production production-import-check
```

For another local project using Python 3.14, install the built wheel from this checkout
(use its absolute path when working elsewhere; `dclq` and `doclang[schematron-saxon]`
ship in core dependencies at `pyproject.toml:44-45`):

```bash
pip install dist/6.1.0/rdam-6.1.0-py3-none-any.whl
pip install "dist/6.1.0/rdam-6.1.0-py3-none-any.whl[http]"
```

The source archive is `dist/6.1.0/rdam-6.1.0.tar.gz`. The local package build uses an
isolated local snapshot of the current package inputs; its packaged provenance names that
snapshot commit, not an older tag. `production-import-check` checks the editable source,
not the distributable wheel.

No neural model weight ships in the wheel. The machine defaults to the published `gumrrg`
DMRST checkpoint at its pinned source commit, using `xlm-roberta-large` at a pinned
revision. A manifest- and hash-validated local release can be selected explicitly when
complete local component receipts are required. Known release identifiers include DMRST
models (`gumrrg-eb1d5745f3a1`, `rstdt-cc01afde1232`) and UniRST models
(`unirst-9407970f1d9d`). `CenteringProvider`, `DungProvider`, `rdam.concepts`, and
supplied-structure `IbisProvider` / `AspicProvider` need nothing beyond the package.

Development uses the `default` environment (`pixi install`, then `pixi run test`).

## Using the machine

The primary entry point is `production_machine(config=MachineConfig(...))`
(`rdam/composition.py:14-73`). Python, `rdam`, and optional `rdam[http]` all use this same
engine. Configuration is explicit and immutable; per-technique model choices override the
shared model. Discovery reports configuration without probing model availability on the
network (`model_probe: not_performed`). Analysis supplies the runtime verdict.

```python
from rdam import (
    AggregateRequest,
    DerivationSpec,
    LlmSettings,
    MachineConfig,
    Technique,
    production_machine,
    serialize,
)

machine = production_machine(config=MachineConfig(llm=LlmSettings(model="google-gla:gemini-3.8-flash")))
request = AggregateRequest.for_text(
    "Should we migrate to DocLang? Option A unifies XPath provenance, though legacy readers need updates.",
    (Technique.CENTERING, Technique.TOULMIN, Technique.IBIS, Technique.DUNG),
    derivations=(DerivationSpec(consumer=Technique.DUNG, compiler="from_ibis", upstreams=(Technique.IBIS,)),),
)
analysis = machine.analyse(request)
json_bytes = serialize(analysis)
```

For immediate AI consumption, read `status`, `requested_techniques`, `xpath_alignment`,
and the embedded `reading_guide`, then the corresponding complete native outcomes. Guides
explain native meanings, source-evidence roles, and limitations; they are not confidence
or truth scores. Walton critical questions distinguish `addressed`, `open`, and
`not_assessable`. Toulmin warrants distinguish `explicit`, `reconstructed`, and
`undetermined`, with source evidence or a reason. Supporting text is not proof that an
inference is correct. Retained upstream results are separate from requested outcomes and
cannot improve completion status.

For custom provider composition:

```python
from pathlib import Path

from rdam import AggregateRequest, Machine, ResultOutcome, StructuredInput, Technique
from rdam.aspic import AspicProvider
from rdam.centering import CenteringProvider
from rdam.dung import DungProvider
from rdam.ibis import IbisProvider
from rdam.rst.provider import RstProvider

machine = Machine(
    [
        RstProvider(store=Path("models/model-releases"), release_id="gumrrg-eb1d5745f3a1"),
        CenteringProvider(),
        IbisProvider(),
        AspicProvider(),
        DungProvider(),
    ]
)
```

**Capabilities** are reported without loading model weights or constructing SDK clients —
one state per technique across all thirteen boundaries (`rdam/contracts.py:681-707`):

```python
for item in machine.capabilities().techniques:
    print(item.technique.value, item.capability)
# rst                AvailableCapability(provider_id='rdam.rst/gumrrg-eb1d5745f3a1', ...)
# centering          AvailableCapability(provider_id='rdam.centering/entity-grid-v1', ...)
# pdtb               UnavailableCapability(reason='not_implemented')
# ...
# ibis               AvailableCapability(provider_id='rdam.ibis/gibis-v2/openai:gpt-5.6-sol', ...)
# aspic              AvailableCapability(provider_id='rdam.aspic/aspic-plus-v1/openai:gpt-5.6-sol', ...)
# dung               AvailableCapability(provider_id='rdam.dung/cadical-sat-v2', ...)
```

**Structure in, for formal evaluation:**

```python
framework = {"arguments": ["a", "b", "c"], "attacks": [["a", "b"], ["b", "c"]]}
request = AggregateRequest.for_structured(
    (StructuredInput(technique=Technique.DUNG, payload=framework),),
    techniques=(Technique.DUNG,),
)
dung = machine.analyse(request).outcome_for(Technique.DUNG)
if isinstance(dung, ResultOutcome):
    print(dung.result.payload["extensions"]["grounded"])  # ['a', 'c']
```

A malformed structure is a `FailedOutcome` with a stable code and a declared retryability
(`invalid_argumentation_framework`, `not_retryable`); a text-only request for Dung without
`structured_inputs` or `derivations` is `UnavailableOutcome(reason='missing_structured_input')`.
Every `AggregateAnalysis` serializes to RFC 8785 canonical JSON with a self-checking
`semantic_digest`.

**Lineage, declared or compiled explicitly.** Callers can either request in-run Wave-2
compilation via `derivations=(DerivationSpec(...),)` (`rdam/contracts.py:725`) or pass an
earlier `NativeTechniqueResult` in `upstream_results` paired with `UpstreamResultReference`.
In both cases, the Dung payload records `input_origin: explicitly_derived` with the
upstream identity, and the aggregate's `lineage` names both provider identities and the
upstream artifact's semantic digest.

## Capability and provenance

### Documents, `dclq` XPath alignment, and provider projections

```python
from pathlib import Path
from rdam import AggregateRequest, Technique, production_machine

machine = production_machine()
request = AggregateRequest.for_source(
    Path("tests/fixtures/doclang/real_world/change-of-tenancy.dclg"),
    (Technique.RST, Technique.CENTERING, Technique.TOULMIN, Technique.WALTON),
)
aggregate = machine.analyse(request)
assert aggregate.preparation is not None
print(len(aggregate.preparation.preparation.inventory))
print(len(aggregate.xpath_alignment))  # cross-technique index keyed by canonical dclq XPath
```

`for_bytes(payload, source_form, source_name, techniques)` accepts materialized bytes;
`for_text` accepts a string; `for_edus` accepts pre-segmented EDUs. Construction
identifies the exact bytes without loading models. `rdam.ingest.describe_capabilities()`
is the sole source-form authority (`rdam/ingest/contracts/source.py:17-21`).

Each aggregate inventories once, builds a shared `LinguisticSubstrate`
(`rdam/ingest/substrate.py:330-346`), and computes one projection per distinct provider
requirement:

- **Substantive single-stream projection (`rdam/substantive-stream-v2`):** Centering and
  all ten LLM-capable providers admit titles, headings, paragraphs, list items, dialogue
  turns, captions, VLM `<description>` blocks (`picture_description`), speaker `<notes>`,
  code, formulas, tables, table cells, and fields (`rdam/ingest/requirements.py:10-24`),
  with cell coordinates and explicit table linearisation records.
- **Authored-prose projection (`AUTHORED_PROSE_V1`):** Neural `RstProvider` admits
  authored prose, headings, list items, and turns while retaining tables, code, formulas,
  pictures, notes, and machine-generated descriptions as receipted side channels.
- **Cross-technique XPath index (`AggregateAnalysis.xpath_alignment`):** Every aligned
  finding across every succeeded technique is indexed by canonical `dclq` XPath
  (`/d:doclang[1]/...`) so consumers can inspect how multiple formalisms analyse the exact
  same document element without merging their native schemas (`rdam/contracts.py:508`).

### Execution and caching

`ExecutionPolicy(max_workers=4)` is the default, bounded to one through thirteen
in-process workers. Wave-1 providers execute concurrently (with a Prefix-Warmth
Coordinator warming shared LLM prompt prefixes when multiple techniques share a model);
Wave-2 derived consumers (`Technique.DUNG` with `derivations`) run deterministically once
their declared Wave-1 upstreams complete. Outcomes retain request order.

Caching is opt-in through `MachineConfig(execution=ExecutionSettings(cache_directory=Path("cache")))`
or `ExecutionPolicy(cache_directory=Path("cache"))`. The cache key binds source,
projection, provider, contract, model, and effective instructions (including the shared
constitution prompt). Dirty source revisions bypass caching. Native `artifact_digest`
covers execution details too; `semantic_digest` excludes only execution fields declared by
the provider.

### Provider availability

A technique is `available` when its checked local prerequisites resolve, and `unavailable`
with a stable reason otherwise (`not_implemented`, `model_unavailable`, or
`missing_structured_input`). `rdam.centering` and `rdam.dung` are exact and deterministic,
so they are available whenever imported. Dual-mode `rdam.ibis` and `rdam.aspic` are
available immediately for supplied structures and require a configured LLM model for
document extraction. `rdam.rst` is available when its configured `hf_model_version` is
known to the façade or when its named local model release validates.

## Provider: RST (`rdam.rst`)

Rhetorical Structure Theory parsing from raw text, DocLang sources, or exact
pre-segmented EDUs. The production formalism is `rst_tree`. Extended RST is confined to
the [offline workbench](workbench/erst/README.md) for testing and evaluation.

### Command line

```bash
# Canonical analysis of text or of a DocLang (.dclg / .dclx) / plain-text file
rdam analyse --text "Because it rained, the match stopped." --techniques rst,centering
rdam analyse document.dclg --techniques rst,centering,toulmin,walton,ibis,dung \
  --derive from_ibis --output analysis.json
rdam summary analysis.json                              # optional terminal inspection
rdam view analysis.json --techniques walton              # whole native result, no rerun
rdam prepare document.dclg                              # complete inventory, no inference
rdam concepts link --request link-request.json          # exact lexical links to Central
rdam capabilities                                      # model-free discovery across 13 boundaries
rdam schema request                                    # machine-readable JSON Schema
rdam serve --port 8080                                  # requires rdam[http]
rdam version
```

Files or stdin (`-`) go in; canonical JSON goes to stdout and diagnostics to stderr.
Analysis exits are 0 complete, 3 partial, and 4 unsuccessful; operational failures exit 1,
invalid input 2, interruption 130, and broken pipe 141 (`rdam/cli.py:77,436-518`). File
output is atomic and refuses replacement unless `--force` is explicit; inputs can never be
overwritten. Formal structures can be passed via `--structured dung=framework.json`,
`--structured ibis=map.json`, or `--structured aspic=theory.json`, or derived explicitly
into Dung via `--derive {from_aspic,from_argument_mining,from_ibis,from_toulmin_walton}`
(`rdam/cli.py:136-143`).

`serve` binds only to `127.0.0.1` or `::1`. Routes are `POST /v1/prepare`, `/v1/analyse`,
`/v1/view`, `/v1/summary`, `/v1/concepts/link` and `GET /v1/capabilities`, `/v1/version`,
`/v1/schemas/{record}`. One POST is admitted at a time; discovery stays responsive.

### Python

```python
from pathlib import Path

from rdam.rst import Parser, RstDocument
from rdam.rst.utils.analysis import tree_stats

parser = Parser.from_model_release(
    Path.home() / ".cache/isanlp_rst/model-releases",
    "gumrrg-eb1d5745f3a1",
    device="auto",  # CUDA if present, else MPS on Apple Silicon, else CPU
)

text = "On Saturday, Team India won against South Africa by seven runs. The final was played in Barbados."
tree = parser(text)["rst"][0]                      # DiscourseUnit tree, original-text character offsets
print(tree_stats(tree)["depth"], tree_stats(tree)["n_leaves"])

analysis = parser.parse_document(RstDocument.from_text(text, document_id="cricket"), output="rst_tree")
print(len(analysis.nodes), len(analysis.primary_edges))
```

### Production source ingest

`rdam.ingest` is the single production boundary for source material across all four
canonical `SourceForm` values (`text`, `edus`, `doclang_xml`, `doclang_archive`;
`rdam/ingest/contracts/source.py:17-21`):

```python
from pathlib import Path

from rdam.ingest import ProductionIngestor, SourceArtifact, describe_capabilities, serialize_contract
from rdam.rst import Parser

print(describe_capabilities().semantic.source_forms)   # all four forms, model-free

parser = Parser.from_model_release(Path.home() / ".cache/isanlp_rst/model-releases", "gumrrg-eb1d5745f3a1")
ingestor = ProductionIngestor(parser=parser)

outcome = ingestor.analyse(
    SourceArtifact.from_path(Path("tests/fixtures/doclang/real_world/change-of-tenancy.dclg")),
    cache_directory=Path("cache"),
)
print(outcome.semantic.status)                 # analysed | empty_primary_discourse
canonical_bytes = serialize_contract(outcome)  # load_contract() reads it back identically
```

Long sources are subdivided at structure and parser-capacity boundaries, batched across
predictor windows, and recombined along a nuclear-aware spine into one anchored
`RstAnalysis`. Contract details:
[`docs/production-api-contract.md`](docs/production-api-contract.md) and
[`docs/production-source-ingest.md`](docs/production-source-ingest.md).

### Viewer, long documents, diagnostics

```python
import rdam.rst as rst

tree.to_rs3("document.rs3")                 # RSTTool / rstWeb format
rst.render("document.rs3")                  # inline in Jupyter (colab=True in Colab)
rst.to_html("document.rs3", "document.html")
rst.to_png("document.rs3", "document.png")  # Playwright + Chromium: `playwright install chromium`
rst.to_pdf("document.rs3", "document.pdf")
```

<img src="examples/example-image.png" alt="A rendered RST tree" width="600">

- **eRST is workbench-only** (`workbench/erst/`). Production rejects `erst_graph` and has
  no eRST checkpoint option or automatic bundle loading.
- **Diagnostics**: `pixi run rst-diag <paths> --model-store models/model-releases --release-id <id>`
  reports prepared characters and segments, EDU and relation counts, thin-relation share,
  tree skew, and coverage ratios (`--json` for machine output).

## Deterministic and dual-mode providers

- **Centering (`rdam.centering`, `rdam.centering/entity-grid-v1`):** Deterministic
  entity-coherence tracking over `LinguisticSubstrate` sentences (`rdam/centering/provider.py:37-186`).
  Computes forward-looking centers (`Cf`), preferred center (`Cp`), backward-looking
  center (`Cb`), Grosz–Joshi–Weinstein transitions (`continue`, `retain`, `smooth_shift`,
  `rough_shift`, `establishment`, `zero_cb`), the Barzilay–Lapata role grid (`S`/`O`/`X`/`-`),
  and local coherence score with exact source alignments.
- **Dung abstract argumentation (`rdam.dung`, `rdam.dung/cadical-sat-v2`):** Exact formal
  evaluation under Dung (1995) `grounded`, `complete`, `preferred`, and `stable`
  semantics (`rdam/dung/semantics.py:19-380`). Uses an integer-bitmask grounded fixed
  point followed by Caminada 3-valued complete-labelling CNF enumeration over CaDiCaL
  1.9.5 (`python-sat`, `DEFAULT_CAPACITY = 128`, `MAX_ENUMERATED_EXTENSIONS = 4096`).
  Accepts either caller-supplied `{"arguments": [...], "attacks": [[attacker, attacked], ...]}`
  or deterministic Wave-2 compilation from `aspic`, `argument_mining`, `ibis`, or
  `toulmin`/`walton` (`rdam/dung/compilers.py:213-236`).
- **IBIS (`rdam.ibis`, `rdam.ibis/gibis-v2`):** Dual-mode deliberation mapping under the
  strict gIBIS link grammar (Kunz & Rittel 1970; Conklin & Begeman 1988;
  `rdam/ibis/provider.py:52-310`). Validates supplied `{"nodes": [...], "links": [...]}`
  deterministically (`input_origin: supplied`) or extracts `QuoteRef`-grounded issues,
  positions, and arguments from text/DocLang (`input_origin: extracted`) and organises
  them with structural gap detection.
- **ASPIC+ (`rdam.aspic`, `rdam.aspic/aspic-plus-v1`):** Dual-mode structured
  argumentation under Modgil & Prakken (2013) (`rdam/aspic/provider.py:58-380`). Validates
  supplied or extracted axioms (`Kn`), ordinary premises (`Kp`), strict rules (`Rs`),
  defeasible rules (`Rd`), contraries, and acyclic preferences; constructs finite
  arguments; resolves rebutting, undermining, and undercutting attacks into defeats under
  last-link or weakest-link liftings; evaluates Dung extensions; and verifies Caminada &
  Amgoud rationality postulates (`sub_argument_closure`, `strict_closure`,
  `direct_consistency`, `indirect_consistency`).
- **Lexical concept linking (`rdam.concepts`):** Deterministic Unicode-normalized,
  word-bounded multi-pattern matching over Central's compiled terminology snapshot via
  Rust `ahocorasick_rs` (`rdam/concepts/linker.py:10,79-146`), also feeding
  `concept_mention` signals into `LinguisticSubstrate` (`rdam/ingest/substrate.py:314-324`).

## LLM-backed discourse, rhetorical, and argumentation providers

All LLM-backed providers (`pdtb`, `sdrt`, `speech_acts`, `classical_rhetoric`,
`argument_mining`, `toulmin`, `walton`, `pragma_dialectics`, plus document-mode `ibis` and
`aspic`) share three runtime guarantees (`rdam/_llm.py`, `rdam/_grounding.py`):

1. **Shared-prefix KV caching and modern vendor SDKs:** Every technique prepends the same
   canonical `rdam/resources/shared-system-prompt.md` constitution and byte-identical
   `<source_document>` + `<linguistic_signals>` prefix (`render_cached_source_prefix` at
   `rdam/ingest/substrate.py:371-392`). Vendor adapters use native Google `google-genai`
   GA `v1` Interactions (`aclient.interactions.create(..., store=False)`), OpenAI
   `prompt_cache_key`, and Anthropic `cache_control` breakpoints over pooled HTTP clients.
2. **Single-turn `QuoteRef` grounding:** Models emit compact `(quote, occurrence)`
   references (`rdam/_grounding.py`) that resolve deterministically to exact character
   offsets, `dclq` XPaths, speaker identities, page numbers, and table coordinates, with
   bounded `ModelRetry` feedback on any mismatched quote or structural invariant.
3. **Deterministic native validation:** Every proposal passes its formalism's own
   validator before becoming a `NativeTechniqueResult` — PDTB-3 sense hierarchy and
   distinct argument spans (`rdam.pdtb`), SDRS DAG acyclicity, DISCOR polarity, and Asher
   & Lascarides Right Frontier Constraint (`rdam.sdrt`), Searlean direction-of-fit and
   felicity coherence (`rdam.speech_acts`), Aristotelian pisteis/stasis/enthymeme schema
   (`rdam.classical_rhetoric`), IAT bipartite `I`-node / `RA`·`CA`·`MA`·`PA` acyclicity
   (`rdam.argument_mining`), Toulmin warrant status and source-anchored rebuttals
   (`rdam.toulmin`), 12 discriminated Walton schemes and critical-question inventories
   (`rdam.walton`), and Pragma-Dialectical stage and ten-rule fallacy mapping
   (`rdam.pragma_dialectics`).

## Repository layout

```text
rdam/                        the distribution and import package — the machine
├── contracts.py, machine.py, composition.py, frameworks.py, serialization.py
├── _llm.py, _grounding.py   vendor KV-cache adapters, Interactions API, single-turn QuoteRef grounder
├── resources/               framework-identities.json, concept-index.json, shared-system-prompt.md
├── ingest/                  dclq + DocLang 0.9 inventory, substrate.py, projections, plans, anchors
├── concepts/                Rust ahocorasick_rs lexical linker over Central semantic resources
├── cli.py, http.py          thin terminal and optional loopback /v1/ interfaces
├── rst/                     RST provider: DMRST/UniRST parsers, converter, rstviewer, provider.py
├── centering/               deterministic Centering Theory & Entity Grid provider
├── pdtb/, sdrt/, speech_acts/, classical_rhetoric/   discourse, pragmatic, and rhetorical providers
├── argument_mining/, toulmin/, walton/, pragma_dialectics/   argumentation providers
├── ibis/, aspic/            dual-mode supplied-structure + grounded-extraction providers
└── dung/                    CaDiCaL SAT semantics.py, Wave-2 compilers.py, provider.py
ontology/                    vendored Central distribution + the rdam LinkML profile (not shipped)
workbench/                   the one experimentation root: corpora, training, evaluation, research,
                             eRST, and the model-store release tooling
models/model-releases/       immutable local releases, each with its manifest and compatibility sidecar
tools/production_boundary/   boundary inspection, reproducible build, artifact validation,
                             clean install, classified baseline comparison
tests/  specs/  docs/        verification, decision-closed feature records, documentation
```

Production code never imports `workbench`. The wheel has one Python import root, `rdam/`,
plus distribution metadata; the sdist also includes the README, licenses, and build
configuration. `pixi run production-boundary` checks source ownership;
`pixi run validate-production-artifacts` checks built archives. Each technique declares
exactly one framework identity from Central's
`coe:artifact/narrative/analytical_frameworks_taxonomy` (`rdam/frameworks.py:1-19`),
verified by `pixi run ontology-validate`.

## Development, gates, and release

Every Python invocation goes through pixi; the task table in `pyproject.toml` is the
authority (`pixi task list`).

```bash
pixi run lint && pixi run typecheck && pixi run test    # ruff, pyright strict, fast suite
pixi run lint-production-modern                         # Python 3.14 modernization gate
pixi run mdlint                                         # markdownlint over the tracked Markdown
pixi run production-boundary                            # import walk from rdam, ownership, dependencies
pixi run ontology-validate                              # LinkML profile, 13 bindings, projection currency
pixi run shared-runtime-coverage                        # 100% statement + branch coverage on shared runtime
pixi run shared-runtime-mutation-test                   # 7/7 shared-runtime mutants killed
pixi run rst-format-coverage && pixi run rst-mutation-test
pixi run smoke                                          # every stored release on every available device
pixi run test-all                                       # everything, including the slow model suites
```

For a clean committed source, build and check the package below. When HEAD has a tag, it
must match `v<version>` from `pyproject.toml`:

```bash
pixi run build-production                    # reproducible double build into ignored dist/<version>/
pixi run validate-production-artifacts       # RECORD, metadata, provenance, entry point, public surface
pixi run -e production production-clean-install \
  --model-store "$HOME/.cache/isanlp_rst/model-releases" \
  --release-id gumrrg-eb1d5745f3a1
```

## Status and roadmap

The active production scope (`6.1.0`) comprises all thirteen technique boundaries — `rst`,
`centering`, `pdtb`, `sdrt`, `speech_acts`, `classical_rhetoric`, `argument_mining`,
`toulmin`, `walton`, `pragma_dialectics`, `ibis`, `aspic`, and `dung` — plus
`rdam.concepts`, over Python, the unified `rdam` CLI, and optional `/v1/` HTTP routes.
**eRST remains workbench-only** (`workbench/erst/`) following the owner's 2026-09-06
instruction; no trained eRST accuracy or production readiness is claimed.

Verified on 2026-11-15 in this checkout:

- `pixi run test`: **3,235 passed, 0 failed**; `pixi run smoke`: **95 passed, 0 failed**
  across CPU and MPS model releases.
- `pixi run shared-runtime-coverage`: **100.00%** statement and branch coverage across
  `rdam/_canonical.py`, `rdam/_immutable_json.py`, `rdam/_execution.py`,
  `rdam/_result_cache.py`, `rdam/_provenance.py`, and `rdam/_provider_provenance.py`;
  `pixi run shared-runtime-mutation-test` and `pixi run rst-mutation-test`: **7/7**
  mutants killed each; `pixi run rst-format-coverage`: **95.70%** coverage across the
  `dclq` + DocLang ingest and `LinguisticSubstrate` modules.
- Measured local runtime benchmarks (Apple Silicon, 2026-11-15): cold `import rdam` +
  `production_machine().capabilities()` across 13 techniques in **721.3 ms**;
  `rdam.concepts` Rust `ahocorasick_rs` scan over 50k chars (8 Central domains, 2,400
  mentions) in **21.33 ms**; 50-argument dense Dung AF exact CaDiCaL SAT evaluation in
  **0.30 ms**.

Earlier dated verification records (including the 2026-09-06 seven-technique baseline in
`specs/019-unified-machine-interfaces/tasks.md` and `specs/001-*`..`specs/021-*`) remain
preserved as historical feature evidence; see [`docs/README.md`](docs/README.md).

The nested `isanlp_rst.production` contract writes `3.0.0` and reads historical `2.0.0`
without rewriting its meaning. Machine record families (`rdam.aggregate`,
`rdam.capabilities`, `rdam.native_result`, `rdam.preparation`) write `2.0.0` while
retaining `1.0.0` read support through `rdam.historical`; use `rdam version` and
`rdam schema` for the installed contracts. Persisted `isanlp_rst` identifiers are retained
intentionally.

## Provenance and licence

This repository is Steve Allison's evolution of the IsaNLP RST Parser into the Rhetorical
Discourse Analysis Machine. The original RST research code and the archived research model
weights are by Elena Chistova; the MIT-licensed source carries her copyright. The machine,
every non-RST technique provider, `dclq` + DocLang single-stream ingest, `rdam.concepts`,
eRST workbench research, and the build and release tooling are Steve's own code.

- **Source code:** MIT — see [`LICENSE`](LICENSE). Copyright Elena Chistova 2020 for the
  original parser; Steve Allison's contributions also under MIT.
- **Production model weights** (`tchewik/isanlp_rst_v3` on HuggingFace, families `rstdt`,
  `gumrrg`, `rstreebank`, `rrtrrg`, `unirst`): **CC BY-NC 4.0 — research and
  non-commercial use only**, see [`LICENSE_MODELS`](LICENSE_MODELS). These models power
  `PredictorDMRST` and `PredictorUniRST` through `Parser`.
- **LLM-produced analyses:** governed by the configured third-party model provider's
  terms.
- **Workbench research experiments:** candidate architectures (e.g. ModernBERT, eRST)
  reside strictly under `workbench/` and are evaluated against baselines before any
  production use.

Issues: `Steve-Allison/Rhetorical_Discourse_Analysis_Machine`.

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

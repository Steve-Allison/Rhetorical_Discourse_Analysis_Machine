# Research and Decisions: Unified Machine Interfaces

**Date**: 2026-09-04

**Status**: Design decisions, not implemented behavior.

## Evidence baseline

Current checkout inspected at `e7deef4968e5b921c33caa8bd1723b58b65280cd` on `master`.
The preceding read-only audit ran the composition, source-entry, CLI-contract and
local-HTTP-contract suites: **18 passed in 4.38s**. Those existing tests are a
baseline, not proof of this design. `pixi run rdam-rst --help` listed `parse`,
`capabilities`, `serve`, `version`; `pyproject.toml` declares only that entry point.

| Verified source | Consequence for this design |
|---|---|
| `rdam/composition.py` | Seven lazy providers, but only a shared LLM model and execution policy are configurable through the factory. |
| `rdam/machine.py` | Generic orchestration already shares inventory/projections and preserves typed sibling failures; preparation is private and unexpected provider defects propagate. |
| `rdam/contracts.py` | Aggregates do not retain requested scope; retained upstream successes are outcomes too. Success lookup currently uses native technique, which differs from requested RST for eRST. |
| `rdam/rst/cli.py` | Both transports call RST ingest; source alternatives are prioritized rather than exclusive; errors can be written to the requested result file. |
| `rdam/rst/provider.py` | RST supports published/local models, inventory, device, eRST bundle and cache, but reconstructs the default policy and loses CLI evidence/refinement choices. |
| `rdam/dung/provider.py`, `rdam/dung/semantics.py` | Dung capacity changes the native algorithm record but is absent from the declaration used by the aggregate cache key. The native validator requires a nonempty argument list. |
| `rdam/ingest/contracts/source.py` | Raw byte identity differs from the metadata-bearing artifact identity; binary archives cannot safely use implicit UTF-8 JSON bytes. Shared path inference omits the CLI's `.txt` special case. |
| `rdam/ingest/contracts/preparation.py` | Full preparation evidence holds policies/warnings; the aggregate receipt drops them. Projection identity binds inventory and requirement, not every resulting projection value. |
| `rdam/_llm.py` | Existing explicit output/transport retries and deadline are owned by the LLM boundary; model identity and key presence can be checked without a client. |
| `rdam/serialization.py` | Existing canonical record persistence validates digest and rejects duplicate keys, but dispatches all three machine records using one shared version constant. |
| `tools/production_boundary/{schemas,public_surface}.py` | Generated schemas and public-surface metadata currently concentrate on ingest and the RST command. |

The main agent read all sources in the table in full. Two read-only research
agents also reviewed Python and transport design independently. Their proposals
were reconciled here, not treated as implementation proof. In particular,
preparation replay was considered but not added to the requested inspection
operation.

## D1 — One machine, not a new service layer

**Decision**: Keep `Machine`, `AggregateRequest`, native results and provider
boundaries. Add typed configuration, public `Machine.prepare`, request codecs,
shared completion/error/summary contracts and thin `rdam.cli`/`rdam.http` adapters.

**Rationale**: The current engine already owns orchestration. Adding a second
application service would create competing analysis ownership.

**Alternatives considered**: Renaming the old CLI alone leaves its RST-only
engine unchanged; a generic command per provider loses aggregate semantics.

## D2 — Configuration outside analysis requests

**Decision**: A strict immutable `MachineConfig` configures one machine. Explicit
file/Python values, narrow CLI overrides, existing model environment fallback,
and package defaults have a documented precedence. HTTP receives no configuration
mutation fields. Relative configuration paths resolve at load time.

**Rationale**: A model path or cache directory is local execution authority, not
source data an HTTP client may choose. Fully resolved settings are recorded with
the result, excluding credentials. Per-technique declarations bind their actual
settings to cache identity; unused provider changes do not invalidate another
provider's cache.

**Alternatives considered**: Configuration in every request invites repeated
model creation and remote filesystem access; an ambient multi-file search stack
makes commands difficult to reproduce. No profiles or config init command added.

## D3 — Explicit result scope and versioning

**Decision**: Write aggregate v2 with requested boundary outcomes separated from
retained upstream native results. Every success has an explicit boundary while
the embedded native result retains its own technique and formalism. Derive
`complete`, `partial`, `unsuccessful` from requested outcomes only.

**Rationale**: Persisted scope is required for truthful saved-result summaries.
Native eRST remains eRST; it is not relabelled to repair lookup. Outer
configuration evidence alone does not require rewriting native payloads; the
separately authorized integrity fixes in D12 do require versioned changes.

**Alternatives considered**: Inferring requested scope from lineage loses
unreferenced retained results; counting all native successes yields false
partial success. Historical v1 data stays readable with unknown request scope,
not silently converted into a supposedly known v2 execution.

## D4 — Preparation is complete inspection, not promised replay

**Decision**: A model-free preparation result retains the existing complete
semantic preparation evidence, plus unique selected projections and explicit
technique bindings. No projection selection means inventory/default preparation
only. Analysis uses this same internal operation once per invocation.

**Rationale**: The existing receipt alone omits policies and warnings. Persisted
inspection is useful without introducing a trust-sensitive prepared-input replay
protocol. A later `analyse` of raw input prepares again; this is documented, not
hidden behind a cache claim. Provider declarations may require local metadata
checks, but never weight loading or network access.

**Alternatives considered**: Accepting a receipt as trusted input permits stale
or altered projections; a replay feature would require additional requirements
and validation not requested here.

## D5 — Strict shared requests and literal source acquisition

**Decision**: Serialize the same `AggregateRequest` used in Python. Add explicit
contract/version and codecs with annotated binary encoding, not a second
hand-maintained transport DTO. CLI convenience arguments construct this request;
`--request` consumes the complete form without merging convenience arguments.
Add `for_edus` and `for_structured` constructors alongside existing constructors.

**Rationale**: A single typed representation provides parity while direct flags
keep common workflows short. Metadata is preserved; submitted provenance never
causes HTTP filesystem/network access. Structural-only identity binds the exact
canonical structure bundle, or reuses an explicitly supplied upstream source.

**Alternatives considered**: JSON text wrapped inside JSON loses schema clarity;
blindly flattening all inputs to text loses native source/EDU identity.

## D6 — Canonical output, useful errors and safe files

**Decision**: JSON machine commands emit one canonical record plus one LF;
`summary` is a separate plain-text command. Default stderr is line-delimited
safe JSON diagnostics; explicit `--diagnostics text` renders the same errors
readably. Help alone is plain text. No interactive prompts or TTY-dependent data.
Output files are no-clobber unless `--force`, written through an atomic sibling
temporary; errors never replace the output with a diagnostic.

**Rationale**: Shell and agent consumers can parse both channels predictably.
Complete aggregates are retained even with nonzero analytical exit codes.
An output path must not alias source/config/request/structure/upstream inputs,
even under `--force`.

**Alternatives considered**: `analyse --format summary` silently discards full
evidence; always overwriting follows neither the user's data-safety rules nor
reproducible scripting needs.

## D7 — Optional maintained local HTTP transport

**Decision**: Add `rdam[http]` using Starlette `>=1.6,<1.7` and Uvicorn
`>=0.52.4,<0.53`, with one process, asyncio/h11, no reload/proxy/CORS/WebSocket
features. Use raw-byte responses from the shared serializer. Synchronous machine
work runs off the event loop; one analysis/preparation admission slot is shared.

**Rationale**: Python's own documentation warns that `http.server` provides only
basic checks and is not recommended for production. A maintained parser is
proportionate for a local API; protocol handling need not become RDAM analysis
code. Python and CLI remain usable without the optional dependency chain.
See [Python HTTP documentation](https://docs.python.org/3.14/library/http.server.html).

Starlette supports shared lifespan state and passing response bytes unchanged;
its threadpool support keeps blocking work off the event loop.
See [Starlette responses](https://github.com/kludex/starlette/blob/main/docs/responses.md)
and [threadpool documentation](https://github.com/kludex/starlette/blob/main/docs/threadpool.md).
Uvicorn exposes programmatic configuration for protocol, host, concurrency and
logging; its proxy handling must be explicitly disabled here.
See [Uvicorn settings](https://github.com/kludex/uvicorn/blob/main/docs/settings.md).

**Alternatives considered**: Extending `BaseHTTPRequestHandler` would make us
maintain framing/admission/error machinery. FastAPI adds another validation/API
schema surface when RDAM already has the authoritative models and serializer.

## D8 — HTTP transport success is not analytical success

**Decision**: A valid aggregate is HTTP 200 whether complete, partial or
unsuccessful. Application errors use typed canonical records and appropriate
4xx/5xx status. Parser-level invalid HTTP or a connection already lost cannot
promise a JSON error; document those boundaries explicitly.

**Rationale**: HTTP reports whether the requested representation was produced;
the aggregate reports analytical outcomes. No WebDAV 207 or renamed provider
failure pretending to be a transport exception.
See [RFC 9110](https://www.rfc-editor.org/rfc/rfc9110.html).

**Alternatives considered**: Returning 500 for every unsuccessful aggregate
encourages invalid retries and loses the distinction between results and bugs.

## D9 — Preserve existing explicit retries, add none in adapters

**Decision**: Expose the existing bounded LLM output retry, transport retry and
deadline settings in typed configuration. Preserve their distinct meanings and
attempt evidence. Machine, CLI and HTTP never add another retry loop. No hard
thread-cancellation deadline is promised for local RST inference.

**Rationale**: A provider's retry contract already exists; changing it to zero
would alter analysis behavior. Conversely, calling an adapter twice can incur
additional paid work and must not occur invisibly.

## D10 — Prove equivalent requests, not erased differences

**Decision**: Exact transport parity reuses the same materialized request,
configuration and external response fixture. Native declared execution fields
are the only allowed exclusions for analytical comparison. File-versus-stdin
tests separately verify content and provenance expectations.

**Rationale**: Different origins really are different provenance. Live model
sampling is not made deterministic by canonical JSON. Existing internal service
doubles are not sufficient new parity evidence.

**Alternatives considered**: Removing all differing keys or comparing only
counts can conceal lost native evidence and configuration drift.

## D11 — AI-ready by default, without a second analytical formalism

**Decision**: Embed a versioned native reading guide in aggregate v2. Add a pure
whole-technique selection view for saved v2 analyses, identically available via
Python, CLI and HTTP. Presentation retains native records unchanged; producing
providers implement the versioned integrity corrections in D12 first.
No generic claim graph, generative explanation, synthesized confidence or ranked
context packing is introduced.

**Rationale**: The owner explicitly requires immediate AI use. Syntax/schema
alone cannot explain epistemic limits. Native contracts show important traps:
Toulmin's warrant explicitness is not assessed; its qualification count means a
qualifier or rebuttal is present. Walton defaults omitted critical questions to
open. PDTB inferred connectives are not quoted spans. Literal alignment searches
all strings, including labels, so a match alone is not an asserted proposition.
The main agent read `rdam/toulmin/argument.py`, `rdam/walton/schemes.py`,
`rdam/pdtb/relations.py`, `rdam/sdrt/graph.py`, `rdam/ibis/grammar.py`,
`rdam/ingest/alignment.py` and `rdam/ingest/contracts/inference.py` in full to
reconcile the additional native-contract research with the design.

**Alternatives considered**: An LLM-written summary would add cost and inference;
rewriting all outputs into claim/evidence objects would destroy formalism
distinctions. Per-field heuristic epistemic labels would overclaim what the
native validators establish. Whole-technique selection is deliberately explicit;
it cannot promise every analysis fits every model's context window.

## D12 — Fix native integrity rather than preserve known weaknesses

**Decision**: Following the owner's explicit instruction, require complete Walton
assessment coverage with a distinct not_assessable state, source-backed Toulmin
warrant origin, accurately named qualification counts and provider-selected typed
source alignment. Details and regression cases are authoritative in
[contracts/native-integrity.md](contracts/native-integrity.md).

**Rationale**: The observed default-open behavior turns missing output into a
finding; absent warrant-origin fields impede safe use; recursive string matching
does not distinguish analytical metadata from evidence. These are repairable
contract weaknesses, not inherent limits to defend in documentation.

**Version decision**: Native envelope v2, Toulmin/Walton/PDTB/SDRT provider contract
v2 where evidence semantics change, and explicit historical v1 readers. Preserve
Walton's scheme catalogue identity and RST/Dung/IBIS payload versions where their
native semantics are unchanged. Bind schema/evidence policy and envelope version
to cache identity; retain but never silently reuse incompatible old cache entries.

**Alternatives rejected**: A warning-only wrapper; treating every missing answer
as open; forcing every warrant into an unjustified origin class; silently
upgrading historical JSON. None establishes the required truth.

## D13 — Tests and cold critique, without evaluation machinery

**Owner correction (2026-09-04)**: “If something needs testing launch a cold-critic
agent. DO NOT INVENT COMPLEXITY just to look clever!”

**Decision**: Remove the owner-annotation gate, reference lifecycle, custom scorer,
coverage quotas and bulk three-run evaluation schedule. Use existing native
regression suites, real-provider parity, focused real-model semantic cases and a
fresh cold critic. Fix concrete findings and rerun affected tests.

**Rationale**: These checks directly test the requested API/CLI and native repairs.
The discarded evaluation system delayed implementation and created maintenance
work unrelated to a solo-local interface. Quotation validity still does not
establish relevant support, so retain those semantic negative cases as tests.

**Cold-critic finding**: Independent inspection confirmed that the test-only
review-state, manifest, scoring and interval machinery was unnecessary. Keep
NI-01–NI-04 tests, transport safety/parity, actual source/output review and the
existing installed-wheel checks. No new runner or approval schema is needed.

## Currency and remaining implementation checks

PyPI metadata queried on 2026-09-04 reports Starlette **1.6.0**, Uvicorn **0.52.4**,
Docling Core **2.94.1** and DocLang **0.7.3**. The latter two match the lower bounds
in the inspected `pyproject.toml`; this is a metadata observation, not upstream
format conformance proof. Sources: [Starlette metadata](https://pypi.org/pypi/starlette/json),
[Uvicorn metadata](https://pypi.org/pypi/uvicorn/json),
[Docling Core metadata](https://pypi.org/pypi/docling-core/json),
[DocLang metadata](https://pypi.org/pypi/doclang/json).

No format schemas/harvesting rules are redefined by this planning package.
Before implementation edits to source/format contract files, recheck the current
Docling/DocLang specs, pins, lock and fixture conformance under AGENTS.md; capture
actual results in the implementation verification report. Resolve and test the
optional HTTP dependencies through Pixi before treating the chosen ranges as an
installed Python 3.14 compatibility result. No such installation is claimed here.

## Clarification coverage

All ten Spec Kit ambiguity categories have explicit requirements or design
decisions. No critical product question remains. Technical choices above are
recommendations executed within the owner-approved planning phase, not new
owner rulings about trained algorithms, release destinations or deployments.

## Implementation preflight — 2026-09-04 (T002)

Live PyPI metadata was checked again during implementation: Docling Core 2.94.1
and DocLang 0.7.3 match the installed distributions and parsed lock entries.
The complete pyproject.toml declares `docling-core>=2.94.1,<2.95` and
`doclang[schematron-saxon]>=0.7.3,<0.8`. Package agreement alone is not full upstream
contract conformance.

The current [DocLang spec at the inspected revision](https://github.com/doclang-project/doclang/blob/6d3b3d3c195d1f63333c5c5fcba8da17937a33bd/spec.md)
was read in full. All 42 local valid and 59 invalid DocLang fixture filenames and
Git blob identities matched that upstream revision. This was a mechanical byte
comparison, not a claim that each fixture was manually read. The parity and
conformance test files were read in full, then executed:

```sh
pixi run pytest tests/ingest/test_doclang_fixture_parity.py tests/ingest/production_ingest/test_upstream_conformance.py -q
```

Observed: `149 passed in 4.33s`, exit 0. These include installed-library loading
and traversal checks for the four Docling fixtures, not exhaustive proof of the
current upstream Docling contract.

The current [Docling document implementation](https://github.com/docling-project/docling-core/blob/a59c38c1da0d3e43bdcfb93ef074f4e269093a1f/docling_core/types/doc/document.py)
differs byte-for-byte from the installed implementation. The initial partial read
was completed through EOF before concluding this preflight. Its current
content_layer.py and constants.py were also read in full. AST comparison found
identical upstream/installed function bodies for `load_from_json`,
`check_version_is_compatible`, `iterate_items` and `_iterate_items_with_stack`.
This comparison does not claim every unrelated upstream change is harmless.

Observed schema acceptance: 1.9.0 and 1.10.0 accepted and normalized to current
1.10.0; 1.11.0 and 2.0.0 rejected. Current content layers are body, furniture,
background, invisible and notes; the default layer set is body only. Explicit
all-layer, group-inclusive, picture-traversing loading of the four local fixtures
reported Markdown 63, PDF 767, PPTX 43 and VTT 38 items. All stored and loaded
fixture versions were 1.10.0. Diagnostic exited 0. Loading success and these
counts are sample-scoped, not proof that every possible document is supported.

Corrected the stale `isanlp_rst.ingest` reference in the fully read fixture README
to `rdam.ingest`, separated its historical observations from the current loading
check and removed the unsupported assertion of verified public availability.
No format production behavior, dependency pin, lock, fixture bytes or RDAM
envelope version was changed by this preflight.

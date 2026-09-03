# Handoff: universal source ingest, and the two remaining techniques

**Written**: 2026-09-02, end of a long session. Resume from here after `/clear`.

## Where the machine actually is

`pixi run test` → **1043 passed**, 134 deselected. Lint, pyright strict, mdlint, and
`production-boundary` (`valid: true`, 131 production modules) all green. Nothing is
committed — the entire session's work is in the working tree.

```text
rst       available   rdam.rst/gumrrg
dung      available   rdam.dung/exhaustive-subset-v1
ibis      available   rdam.ibis/gibis-grammar-v1
toulmin   available   rdam.toulmin/layout-v1/openai:gpt-5.6-sol
walton    available   rdam.walton/schemes-v1/openai:gpt-5.6-sol
sdrt      unavailable(not_implemented)
pdtb      unavailable(not_implemented)
```

**5 of 7.** SC-012 requires 7, so 006 is still not met.

## What changed this session

### 1. The promotion-evidence gate is gone (owner ruling)

It was never requested and it made working parsers report `unavailable`. Deleted:
`rdam/promotion.py`, both packaged `promotion-decision.json` resources,
`workbench/promotion/{decision,modernbert}.py`, `workbench/promotions/`,
`specs/008-promotion-system/`, `contracts/promotion-evidence.md`, and the promotion tests.

`UnavailableReason` is now three values, all meaning *can it run*: `not_implemented`,
`missing_structured_input`, `model_unavailable`. `ProviderProvenance.licence_decision`
became `licence`.

**Kept deliberately** — three different things share the name "promotion":

- `workbench/promotion/promote.py`, `PromotionReceipt` — copying a model into the
  immutable store.
- `workbench/promotion/compatibility.py`, `CompatibilityRedeclaration` — the loader reads
  those sidecars.
- `tools/production_ingest/*` — the Gold Set gate from spec 002, a separate concept.

Specs 002–005 keep their original wording as dated history; the affected rows in dated
evidence files are struck with a note rather than erased.

### 2. 006 was rewritten so it cannot pass without all seven techniques

As written, every success criterion was satisfiable with four techniques absent — Scope
Boundaries excluded the providers, FR-018 let PDTB and SDRT sit in the workbench
indefinitely, and the priority assumption made PDTB conditional on "a concrete need".
*Not building them scored as a pass.* Now:

- **FR-031** — all seven must have a provider; `unavailable(not_implemented)` is
  outstanding work, never an acceptable end state.
- **FR-032** — Toulmin, Walton and SDRT are expected to need LLM inference, and an
  LLM-backed provider is a required provider on the same footing as a deterministic one.
- **SC-012** — `capabilities()` must report 7/7, "however green every other gate is".

### 3. The LLM boundary

`rdam/_llm.py` — one shared boundary, justified under FR-029 (four callers, one contract,
unambiguous ownership). Pydantic AI, model-agnostic via a model string.

- Model: **`gpt-5.6-sol`** (`DEFAULT_MODEL = "openai:gpt-5.6-sol"`), owner's choice,
  confirmed to exist on the account by listing the API's models. Override with
  `RDAM_LLM_MODEL`.
- Keys come from `.env` at the repo root (git-ignored, verified). An explicit environment
  variable always wins over the file.
- **The model proposes; the formalism disposes.** Nothing repairs a malformed proposal.
- Two retry classes kept separate per the 006 capability contract: output-validation
  retries (Pydantic AI carries the validation error back) and transport retries.
- 30 tests, no network — `FunctionModel` plus `ALLOW_MODEL_REQUESTS = False`.

### 4. Two techniques built

| | module | tests |
|---|---|---|
| **Toulmin** | `rdam/toulmin/argument.py` — six elements; the warrant is mandatory and may not restate the claim or a ground, which is FR-019 enforced in the type | 24 |
| **Walton** | `rdam/walton/schemes.py` — 12 schemes with premise roles and Walton's critical questions; instances must fill exactly their scheme's roles; open questions are reported, never answered | 90 |

Both prompts are generated from the formalism, so prompt and validator cannot drift.
`pydantic-ai` and `openai` are now declared production dependencies in
`tools/production_boundary/authority.py`.

## Next: feature 013 — universal source ingest

**Owner ruling, 2026-09-02**: ingest and source content prep are universal. Everything
gets the same source input. `rdam.rst.ingest` **moves to `rdam.ingest`**.

Today the machine is text-only: `AggregateRequest.for_text()` takes a bare `str`, RST's
provider re-enters its own ingest via `SourceArtifact.from_text()`, and the other
providers get the raw string. **A `report.md` cannot reach the machine at all** — the
governed pipeline (Markdown, Docling JSON, DocLang, anchors, `AUTHORED_PROSE_V1`,
subdivision, receipts) is unreachable through `Machine`.

Scale, measured: **25 modules, 10,477 lines, 107 code files and 27 documents referencing
`rst.ingest`.** This is a feature, not an edit.

Scope:

1. Move `rdam/rst/ingest/` → `rdam/ingest/`. `rdam.rst.ingest` becomes a re-export so the
   documented RST public surface is preserved; `pixi run rst-baseline compare` must give
   zero analytical differences.
2. `AggregateRequest.for_source(path)` — ingest runs **once** per aggregate, and every
   provider receives the same prepared prose and anchors.
3. Persist the ingest receipt on the aggregate so every technique's result traces to the
   same preparation.
4. Do **not** change the persisted contract id `isanlp_rst.production` 2.0.0 without a
   separate owner ruling.

Then, in the same or a following feature:

- **Cache the LLM boundary** on (source digest, model, instructions digest, contract
  version). There is no cache today; every `analyse()` is a fresh paid call.
- **Run independent providers concurrently.** `Machine.analyse()` is a sequential
  `for technique in request.techniques:` loop; with four LLM providers that is four serial
  round trips for work that is isolated by contract (FR-014).

Cross-technique flow stays **declared, never inferred** — FR-015 is deliberate and should
not be automated.

## Then: SDRT and PDTB

Build after 013 so they consume prepared source from the start rather than being
retrofitted.

| | native structure | notes |
|---|---|---|
| **SDRT** | SDRS: discourse units, coordinating vs subordinating relations, the right-frontier constraint | multi-party dialogue is SDRT's native object |
| **PDTB** | explicit/implicit relations, connective, Arg1/Arg2, the three-level sense hierarchy | sense hierarchy enforced by the validator |

Each needs its own decision-closed feature first (FR-024).

## Standing constraints

pixi only, never `pip`/`conda`/`poetry`/bare `pytest`. **Never suppress a checker** — no
`type: ignore`, `noqa`, `pyright: ignore`, or blanket `except`; make the statement true
instead (this was breached twice this session and both were fixed properly). Commit only
when asked; never push unless asked. Tag `v5.0.0` is published and must never move. No
invented ceremony. Read whole files. Ask in prose, never the question UI. One person, one
machine — never team or enterprise scale.

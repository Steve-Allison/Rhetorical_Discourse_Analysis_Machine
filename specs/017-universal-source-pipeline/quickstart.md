# Quickstart: Validating the Universal Source Pipeline

**Feature**: 017 | **Date**: 2026-09-03

Every success criterion with the check that demonstrates it. Each scenario runs on its own.
Shapes and rules live in [data-model.md](data-model.md) and [contracts/](contracts/); this
is the run guide.

## Prerequisites

```bash
pixi install
```

A local model release (`models/model-releases/`) or the published `gumrrg` version for the
RST scenarios, and an API key in `.env` for the model-backed ones. Scenarios needing neither
are marked.

Two fixtures this feature adds, because two of its correctness claims cannot be tested
without them:

- a document whose only quantitative evidence is a **table** — for SC-004;
- a **multi-party transcript**, including turns that are deliberately unattributable — for
  SC-007 and SC-008.

## Historical baseline

The pre-change baseline is already captured in `evidence/baseline-dmrst-current/`;
its commands and measurements are recorded in [evidence/baseline.md](evidence/baseline.md).
Do not overwrite it with a post-change capture. SC-010 below compares the current
implementation with that historical evidence using the same immutable parser release.

## SC-001 — Every available source form is analysable

```bash
pixi run python -c "
from rdam.ingest import describe_capabilities
print([(f.source_form.value, f.availability.value) for f in describe_capabilities().semantic.source_forms])
"
pixi run pytest tests/machine/test_all_source_forms.py -q
```

Then analyse a fixture of each reported form. **Expected**: every available form analyses;
five of six were unreachable before. A form whose optional dependency is absent fails typed
and staged, never partially.

## SC-002, SC-003 — Inventory once, projections shared

No model needed.

```bash
pixi run pytest tests/machine -k "inventory or projection" -q
```

**Expected**: inventory and disposition execute exactly once for aggregates naming one
through seven techniques; two providers declaring identical requirements receive the same
projection object, computed once.

## SC-004 — Each technique sees what it can analyse

The claim that justifies this feature being more than a relocation.

```bash
pixi run pytest tests/ingest -k "projection_admits" -q
pixi run pytest tests/toulmin -k "table" -q
pixi run pytest tests/rst/test_provider.py -k "projection_excludes_tables" -q
```

**Expected**: for the tabular-evidence fixture, Toulmin's grounds are present and each
anchors to a `TableCoordinateAnchor` naming the cell it came from; RST's projection does not
admit the table. Before this feature Toulmin receives no table at all, and its contract
requires at least one ground — so the pre-feature behaviour is a confabulated ground, which
is exactly what this check exists to prevent.

## SC-005, SC-006 — Projections are exact and derived

```bash
pixi run pytest tests/ingest -k "reconstruct or transformation" -q
```

**Expected**: across all six source forms, every projection's segments concatenate to its
prepared text exactly and each names its contributing items and anchors; every unit of
content admitted by transformation names the `TransformationRecord` that produced it. **Zero
admitted content without a derivation.**

## SC-007, SC-008 — Speakers are resolved or declared absent, never invented

```bash
pixi run pytest tests/ingest -k "speaker" -q
pixi run pytest tests/sdrt -k "speaker" -q
```

**Expected**: every turn carries `resolved` with a participant id, or `unresolved` with
evidence saying why; the receipt's `SpeakerCoverage` reconciles exactly
(`resolved + unresolved == turns`). On the deliberately unattributable turns: **zero invented
speakers**. A provider declaring `requires_speaker_identity` is told, rather than silently
receiving anonymous turns.

## SC-009 — Planning is per requirement

```bash
pixi run pytest tests/ingest -k "capacity" -q
```

**Expected**: two providers declaring different capacity units over one source each receive
a plan valid for their own capacity, from the one inventory.

## SC-010 — RST preservation with independently verified correctness repairs

The gate for the whole relocation, and for the projection model being behaviour-preserving.

```bash
pixi run rst-baseline compare \
  --baseline specs/017-universal-source-pipeline/evidence/baseline-dmrst-current \
  --store "$HOME/.cache/isanlp_rst/model-releases" \
  --release-id gumrrg-eb1d5745f3a1 --device cpu
```

**Expected**: exit 0, `no_unexplained_regressions: true`, and no unexplained analytical
differences. The owner-approved source-ID and DocLang table corrections are reported
separately as `source_identity_correction` and `doclang_table_correction`. They change
the records, so `equivalent` and `analytically_equivalent` remain `false`. The original
baseline is never overwritten. Execution, package identities, derived digests and the
earlier approved capacity-field rename remain separately classified.

Verify that the checker rejects deliberate corruption, including unchanged historical
bugs and a stale digest that conceals changed contents:

```bash
pixi run --locked pytest tests/production_boundary/test_baseline_corrections.py \
  tests/production_boundary/test_rst_baseline.py -q
```

## SC-011, SC-012 — The cache answers only when it should

```bash
pixi run pytest tests/llm -k "cache" -q
```

**Expected**: an identical repeat against a configured cache performs **zero** model
requests and returns a semantically identical result; one demonstrated miss per element of
the analytical identity — source, projection, provider id, contract version, model identity,
instructions identity; a corrupt or contract-stale entry re-analyses; with no cache
configured, nothing is written. These run against a Pydantic AI `FunctionModel` with
`ALLOW_MODEL_REQUESTS = False`, so "zero model requests" is enforced by the harness rather
than trusted.

## SC-013, SC-014 — Concurrency is faster and identical

```bash
pixi run pytest tests/machine -k "concurren" -q
pixi run pytest tests/stress -m stress -k "real_parser or real_provider" -q
```

**Expected**: concurrent and sequential aggregates over one request have **identical
semantic digests**; four model-backed techniques complete in materially less wall-clock time
than the sum of the four individually; a concurrent failure does not disturb a concurrent
success. The stress test establishes whether the real parser is safe in parallel — if it is
not, the RST provider is serialised and that decision is recorded with the measurement that
forced it.

## SC-015 — Two techniques, one span

Two native findings sharing source coordinates.

```bash
pixi run pytest tests/machine -k "alignment" -q
```

**Expected**: findings from two techniques over one source are reported against one source
span, by shared anchor — without their formalisms being merged into a common vocabulary.

## SC-018 — The persisted contract identifiers did not move

The relocation's silent-failure mode. `rst-baseline compare` classifies *analytical*
difference and would not catch an identifier drifting.

```bash
pixi run pytest tests/ingest -k "persisted_identifiers" -q
```

**Expected**: `isanlp_rst.production` is still 2.0.0, every schema `$id` is byte-identical
to its recorded value, and every runtime contract name is unchanged. These name stored
contracts, not module paths, and the module path is exactly what this feature changes.

## SC-019 — The inventory is still complete

```bash
pixi run pytest tests/ingest -k "inventory_completeness" -q
```

**Expected**: across all six source forms, every item is classified, dispositioned and
accounted, with **zero valid content discarded**. This is the existing guarantee; relocation
plus per-requirement projection is exactly what could erode it.

## SC-020 — Parallel safety is declared, and nothing is retained

```bash
pixi run pytest tests/machine -k "provider_lock_lifetime or parallel_safety" -q
```

**Expected**: every provider declares its parallel safety; no provider is serialised without
a declaration; a provider declaring itself safe is not locked; and a provider is not
retained after collection — including one that cannot be weak-referenced, which the current
registry would otherwise hold for the life of the process.

## SC-016, SC-017 — Nothing regressed, nothing suppressed

```bash
pixi run lint
pixi run typecheck
pixi run test
pixi run mdlint
pixi run -e default production-boundary
pixi run ontology-validate
```

Because the relocation and the concurrency work touch the predictor stack:

```bash
pixi run test-all
pixi run smoke
```

**Expected**: all green; all seven techniques still `available`; and no suppression
anywhere:

```bash
grep -rn "type: ignore\|pyright: ignore\|noqa" rdam tests tools    # expect: no matches
```

## End to end: a real tabular document

```bash
pixi run python -c "
from pathlib import Path
from rdam import AggregateRequest, Technique, production_machine

machine = production_machine()
aggregate = machine.analyse(
    AggregateRequest.for_source(
        Path('tests/fixtures/pipeline/tabular-evidence.md'),
        (Technique.RST, Technique.TOULMIN, Technique.WALTON),
    )
)
print('preparation receipts:', 1 if aggregate.preparation else 0)
print('distinct projections:', len(aggregate.preparation.projections) if aggregate.preparation else 0)
for outcome in aggregate.outcomes:
    print(' ', type(outcome).__name__)
"
```

**Expected**: one inventory and one receipt shared by all three techniques, the distinct
projections they required, and one explicit outcome each — from a Markdown file the machine
previously could not accept at all.

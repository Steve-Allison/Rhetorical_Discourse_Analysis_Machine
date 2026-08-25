# Contract: Gold Set and Promotion Evidence

## Purpose and boundary

This contract proves that production source ingest is correct, relevant,
structure-aware, deterministic, and measurably no worse for RST analysis. It is
release evidence, not a runtime feature and not training content.

The production wheel executes each source and emits strict serialized results.
Repository-only tooling then compares those outputs with frozen expectations and
uses `offline_workbench.evaluation.rst` for canonical RST metrics. Production
code never imports the assessor, scorer, Gold Set, corpus, or labels.

## Gold Set authority

- Private or non-redistributable content lives outside the repository at an
  explicit absolute `--gold-root` path.
- Redistributable normative fixtures may live under `tests/fixtures` with their
  licences and provenance.
- The repository stores only text-free manifests, hashes, adjudication metadata,
  and results that do not disclose protected source content.
- The candidate cannot modify the frozen Gold Set or expectations.
- A freeze record contains the manifest digest, expectation digest, adjudicator,
  date, and tool/schema versions before the candidate run begins.

## Minimum composition

The frozen set contains at least 20 sources and all five production source
families: plain text/presegmented EDUs, Markdown, Docling JSON, and DocLang XML
or archive. At least 12 sources have adjudicated EDU segmentation and primary
RST structure.

Across the set, the manifest must cover:

- clean short prose;
- long and deeply structured documents;
- at least one source of one million or more characters;
- headings, lists, dialogue/turns, slides/pages, and nested groups;
- tables, code, formulas, raw HTML, scripts/styles/navigation;
- notes, furniture/background/invisible content, picture descriptions;
- exact repeated content and conversion-artifact duplicates;
- Unicode normalization and offset-sensitive text;
- current valid Docling and DocLang normative specimens;
- empty primary discourse and unknown-but-valid content;
- malformed contracts, unresolved references, and unsafe `.dclx` archives;
- cache hit, cache miss, changed validator/policy/model identity, and corruption.

The set contains at least two examples each of long structured prose,
presentations with notes, OCR-heavy material, multi-speaker discourse,
code/raw-markup-rich Markdown, rich or nested tables, repeated content, and
Unicode/coordinate stress. One source may satisfy multiple risk classes, but
its evidence must remain independently inspectable for each class.

Real-world untouched sources are the primary evidence. Normative upstream
specimens prove contract conformance. Synthetic sources are permitted only for
precise adversarial invariants that cannot be safely obtained otherwise; they
do not replace real coverage.

## Required expectations per source

Every source has human-verified expectations for:

- immutable source identity and provenance class;
- complete content inventory and hierarchy;
- exactly-one disposition for each inventory item;
- primary/side-channel/excluded relevance decisions;
- prepared text or digest-safe interval expectations;
- structure/subdivision expectations;
- duplicate findings and actions;
- source/prepared/analysis coverage;
- representative round-trip anchors, including every anchor type exercised;
- expected success or stable typed failure.

The 12 or more RST-gold sources additionally contain adjudicated EDU boundaries
and primary RST tree annotations under one frozen evaluation convention.

## Candidate identity and run conditions

Baseline and candidate records freeze:

- Git commit and dirty-state proof;
- built wheel digest and installed package inventory;
- exact released-model manifest and file digests;
- Python/Pixi lock and relevant dependency versions;
- policy, adapter, preparation, subdivision, and result-schema digests;
- machine/OS identity and resource conditions;
- Gold Set and expectation digests.

Baseline and candidate use identical model bytes, Gold Set, scorer,
configuration, and machine. No training, fine-tuning, model selection, annotation
repair, manual source cleanup, network access, or per-document exceptions are
permitted after freeze.

## Ordered promotion gates

A later gate cannot hide an earlier failure. Results are reported per source
before any aggregate.

### Gate 1 — Source-contract validity

- 100% of valid sources are accepted.
- 100% of invalid/unsafe sources fail at the expected stage and stable code.
- Current unmodified Docling and DocLang normative specimens pass.
- Raw and accepted contract identities are correct.

### Gate 2 — Inventory and relevance

- 100% validated inventory reconciliation.
- 100% exactly-one disposition coverage.
- 100% agreement with human relevance decisions.
- No code, formula, raw-markup artifact, navigation, machine picture
  description, furniture/background/invisible content, or notes enter default
  primary discourse unless the frozen expectation explicitly establishes that
  it is authored discourse under the named policy.

### Gate 3 — Mapping, provenance, and anchors

- 100% source and prepared-text coverage.
- 100% final EDU/relation/node anchor coverage.
- Every sampled source-to-prepared-to-analysis and reverse traversal resolves to
  the exact expected source interval/item.
- Synthetic text never claims a source interval.
- No unresolved, overlapping, duplicated, or fabricated mapping passes.

### Gate 4 — Structure and RST quality

Using the frozen canonical offline scorer:

- segmentation precision, recall, and F1 do not decrease for any source form;
- Standard Parseval Span, Nuclearity, Relation, and Full do not decrease for any
  source form;
- no per-source quality regression is hidden by an aggregate;
- the candidate introduces zero new source-anchor or structural-boundary
  violations;
- structure-boundary violations decrease by at least 50% against baseline;
- every long source yields one coherent, complete tree.

The scorer identity and relation/nuclearity configuration are frozen before
candidate results. There are no metric waivers or post-result configuration
changes.

### Gate 5 — Determinism and cache correctness

- Ten repeated cached and uncached runs for every representative path have
  identical semantic results and semantic receipts.
- Cache identity changes for source, contract, validator, adapter, policy,
  preparation, subdivision, model, or result-schema changes.
- Valid hits are verified; corruption and contradictory identity fail visibly.
- A parser lacking an immutable model identity disables durable caching.

### Gate 6 — Performance at excellence scale

On the frozen local machine and released model:

- preparation adds no more than the specification's allowed overhead to
  representative sources;
- valid cache-hit latency satisfies the specification threshold;
- the one-million-character source completes within the specification's time
  and peak-memory bounds;
- evidence reports stage timing, peak RSS, prepared size, unit count, and cache
  state truthfully.

These are solo/local excellence bounds, not throughput, concurrency, service
availability, or enterprise-scale targets.

### Gate 7 — Installed-wheel production boundary

From a clean temporary directory and environment containing only the built
production wheel, its declared production dependencies, and released model:

- all production source forms run without the repository on `sys.path`;
- no training, corpus, Gold Set, scorer, benchmark, or `offline_workbench`
  module is installed or importable through the ingest path;
- no network is used;
- persisted results validate and can subsequently be scored by the separate
  repository assessor.

### Gate 8 — Direct inspection and SOTA comparison

The operator directly inspects every source result—not only aggregates—and
records pass/fail plus any anomaly. A dated matrix compares the implemented
capabilities with current primary-source practice for validation, authored
content selection, structural subdivision, provenance, loss accounting,
determinism/cache identity, and RST evaluation.

## Decision rule

Promotion passes only when every required source and every ordered gate passes.
The decision schema contains no waiver, expected failure, aggregate override,
or "acceptable regression" field. A failure creates evidence for another
candidate; it does not mutate the frozen benchmark.

Only after a complete pass may the project claim state-of-the-art production
source ingest for this small-volume RST/eRST use case, bounded to the comparison
date and measured capabilities. It may not claim model SOTA, universal document
conversion, enterprise throughput, or unmeasured superiority.

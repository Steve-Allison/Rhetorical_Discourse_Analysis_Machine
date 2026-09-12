# Research and decisions: DocLang decoder

Date: 2026-09-12. Observations apply to RDAM `74f7f3a11183abcd707bf7021a9604b966c1160f` unless stated otherwise. The user approved full implementation; shared-ingest ownership was clarified during execution.

## R1 — Native document ownership rather than a new dependency

**Observed:** `docling-nlp` commit `7a4b20a1f4ecf38fa3f8bfb9ca192fd645485cb3` separates a DCLG XML object from its archive layer. Its document object owns raw bytes and a tree and offers content/path operations. Its reader feeds that object directly.

Sources read in full:

- [dclg_document.h](https://github.com/docling-project/docling-nlp/blob/7a4b20a1f4ecf38fa3f8bfb9ca192fd645485cb3/src/andromeda/tooling/doclang/dclg_document.h)
- [content.h](https://github.com/docling-project/docling-nlp/blob/7a4b20a1f4ecf38fa3f8bfb9ca192fd645485cb3/src/andromeda/tooling/doclang/content.h)
- [reader.h](https://github.com/docling-project/docling-nlp/blob/7a4b20a1f4ecf38fa3f8bfb9ca192fd645485cb3/src/andromeda/tooling/doclang/reader.h)

**Decision:** implement the useful separation privately in Python using existing dependencies. Keep request-local ownership, use composition for archive facts, and expose only immutable current RDAM contracts downstream.

**Rationale:** no C++ bindings or NLP runtime is necessary for XML/ZIP ingestion. A new abstract document framework would add scope without serving another proven caller.

**Alternatives:** importing `docling-nlp` adds an unnecessary runtime and different validation semantics; copying its inheritance hierarchy adds mutable public API concerns. Neither is selected.

## R2 — One RDAM parse, official validation retained

**Observed:** `rdam/rst/doclang/loader.py:149` (baseline path) parses the main document for archive checks, then `rdam/ingest/_harvest.py:300` validates through a temporary path and parses again for harvesting. The complete files were read.

The upstream public validator accepts `str | Path`, returns no document tree and invokes independent validation engines. Complete source files read by the research agent:

- [validation.py](https://github.com/doclang-project/doclang/blob/663e9f59a5bb0e7e5c5be962fd942a4b3976c171/doclang/validation.py)
- [xsd_validation.py](https://github.com/doclang-project/doclang/blob/663e9f59a5bb0e7e5c5be962fd942a4b3976c171/doclang/xsd_validation.py)
- [schematron.py](https://github.com/doclang-project/doclang/blob/663e9f59a5bb0e7e5c5be962fd942a4b3976c171/doclang/schematron.py)

Context7 resolution/query corroborated the public path-based API.

**Decision:** retain official XSD and Schematron validation and the temporary-file bridge for materialized source bytes. Reuse one RDAM-owned root and path index for package reference checks and decoding.

**Rationale:** fewer RDAM parses is achievable without using private upstream validator internals. One total parse and zero temporary files are not promised.

**Alternative rejected:** replacing official validation with XML well-formedness or an upstream private-schema call weakens the current contract or couples us to private implementation details.

## R3 — Source-native traversal and current typed mapping

**Observed:** `rdam/ingest/prepare.py:98` converts through `_legacy_artifact`, `_harvest.inventory_source` and `_translate_item`. Its table reconstruction at line 536 consumes coordinates encoded by `_harvest.py:904`. Text handling is split between `_harvest.py:867` and `text_walker.py`. All three files were read completely.

**Decision:** decode format facts once; map them directly to current typed inventory. Retain the legacy route only for other formats and existing historical readers. Keep source classification and RDAM policy separate from low-level XML extraction.

**Rationale:** this removes repeated representation conversions while preserving the machine's existing public preparation pipeline. A format-neutral rewrite is unnecessary.

**Caution:** upstream's table helper collects direct text nodes; RDAM reconstructs cell coordinates and merged spans. The upstream traversal cannot replace RDAM's table semantics. Preserve the existing metadata-aware walker and extend it into the sole fragment owner.

## R4 — Private fragment addressing

**Observed:** upstream `content.h` resolves `text()[n]` after excluding whitespace-only text nodes. It is a custom convention, not safely interchangeable with ordinary XPath text-node numbering.

**Decision:** use explicit private text/tail slots described in the data model. Do not emit a new persisted anchor kind or change existing element paths. Resolve fragments against the original tree for extraction integrity and diagnostics.

**Rationale:** lxml represents mixed content through element text/tails; an explicit slot avoids whitespace/CDATA numbering ambiguity. Source byte identity and normalization remain distinct.

**Alternative:** public fragment-level citation support could be useful later, but requires an explicit schema and compatibility decision beyond this private refactor.

## R5 — Upstream currency and the supported boundary

Live metadata and source comparison on 2026-09-12:

| Item | Current upstream | Local observation |
|---|---|---|
| DocLang package | PyPI 0.7.3 | Pin `doclang[schematron-saxon]>=0.7.3,<0.8`; lock 0.7.3. |
| DocLang main | `663e9f59a5bb0e7e5c5be962fd942a4b3976c171` | Fixture manifest `6d3b3d3c195d1f63333c5c5fcba8da17937a33bd`. |
| Valid main fixtures | 59 | 42 mirrored; 17 additional track specimens upstream. |
| Invalid main fixtures | 78 | 59 mirrored; 19 additional track/bdiv specimens upstream. |
| Existing mirrored fixtures | No intersecting file changed | Every intersecting name/hash compared by the research agent. |
| Docling Core package | PyPI 2.96.0 | Pin `>=2.94.1,<2.95`; lock 2.94.1. |
| Docling document schema | Main constant 1.10.0 | All six discovered local DoclingDocument fixture versions equal 1.10.0. |

Sources: [DocLang PyPI](https://pypi.org/project/doclang/), [Docling Core PyPI](https://pypi.org/project/docling-core/), [DocLang fixture tree](https://github.com/doclang-project/doclang/tree/663e9f59a5bb0e7e5c5be962fd942a4b3976c171/tests/data), [Docling constants](https://github.com/docling-project/docling-core/blob/6073888fb9cac0c3de77a441c7c724620996fb7e/docling_core/types/doc/common/constants.py), local `pyproject.toml`, `pixi.lock` and fixture manifest.

**Runtime observation, one specimen only:** fetched and read `ok_track_minimal.dclg` at the main commit, then called installed `doclang.validate(path, allow_empty_namespace=True)` through locked Pixi. It raised `ValidationError: XSD validation failed`, reporting that `track` was not an expected element. This demonstrates one concrete release/main incompatibility; it does not prove the outcomes of the other new specimens.

**Decision:** preserve 0.7.3's supported corpus for the refactor, record the main-track gap, and do not vendor newer fixtures as accepted without a compatible released validator. Keep Docling Core unchanged and explicitly record its package drift. Recheck both at implementation start; dependency upgrades require a revised decision if they become necessary.

**Implementation recheck:** the research agent subsequently read the entire 158,079-character current DocLang `spec.md` through contiguous chunks. The releases and immutable commits above remained unchanged. Current-main `document.py` in Docling Core was inspected only through complete extracted methods, not the complete file; no 2.96.0 runtime compatibility claim is made.

The [archive section](https://github.com/doclang-project/doclang/blob/663e9f59a5bb0e7e5c5be962fd942a4b3976c171/spec.md#doclang-archive-format) requires the three OPC control parts and a main-document relationship. Retain these requirements.

**Normative defect discovered:** the released validator accepts orphan `lcel`, `ucel`, and `xcel`, mismatched intersection ownership, and the malformed fourth table in unchanged `ok_comprehensive.dclg`. RDAM now rejects impossible geometry and non-content cells containing body text. The original upstream mirror remains untouched; its conformance test explicitly distinguishes upstream validator acceptance from RDAM's semantic rejection. RDAM's separate `retained_content/mixed.dclg` specimen now has a valid rectangular merge.

The complete spec also confirms that metadata-subtree tails belong to body content, cells/items occupy direct-sibling intervals, nested tables have independent grids, and `content` preserves internal whitespace. These facts ground the targeted corrections recorded in [implementation results](implementation-results.md).

## R6 — Verification repairs are required

**Observed:** the complete `tools/rst_mutation_test.py` has three targets at nonexistent `rdam/rst/ingest/_harvest.py`. A locked-Pixi import of its mutant declarations printed `source_exists=False` for validator bypass, Markdown anchor offset and Docling body-layer-only mutants. The runner also uses any nonzero pytest exit as a kill, without an unmodified causal baseline.

**Decision:** repair the runner before relying on it. Reuse or extract the existing causal-verdict logic from the fully read `tools/shared_runtime_mutation_test.py` if it serves both runners; add regression tests for verdict classification. Do not introduce a new mutation framework.

**Observed:** `_inventory_doclang_data` currently fingerprints `_harvest.py` and `loader.py`; it does not explicitly include `text_walker.py`. This is a source inspection finding about the fingerprint inputs, not a demonstrated stale-cache incident.

**Decision:** include the actual semantic decoder/mapping files in the new identity and verify dependent cache behaviour. Do not preserve an obsolete fingerprint merely to obtain byte-equal baseline output.

## Planning validation and read scope

Command through locked Pixi: the four-file baseline in `quickstart.md` completed with **98 passed in 0.85s**. The full current-main conformance corpus, full production suite, inference and mutation gate were not run. Implementation performance gains have not been verified.

Complete local files read during this conversation: `CLAUDE.md`; `rdam/ingest/contracts/source.py`; `rdam/ingest/doclang/loader.py`; `text_walker.py`; `rdam/ingest/_harvest.py`; `prepare.py`; `pyproject.toml`; the constitution and planning scripts/template; `tests/ingest/test_doclang_text_walker.py`; `test_doclang_fixture_parity.py`; production-ingest `test_doclang_ingest.py`, `test_doclang_complex.py`, `test_upstream_conformance.py`, `test_performance.py`, `test_failure_stages.py`; `tests/machine/test_source_entry_points.py`; both mutation runners; fixture README; Markdown lint script/config. The research agent fully read the fixture manifest and upstream validator files. Large lock/fixture data was parsed in full for metadata comparison, not manually reviewed as complete content.

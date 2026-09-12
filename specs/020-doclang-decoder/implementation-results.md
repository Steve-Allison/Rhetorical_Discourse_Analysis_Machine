# Feature 020 implementation results

Status: implemented and verified in the working tree, 2026-09-12.

## Ownership and outcome

DocLang source reading belongs to **shared ingestion**. The complete private package moved from `rdam.rst.doclang` to `rdam.ingest.doclang`; the obsolete RST package is absent. `rdam.ingest._doclang` maps source facts directly into current inventory contracts for the machine and every technique. Existing persisted adapter labels remain unchanged for compatibility.

The document owns original bytes, one RDAM XML tree and a canonical path index. Archive checking reuses that main tree. Official path-based XSD/Schematron validation still runs against the original bytes; OPC requirements and ZIP bounds remain enforced. Private text-slot selectors resolve exact Unicode fragments, including comment/processing-instruction tails and trim ranges. They never enter serialized anchors.

A shared walker supplies raw/wrapped/list/cell surfaces. One marker traversal determines table coordinates; a local ownership grid verifies rectangular merged cells. Metadata and component wrappers remain inventoried. Current typed boxes/cell anchors are constructed without legacy selector strings or legacy inventory objects.

## Exact comparison and corrections

Captured 51 preparations at baseline commit `74f7f3a11183abcd707bf7021a9604b966c1160f`: 42 mirrored DocLang fixtures, the real form, four Docling fixtures, Markdown, archive, text and EDUs. The final comparison reconstructs expected preparation from the old inventory plus only the explicit corrections below and the new implementation fingerprint. All 50 still-accepted cases match exactly; the remaining malformed upstream specimen is explicitly rejected.

| Specimen | Proven correction |
|---|---|
| `doclang_example.dclg` | Recover the five raw list descriptions after their location heads. |
| `ok_content_in_virtual_text.dclg` | Recover list item `Second` inside `content`. |
| `ok_list_raw_before.dclg` | Recover `Raw text with location before`. |
| `ok_list_with_unwrapped_text.dclg` | Recover the sixth list's location-tail text and keep raw text after `foo` in its source order. |
| Real form `change-of-tenancy.dclg` | Remove generated picture description/custom metadata from the table's signed-name cell; link the two source pictures to their owning cells. |
| `ok_comprehensive.dclg` | Reject fourth-table empty/continuation cells containing text and orphan continuations. The upstream mirror and its manifest remain byte-identical. |

New exact regressions additionally cover duplicate wrapper tails, mixed raw/wrapped and nested-list ordering, nested-primary deduplication, nested-table isolation, comments, CDATA, metadata exclusion, and invalid merge ownership. Those specimens are independently specified; there is no blanket baseline refresh.

The old Feature 017 comparison tests now use the exact pre-020 semantic snapshot captured before this change for their historical DocLang correction proof. No execution record is invented. Their existing corruption cases remain active. New baseline captures use RDAM's corrected valid mixed-content specimen. The historical upstream specimen is not silently repaired.

Source bytes, IDs, public shapes, paths, classifications and non-DocLang content are preserved except for the named semantic repairs. Only the existing implementation fingerprint and its dependent identities change routinely. Tests alter each actual fingerprint input independently and prove that changing the decoder revision prevents an old analysis-cache hit.

## Verification

- Exact semantic comparison: **50 matched; 1 named malformed input rejected**.
- Critical mutation gate: **10/10 killed**, with a passing unmodified causal test first. Collection/setup/import failures and timeouts do not count as kills.
- Strict Pyright: **0 errors, 0 warnings**. Its informational newer-version notice does not change the locked environment.
- Python modernization lint: **passed**, without added suppressions.
- Source production boundary: **174 modules scanned, zero violations**. This is source-tree evidence, not wheel certification.
- Ingestion suite: **596 passed in 119.93 seconds**; format branch coverage **96.37%**, against the unchanged 90% floor. Decoder coverage is **98.76%**.
- Historical baseline comparison tests: **34 passed in 12.25 seconds**.
- Ruff: **all checks passed**. Markdown: **273 files, zero issues**, including all eight feature documents.
- AST graph refreshed: **37,098 nodes, 56,684 edges**. No semantic labeling API call was made.
- Full fast suite (`pytest -m "not slow and not stress and not live" -q`): **3,088 passed, 197 deselected, 1 third-party warning in 437.88 seconds**. This includes machine/interface tests; slow, stress and live checks were not run.
- Final diff inspection and whitespace check passed. Production changes are confined to shared DocLang ingestion and the shared classifier; tests, affected tooling, documentation and the generated graph accompany them.

The broad suite emits a third-party `google.genai` deprecation warning for Python's `_UnionGenericAlias`. No warning filter or dependency upgrade is introduced by this DocLang change. Graphify also reports its existing skill/package version mismatch (0.9.54/0.9.53) and that community labels need semantic refresh; the AST update succeeded, but semantic labels are not certified current.

## Matched performance

Each process used one warmup followed by five measured public preparations. Baseline ran from an isolated export of the exact commit; candidate ran from this checkout using the same locked interpreter/dependencies and identical input bytes. A final sequential pair followed an earlier run under concurrent verification load. All final samples are shown, in milliseconds.

| Input | Bytes | XML nodes | Baseline samples (ms) | Candidate samples (ms) |
|---|---:|---:|---|---|
| form-xml | 13184 | 388 | 185.096, 121.778, 119.464, 116.352, 120.537 | 181.726, 118.183, 116.112, 113.872, 117.772 |
| table100-xml | 3034 | 302 | 237.042, 296.681, 239.007, 242.492, 240.503 | 235.034, 234.959, 307.725, 249.117, 245.057 |
| table100-archive | 4118 | 302 | 242.464, 242.422, 242.625, 246.560, 251.872 | 248.967, 250.170, 246.888, 243.688, 246.642 |

The table has 100 rows and 200 cells. The archive uses stored ZIP members so repetitive test text does not violate the real compression-ratio bound. The real form is tested as XML because the fixture does not provide its referenced binary assets.

Final process peak RSS, a cumulative native-inclusive process high-water mark: baseline **588,398,592 bytes**; candidate **587,628,544 bytes**. It is not a per-document allocation measurement. Median changes are small (about -2.3% for the form, +1.9% for table XML, +1.8% for archive); these runs do not establish a general speedup.

An inclusive call profile on the 100-row XML recorded one official validation call in both revisions (~178–180 ms under profiling). The baseline made 302 `_doclang_anchors` calls and 302 `_translate_item` calls. The candidate made one main-tree parse, one path-index call and one decoder call, with no legacy conversion. Archive regression profiling verifies three RDAM control-part parses in total, including exactly one main-document parse. These structural counts are distinct from end-to-end latency.

The initial 1,000-row experiment spent minutes in Saxon and was invalidated when the running baseline later tried to fingerprint a relocated working-tree path. It provides no usable before/after measurement. The retained measurements above use an isolated baseline to avoid that error.

## Supported upstream boundary

DocLang remains `0.7.3`, including official Saxon Schematron validation. Current-main commit `663e9f59a5bb0e7e5c5be962fd942a4b3976c171` has 59 valid/78 invalid specimens versus the pinned mirror's 42/59. The additional track/bdiv cases are not advertised as supported: installed 0.7.3 rejects the main-only minimal track specimen. All intersecting fixture names/hashes are unchanged.

Docling Core remains pinned/locked at 2.94.1; current upstream is 2.96.0. Its schema 1.10.0 matches the local fixtures, but this work does not certify a dependency upgrade. No dependency, public schema, trained model or inference mathematics changed. See [research](research.md) for immutable upstream sources and the complete-spec read evidence.

## Read scope and local evidence

Read in full before implementation/reliance: the feature planning package; shared preparation/policy/source contracts and identity/cache modules; original DocLang loader/walker/errors; original legacy harvester; new document/decoder/mapper/classification modules; mutation runners; relevant DocLang/archive/retained-content/conformance and baseline-correction tests; baseline capture/comparison tools; dependency/task configuration; current production-boundary documentation. The research agent fully read the current DocLang spec and validator files. JSON baselines, fixture manifests and lock metadata were parsed completely for comparisons.

Temporary 51-case records, exact candidate differences, comparison script outputs, profiles and measurements remain at:

`/var/folders/w_/d3z3xl2j6qzcsp3r44q4_djw0000gq/T/rdam-020-baseline-2blzgmwz`

No publication, commit, tag or push is part of this implementation.

Runtime: Python 3.14.7, Darwin arm64, DocLang 0.7.3, docling-core 2.94.1, lxml 6.1.2.

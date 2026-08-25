# Research: World-Class Production Source Ingest

**Evidence date:** 2026-08-25

## 1. One canonical preparation boundary, not five pipelines

**Decision**: Add `isanlp_rst.ingest` as the single production authority for source identity, inventory, policy, preparation, coverage, subdivision, cache identity, receipt, and result. Existing source-format modules retain only format-specific validation and inventory projection. Plain text, EDUs, Markdown, Docling, and DocLang all enter the same service.

**Rationale**: The current format routes separately implement knobs, flat string joining, length rejection, cache lookup, parsing, projection, and result envelopes. That prevents one enforceable relevance policy or coverage proof. A small common boundary removes duplication without adding services or a plugin framework.

**Rejected**: Keep improving each adapter independently; create a parallel adapter tree; introduce a third shared distribution; use a workflow engine.

## 2. Production, promotion evidence, and offline evaluation remain separate

**Decision**: Runtime contracts and behavior live only under `isanlp_rst`. Redistributable conformance fixtures live under `tests`; private real Gold Set content remains in a local root; text-free manifests and inspection evidence live under the feature specification; release orchestration lives under `tools/production_ingest`; RST metric math remains canonical in `offline_workbench.evaluation.rst` and scores frozen serialized outputs after clean production execution.

**Rationale**: Feature 003 established a one-way dependency: offline/repository code may consume production, never the reverse. Gold labels and Parseval are required to prove ingest quality but are not source-ingest runtime capabilities. Separating clean-wheel execution from later scoring satisfies both the quality gate and the production boundary without duplicating a scorer.

**Rejected**: Package Gold annotations or Parseval in production; make runtime call an evaluator; duplicate Parseval under tools; treat release evidence as training content.

## 3. Current upstream versions are already correctly pinned

**Decision**: Retain `docling-core>=2.92,<2.93` and `doclang[schematron-saxon]>=0.7.3,<0.8`. Do not add the full `docling` package or Docling chunking extra.

**Evidence**:

- PyPI latest on 2026-08-25 is [`docling-core` 2.92.0](https://pypi.org/project/docling-core/); Pixi resolves 2.92.0. Current DoclingDocument schema is 1.10.0, and all four local fixtures load under the current runtime.
- PyPI latest is [`doclang` 0.7.3](https://pypi.org/project/doclang/); Pixi resolves 0.7.3 with `saxonche>=12.9.0` from the full-validation extra.
- Upstream DocLang `main` is commit `6d3b3d3c195d1f63333c5c5fcba8da17937a33bd`, matching the local manifest. Local/upstream inventories are 42 `.dclg` files with identical names and hashes.
- Current Docling native chunkers demonstrate the right structure-first principle, but the optional chunking dependency conflicts with this runtime's Transformers range on macOS and is designed for RAG token chunks, not RST tree construction. The production ingest will implement its own small RST-specific subdivision over the canonical prepared hierarchy.

**Rejected**: Upgrade for appearance; install full Docling conversion machinery; use `docling-core[chunking]`; treat pins or locks alone as contract proof.

## 4. Docling validation preserves both raw and accepted contract identity

**Decision**: Read raw `schema_name`/`version` from JSON before loading, validate with `DoclingDocument.load_from_json`, then record raw declared version, accepted normalized version, `docling-core` version, source origin, and raw digest separately. Inventory the entire validated document using all content layers, groups, and top-level collections before applying policy.

**Rationale**: In 2.92.0, the loader accepts compatible schema versions and normalizes the loaded object to current 1.10.0. Recording only `doc.version` loses the incoming declaration. Current `iterate_items()` supports `with_groups=True`, `traverse_pictures=True`, and explicit content layers `body`, `furniture`, `background`, `invisible`, and `notes`. Complete inventory requires all of them, plus reconciliation with top-level item collections.

**Rejected**: Cache before loading; infer source version from the loaded object; pre-filter layers during inventory; silently skip unresolved references; use Docling's downgrade projector to avoid validation.

## 5. DocLang accepts the full current source family

**Decision**: Support `.dclg`, `.dclg.xml`, and `.dclx` as one DocLang source family. Run full XSD+Schematron validation with `allow_empty_namespace=True`, because current DocLang permits an omitted namespace. Securely open `.dclx` as its current OPC/ZIP archive form, inventory `document.xml` plus asset identities, reject traversal/symlink/duplicate/member-size/compression abuse, and never execute or fetch assets.

**Rationale**: The current [DocLang toolkit](https://github.com/doclang-project/doclang/blob/main/doclang/README.md) requires `schematron-saxon` for default full validation and documents `allow_empty_namespace=True`. The [0.7 changelog](https://github.com/doclang-project/doclang/blob/main/CHANGELOG.md) adds the archive format and hardens DTD/entity and symlink behavior. Current upstream valid specimens include namespaced and non-namespaced documents. A caller should not need `validate_xml=False` or manual extraction to submit a current-valid DocLang source.

**Rejected**: Force a namespace; XSD-only validation; support bare XML only; depend on the full Docling converter; extract archives to an uncontrolled directory.

## 6. Valid source structure is inventoried even when RST cannot analyse it

**Decision**: Inventory all current semantic, structural, head, layout, origin, and container items. Represent table/list/group/field/picture structure recursively. Give every item exactly one disposition: primary, side-channel, excluded, transformed, deduplicated, or rejected. Unsupported-but-valid analysis treatment is retained with `not_analysed`, not rejected.

**Rationale**: Current DocLang permits any semantic element sequence inside table cells, including nested tables; the current adapter rejects this and requests destructive upstream flattening. Docling has 30 current item labels while the four fixtures cover only eight. An eligibility-first harvester cannot prove what it never enumerated.

**Rejected**: Flatten tables to blank-line cell text; reject nested tables; drop unknown valid items; treat a boundary marker as an inventory disposition.

## 7. `authored_prose_v1` is the safe production default

**Decision**: Include authored prose, titles/headings, meaningful list text, and authored transcript turns. Keep code, formulas, raw markup, script/style/navigation, furniture/background/invisible content, machine picture descriptions, slide notes, and table structure outside primary RST by default. Retain excluded content and origin evidence. Opt-in behavior is available only through explicit named policies.

**Rationale**: RST relations are meaningful only over a coherent authored discourse stream. The current defaults include Markdown code/raw HTML/tables and Docling notes/picture descriptions/tables. In the real PPTX fixture, five identical note blocks contribute 6,890 repeated characters. [Unstructured's partition model](https://docs.unstructured.io/open-source/core-functionality/partitioning) likewise exposes typed elements so an application can select narrative text instead of treating every extraction as prose.

**Rejected**: Preserve current booleans as the default; silently deduplicate repeated prose; discard excluded content; treat all human-visible text as primary discourse.

## 8. Raw HTML is parsed structurally, never regex-stripped

**Decision**: Use the already-installed hardened lxml HTML parser to inventory HTML nodes and text. Exclude script, style, navigation, templates, metadata, and markup artifacts by default; preserve them as side-channel source evidence. Only text from explicitly eligible authored-content nodes may enter primary RST.

**Rationale**: The [GFM specification](https://github.github.com/gfm/) treats raw HTML blocks—including script/style blocks—as literal HTML and notes that GitHub applies additional sanitization. The current `<[^>]+>` substitution leaves script/style bodies behind and destroys DOM context, so it cannot make a trustworthy relevance decision.

**Rejected**: Regex tag removal; rendered-HTML execution; network retrieval; blanket rejection of Markdown containing HTML.

## 9. Reversible prepared text uses explicit segment mappings

**Decision**: Represent prepared text as ordered source-derived or synthetic segments. Each source-derived segment retains native address, source text/range, prepared range, structure ancestry, and every normalization operation. Synthetic separators and macro representations have their own identities and can never masquerade as source text.

**Rationale**: The [W3C Web Annotation Data Model](https://www.w3.org/TR/annotation-model/) establishes position, quote, XPath, and refined selectors for robust targeting. W3C PROV distinguishes entities, activities, and derivations. The local contract need not implement RDF, but should retain the same essential separation: source entity, preparation activity, derived text, and exact selectors.

**Unicode decision**: Preserve source characters by default. Permit canonical NFC only through a named transformation with an exact map; prohibit blind NFKC/NFKD. [Unicode UAX #15](https://unicode.org/reports/tr15/) warns that compatibility normalization can remove meaningful distinctions and that concatenated normalized strings are not necessarily normalized.

**Rejected**: Only source-ref overlap; fabricated offsets after stripping; compatibility normalization; unreceipted `.strip()` or whitespace collapse; implicit `\n\n` joining.

## 10. Structure constrains analysis before the parser runs

**Decision**: Build a hierarchy from source structure, then derive complete ordered analysis units. Prefer authored headings/sections/groups/slides/turns; use pages only as secondary layout evidence; fall back deterministically to paragraphs/sentences/ranges. Determine unit capacity from a stable parser/model capability contract. Analyse local units, derive anchored nuclear-spine macro representations, recursively analyse structural parents, and stitch one coherent tree.

**Rationale**: [Docling's current chunking design](https://docling-project.github.io/docling/concepts/chunking/) operates on the native document structure, retains headings/captions, and subdivides only oversized content. [Docling heading hierarchy](https://docling-project.github.io/docling/usage/heading_levels/) explicitly notes that flat heading levels weaken hierarchical downstream processing. RST needs the same structure-first principle, but with complete tree construction rather than independent RAG chunks.

**Rejected**: Parse one flat string then annotate memberships; fail at 200,000 characters; ask the caller to chunk; arbitrary fixed 300-character macro prefixes; independently parse chunks without a document-level tree; let overlap duplicate output EDUs.

## 11. Cache identity describes analytical meaning

**Decision**: Compute a stable fingerprint from raw source identity, raw/accepted upstream contract, validator versions/semantics, inventory adapter identity, policy digest, preparation/subdivision identity, released-model manifest/file digests, and result-contract version. Canonicalize hash inputs deterministically and verify the stored payload digest on load. Validate before lookup.

**Rationale**: [RFC 8785](https://www.rfc-editor.org/rfc/rfc8785.html) explains why cryptographic hashing requires invariant JSON representation. Current keys omit validator/package/preparation/source revision identity and use process-local `id(parser)` for injected parsers. A current validation result cannot be inherited from an older cache.

**Behavior**:

- changed identity: normal miss;
- valid matching entry: hit after integrity/identity verification;
- corrupt or contradictory entry at the expected key: actionable failure;
- parser without immutable model digest: analysis permitted, durable cache disabled and receipted.

**Rejected**: Treat corrupt as an unexplained miss; cache before validation; key by source bytes and basename alone; use object identity; include timing/timestamp in semantic identity.

## 12. Determinism separates semantic and execution evidence

**Decision**: `PreparationReceipt.semantic_digest` covers only deterministic source, policy, mapping, disposition, coverage, subdivision, model, and result meaning. `ExecutionReceipt` carries timestamp, duration, peak RSS, cache state, and machine observation. Ten repeated cached/uncached runs must match on semantic form while execution observations may differ.

**Rationale**: The specification requires both meaningful semantic equality and actual timings/cache evidence. Mixing them in one equality surface makes those requirements contradictory.

**Rejected**: Freeze fabricated timings; omit operational evidence; declare JSON byte equality while embedding current timestamps.

## 13. Gold Set and promotion use ordered, per-source gates

**Decision**: Freeze at least 20 real/normative/synthetic sources before candidate execution, with all five source families and all required risk classes. Every source has source identity and human-verified inventory/policy/structure/coverage/anchor expectations; at least 12 have adjudicated EDU and primary RST structure. Run baseline and candidate with identical released-model bytes and machine. Report each source before aggregates.

**RST evaluation decision**: Use segmentation precision/recall/F1 plus Standard Parseval Span, Nuclearity, Relation, and Full metrics from the canonical offline scorer. Do not change metric configuration after candidate results exist. [Morey et al. (2017)](https://aclanthology.org/D17-1136/) showed that inconsistent RST evaluation implementations can manufacture apparent progress, so scorer identity and configuration are frozen evidence.

**Rejected**: Large shallow benchmark; aggregate-only promotion; synthetic mocks in place of real/normative sources; retraining; manual cleanup; per-document exceptions; scorer duplication or post-result tuning.

## 14. Dated SOTA comparison and bounded claim

| Required capability | Current primary practice | Feature 002 response | Gap after design |
|---|---|---|---|
| Source-contract compliance | Docling Pydantic document contract; DocLang XSD+Schematron and normative specimens | Validate current contract before trust/cache; retain raw and accepted identity; run unmodified specimens | None planned |
| Authored-content selection | Docling content layers; typed Unstructured elements | Complete inventory first; named `authored_prose_v1`; retained side channels | None planned |
| Structure-aware long documents | Docling hierarchical/hybrid chunking retains document hierarchy and only splits oversized units | Recursive structure-first RST units, coherent macro/micro tree, million-character proof | None planned |
| Source provenance | W3C selector and derivation principles | Native + quote/position selectors, transformation ledger, synthetic separation, round-trip anchors | None planned |
| Loss accounting | Typed elements and metadata are common; most systems do not prove full reconciliation | Exactly-one disposition and source/prepared/analysis coverage proof, fail closed | Stronger than compared defaults |
| Determinism/cache identity | RFC 8785 canonical hashing principle | Full analytical fingerprint, integrity-checked cache, semantic/execution split | None planned |
| Production RST evaluation | Standardized Parseval implementation and fixed scoring conditions | Frozen identical-model baseline/candidate, EDU + Span/Nuclearity/Relation/Full, per-source gates | None planned |

**Bounded claim**: If implementation and all promotion gates pass, the project may claim state-of-the-art production source ingest for this small-volume RST/eRST use case as of 2026-08-25. It may not claim model-level SOTA, enterprise throughput, universal document conversion, or superiority outside the compared capabilities.

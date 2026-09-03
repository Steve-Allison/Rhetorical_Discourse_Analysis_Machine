# Contract: RST Preservation Inside the Machine

**Feature**: 006 | **Authority**: [spec.md](../spec.md) FR-008..FR-011, SC-002

`rdam.rst` is the machine's canonical RST/eRST provider and remains directly usable.
Changes elsewhere in the machine are valid only while this contract stays green.
Historical `isanlp_rst` strings embedded in model manifests, runtime contracts, media
types, or producer identities remain compatibility data; they are not Python import or
command names.

## Preserved public surface

| Surface | Required preservation |
|---|---|
| Package and command | The `rdam` distribution contains importable `rdam.rst`; `rdam-rst` resolves to `rdam.rst.cli:main`. |
| Parser façade | `rdam.rst.Parser` supports DMRST and UniRST dispatch, published and immutable local releases, explicit device/dtype behaviour, text/EDU parsing, typed document analysis, batch and hierarchical parsing, and eRST completion when a validated bundle resolves. |
| Machine provider | `rdam.rst.provider.RstProvider` declares RST and eRST formalisms without loading a model, maps canonical ingest failures one-to-one, and returns the native serialized ingest outcome unchanged as its payload. |
| Canonical ingest | `rdam.rst.ingest.ProductionIngestor.capabilities()`, `.prepare()`, and `.analyse()` support `text`, `edus`, `markdown`, `docling_json`, `doclang_xml`, and `doclang_archive`, retaining receipts, anchors, subdivision, component identity, and cache identity. |
| Native contracts | Public models and serializers under `rdam.rst.contracts` and `rdam.rst.ingest` preserve strict validation, canonical serialization, semantic digests, and versioned read/write behaviour. |
| RST/eRST artifacts | `DiscourseUnit`, RS3, RS4, signals, graph projections, ontology adapters, and viewer/rendering exports preserve their native meanings. |
| Boundary projections | The CLI and loopback HTTP API project the same canonical ingest contract and retain phase-accurate, privacy-safe typed failures. |

No aggregate caller may require an RST consumer to adopt a theory-neutral replacement
for these native results. Trained architecture, inference mathematics, relation meaning,
model identity, or serialization changes require their own approved and validated
feature; repository or machine work cannot change them incidentally.

## Equivalence procedure (SC-002)

1. Run the focused public-surface, contract, serialization, ingest, provider, and CLI
   tests through Pixi. All six source forms must be covered, including current upstream
   Docling and DocLang conformance fixtures.
2. Run `pixi run test`, `pixi run production-boundary`, `pixi run lint`, and
   `pixi run typecheck`. Run `pixi run test-all` when the available local model releases
   and external-provider conditions permit its integration tests to execute honestly.
3. For a distribution candidate, build and validate the wheel/sdist and run
   `pixi run -e production production-clean-install`; an editable-source import check is
   not wheel proof.
4. Compare canonical serialized records byte-for-byte and computed parse results under
   their established semantic equivalence assertions. A failing comparison is a product
   defect; the expected record is never edited merely to match the new output.

Pass condition: every supported public operation and persisted contract kind exercised
by the governed test manifest passes. The dated observed commands and counts belong in
[../evidence/rst-surface-audit.md](../evidence/rst-surface-audit.md).

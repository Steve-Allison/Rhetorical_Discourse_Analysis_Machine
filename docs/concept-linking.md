# Shared concept linking

`rdam.concepts` links exact inventory surfaces to the packaged Central distribution.
It is opt-in, uses no model or credentials, and is independent of discourse techniques.
Central defines meanings; this module produces lexical candidates, never accepted bindings.

## Python

```python
from pathlib import Path
from rdam.concepts import ConceptIndex, ConceptLinkRequest, link_source
from rdam.concepts.serialization import serialize, export_jsonl
from rdam.ingest import SourceArtifact

index = ConceptIndex.load()  # all eight declared domains
source = SourceArtifact.from_text("Adobe Analytics supports reporting.", source_name="example.txt")
result = link_source(source, index)
Path("links.json").write_bytes(serialize(result))
Path("mentions.jsonl").write_bytes(export_jsonl(result))
Path("request.json").write_text(ConceptLinkRequest(source=source).model_dump_json())
```

Use `link_inventory(inventory, index)` to reuse an existing `ContentInventory`.
`resolve_candidates(inventory, index, spans)` accepts explicit `CandidateSpan` records
with item ID, representation pointer, start/end and quote. Unknown supplied phrases
remain `unmapped`; a dictionary scan cannot report all unknown concepts.

`ConceptIndex.load(path, domains=("adobe",))` loads a generated JSON projection or a
directory containing `concept-index.json`. It does not compile raw LinkML at runtime.
Development projection generation follows Central's distribution/domain manifests:

```sh
pixi run python tools/compile_concept_index.py --help
```

The packaged distribution (`rdam/resources/concept-index.json`, verified 2026-11-15 via
`ConceptIndex.load().projection` at `rdam/concepts/index.py:103-140`) is Central
`coe:distribution/4.0.0` (`4.0.0`): eight domains, 2,482 semantic resources, and 3,516
lexical entries (2,315 labels, 1,201 terms), including the fourteen analytical framework
concepts under `coe:artifact/narrative/analytical_frameworks_taxonomy`. Matching is
executed via compiled Rust `ahocorasick_rs` automata cached per `(content_digest, domains,
acronym_case_sensitive)` (`rdam/concepts/linker.py:73-146`), and `scan_text_mentions()`
(`rdam/concepts/linker.py:210-239`) also supplies deterministic `concept_mention` signals
to `LinguisticSubstrate` during source preparation (`rdam/ingest/substrate.py:314-324`).
A lexical entry is a resource's label or one of its Central terms, the names Central
carries inline on the resource with a LexInfo term type and status. Duplicate IDs, absent
declared modules, unknown fields, and invalid term types or statuses fail compilation.
Domain selection restricts matching without editing Central. Retired identifiers remain
available diagnostically and cannot produce active candidates.

## Wire interfaces

```sh
pixi run rdam concepts link --request request.json --output links.json
pixi run rdam concepts link --request request.json --format jsonl --output mentions.jsonl
pixi run rdam schema concept-links
```

`POST /v1/concepts/link` consumes the same typed request and returns the same result
through the existing bounded HTTP adapter. Configure the index through `create_app` or
`rdam serve --ontology-index`; requests cannot select server filesystem paths.
Schemas for request, result and standalone mention records are shipped under
`rdam/ingest/schemas/concept-*.schema.json` in validation and serialization modes.

The result contract is `rdam.concept_links`, version `2.0.0`; exported mentions are
`rdam.concept_mention` `2.0.0`. Its identity includes
source, inventory, adapter, ontology digest/domains, algorithm, implementation and options.
Each mention retains original anchors and a named text surface. Offsets are zero-based,
half-open Python character offsets into that surface, not XML or file byte offsets.
`validate_result(result, inventory, index)` replays matching and rejects stale evidence.

Ordinary labels use Unicode-aware case folding and whitespace matching with reversible
offsets. Acronyms, initialisms and product codes are case-sensitive by default
(`acronym_case_sensitive`). Punctuation, overlapping ranges and separate occurrences
survive. Each matching reason is `label` or `term`; a term reason retains its term type,
status (`admitted`, `superseded` or `deprecated`), validity dates and usage note, so
superseded and deprecated names still match and say so. A unique lexical target is not
proof of contextual meaning.
Generated descriptions retain authorship and layer. Code, formula and metadata remain
classified separately. Non-text, empty, redacted and explicit duplicate surfaces are
accounted for rather than reconstructed or silently merged.

## Downstream example

```sh
pixi run python examples/concept_passages.py mentions.jsonl coe:entity/adobe/analytics
pixi run python examples/concept_passages.py links.json coe:entity/adobe/analytics --analysis analysis.json
```

The example also reads CSM 5.3 retrieval cards and treats historical 5.2 cards without
mention evidence as empty. It displays quotes, anchors, candidates or explicit acceptance,
and optional native analysis locations. The native join establishes shared inventory
location only; it does not infer support, agreement or pedagogical suitability.

CSM owns its explicit review decisions and adapter. See its
`docs/technical/concept-linking.md`. The isolated Docling NLP comparison and measurements
are in `workbench/experiments/concept_linking/REPORT.md`.

## Verification scope

See `specs/021-shared-concept-links/verification.md` for original Feature 021 check
outcomes and limitations, and `tests/concepts/` (`pixi run pytest tests/concepts -q`) for
live compilation and matching verification against `../Central_Configs`. RDAM tracks
`dclq` `>=2.107.0,<3` and DocLang `main` (`ae8ad5490b9b03b344e3e49dcb0f6f2209795de6` as
of 2026-11-15; see [production ingest](production-source-ingest.md)). Locked versions
must not be described as the latest spec.

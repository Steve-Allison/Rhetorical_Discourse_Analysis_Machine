# Shared concept linking

`rdam.concepts` links exact inventory surfaces to the packaged `Central_Configs` v5.0.0
proper-noun surface lexicon (`LinkableProperNoun` classes only; Rule 6 craft firewall).
It is opt-in, uses no model or credentials, and is independent of discourse techniques.
`Central_Configs` defines meanings; this module produces deterministic Stage 1 proper-noun
mentions and candidate spans, never LLM-inferred semantic acceptance.

## Python

```python
from pathlib import Path
from rdam.concepts import ConceptIndex, ConceptLinkRequest, link_source
from rdam.concepts.serialization import serialize, export_jsonl
from rdam.ingest import SourceArtifact

index = ConceptIndex.load()  # all ten LinkableProperNoun collections
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

`ConceptIndex.load(path, domains=("offerings",))` loads a generated JSON projection or a
directory containing `concept-index.json`. It does not read LinkML or SQLite at runtime.
Development projection generation queries `../Central_Configs/dist/build/central.sqlite`
and `../Central_Configs/schema/coe.linkml.yaml`:

```sh
pixi run python tools/compile_concept_index.py --help
```

The packaged distribution (`rdam/resources/concept-index.json`, verified 2026-11-15 via
`ConceptIndex.load().projection` at `rdam/concepts/index.py:101-137`) projects
`https://steve-allison.github.io/Central_Configs/v5/schema/coe` (`5.0.0`): ten
`LinkableProperNoun` collections (`add_ons`, `ai_agents`, `ai_models`, `business_units`,
`editions`, `offerings`, `organisations`, `product_capabilities`, `surfaces`,
`technical_standards`), 206 resources (`^coe:C[0-9]{5}$`), and 330 `SurfaceMatchRule`
entries. Craft, pedagogy, rhetoric, discourse, and rubric concepts never enter
`concept-index.json`. Matching executes via compiled Rust `ahocorasick_rs` automata cached
per `(content_digest, domains)` (`rdam/concepts/linker.py:92-135`), enforcing identifier-safe
boundaries, `case_exact` / `case_sensitive` gates, `±25`-token `negative_phrases` vetoes,
`±anchor_window_tokens` `context_anchors` checks (excluding the matched span itself), and
leftmost-longest non-overlapping span selection. Spans with `requires_llm_disambiguation=True`
or multiple candidate CURIEs emit `resolution="ambiguous"`, `ambiguous=True`, and `curie=None`
with `candidate_curies`, while deterministic spans set `curie=candidate_curies[0]`.
`scan_text_mentions()` (`rdam/concepts/linker.py:293-331`) supplies deterministic
`concept_mention` signals (`resolution="unique"` only) to `LinguisticSubstrate` during
source preparation (`rdam/ingest/substrate.py:314-324`).

## Wire interfaces

```sh
pixi run rdam concepts link --request request.json --output links.json
pixi run rdam concepts link --request request.json --format jsonl --output mentions.jsonl
pixi run rdam schema concept-links
```

`POST /v1/concepts/link` consumes the same typed request and returns the same result
through the existing bounded HTTP adapter. Configure the index through `create_app` or
`rdam serve --ontology-index`; requests cannot select server filesystem paths.
Schemas for index, request, result and standalone mention records are shipped under
`rdam/ingest/schemas/concept-*.schema.json` in validation and serialization modes.

The result contract is `rdam.concept_links`, version `3.0.0`; exported mentions are
`rdam.concept_mention` `3.0.0`, and the index contract is `rdam.concept_index` `3.0.0`.
Each result identity includes source, inventory, adapter, ontology digest/domains,
algorithm, implementation and options. Each mention retains original anchors and a named
text surface. Offsets are zero-based, half-open Python character offsets into that surface,
not XML or file byte offsets. `validate_result(result, inventory, index)` replays matching
and rejects stale evidence.

## Downstream example

```sh
pixi run python examples/concept_passages.py mentions.jsonl coe:C01007
pixi run python examples/concept_passages.py links.json coe:C01007 --analysis analysis.json
```

The example also reads CSM 5.3 retrieval cards and treats historical 5.2 cards without
mention evidence as empty. It displays quotes, anchors, candidates or explicit acceptance,
and optional native analysis locations. The native join establishes shared inventory
location only; it does not infer support, agreement or pedagogical suitability.

## Verification scope

See `tests/concepts/` (`pixi run pytest tests/concepts -q`), including
`tests/concepts/test_golden_grounding.py` against `../Central_Configs/tests/golden_grounding.yaml`
(200 benchmark sentences: 190 deterministic cases including 40 NIL traps, plus 10 Stage 2
LLM disambiguation candidate-surfacing cases). RDAM tracks `dclq` `>=2.107.0,<3` and
DocLang `main` (`ae8ad5490b9b03b344e3e49dcb0f6f2209795de6` as of 2026-11-15; see
[production ingest](production-source-ingest.md)). Locked versions must not be described as
the latest spec.

# Shared concept linking and downstream evidence integration

Status: approved for implementation by Steve, 2026-09-12.

## User scenarios

1. A caller links an existing shared ContentInventory to Central identifiers without
   loading a model, reading source formats again, or supplying credentials.
2. A caller supplies source-anchored extracted phrases and receives lexical candidates,
   ambiguity, or an explicit unmapped result with exact evidence.
3. CSM curates candidates separately from node ontology bindings, persists reviewed
   mention selections, and projects them into retrieval cards 5.3.
4. A downstream consumer finds passages by canonical identifier and optionally joins
   native analysis through shared source locations, without inferring entailment.
5. An isolated docling-nlp 1.4.0 experiment measures extraction coverage against fixed
   independent annotations and recommends adoption or rejection from measurements.

## Requirements

- Central remains the sole ontology authority. Follow all distribution/domain modules;
  preserve term senses, definitions, distinctions and synonym scopes. Reject duplicate
  identifiers, dangling terminology references and missing declared files.
- Default to all domains, with explicit domain restriction; retain retired records for
  diagnostics but exclude them from matches. Generate a runtime JSON projection during
  development/build; runtime requires neither LinkML compilation nor network.
- Publish rdam.concepts with ConceptIndex.load, link_inventory, link_source and
  resolve_candidates. Expose the same operation through typed JSON, CLI, bounded HTTP,
  JSON Schema and independently consumable JSONL mentions.
- Separate versioned contract rdam.concept_links 1.0.0. Preserve existing analytical and
  preparation contracts. HTTP requests cannot name server filesystem paths.
- Evidence includes source, inventory, adapter, ontology snapshot, implementation and
  matching options, representation pointer, exact surface identity, original anchors,
  half-open Python character offsets, exact quote and stable occurrence identity.
- Preserve source layer/authorship, including generated descriptions. Distinguish code,
  formula and metadata. Account for redacted/non-text/explicit duplicate exclusions.
- Match only within each surface. Unicode casefold and whitespace normalization retain
  original offsets, punctuation and word boundaries; acronyms are case-sensitive.
  Preserve overlaps and separate occurrences; combine matching reasons per target/span.
  No stemming, fuzzy matches, guessed abbreviations or inferred semantic relationships.
- Unique means lexical uniqueness, not contextual truth or accepted CSM binding.
  Broad/narrow/deprecated synonyms retain their scope. Only supplied unknown spans are
  unmapped; dictionary scanning does not certify complete conceptual coverage.
- Validate all references, quotes, offsets and reused identities; stale evidence fails.
- CSM owns its adapter and exact/close/unmapped acceptance. Reconcile source locators
  explicitly, never by array index alone. Keep pending candidates separate from accepted
  mentions and preserve node-level ontology_binding. Old cards contain no invented links.
- Use the current wiki authority; no corpus migration, live publication or changes to
  accepted source plates. Replace CSM's Adobe-only resolver while retaining its active
  resource and predicate checks.
- docling-nlp stays evaluation-only in a separate Pixi environment. Compare baseline
  matching to extraction plus the same resolver on identical surfaces. Verify offset
  units and measure precision/recall, canonical inclusion, ambiguity, spurious/additional
  mentions, runtime, memory and installation complexity. No production dependency changes.

## Success criteria

Real public and persisted-output tests cover six source forms, representation classes,
Unicode/ambiguity/overlap/staleness, Python/CLI/HTTP parity, reviewed CSM authoring and
regeneration, installed-package consumption and historical cards. Run RDAM fast tests,
lint, strict typing, boundary/build checks; CSM test/lint/format/type/CI. Report corpus
failures separately. Update docs/schemas/readers/examples and refresh graphs. No push,
tag or remote publication. All phases remain in scope until verified.

## Assumptions

No additional product decisions; the supplied implementation plan is authoritative.

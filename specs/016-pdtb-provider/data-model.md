# Data Model: PDTB Provider

## TextSpan

- `start`, `end`: zero-based half-open character offsets with `start < end`.
- `text`: non-empty exact source slice.

Offsets accept integers only: strings and booleans are not coerced. Span text is retained
exactly as proposed so source validation can detect, rather than normalize, a mismatch.

## PdtbArgument

- `spans`: one or more internally ordered, non-overlapping `TextSpan` values.

The two arguments of one relation must not overlap, but Arg1 is not required to precede Arg2.

## PdtbRelation

- `relation_id`: unique identity.
- `relation_type`: one of the seven PDTB-3 types.
- `arg1`, `arg2`: required binary arguments.
- `senses`: unique canonical PDTB-3 leaves, required only for sense-bearing types.
- `connective_spans`: exact source evidence for Explicit.
- `inferred_connectives`: non-empty proposed connectives for Implicit.
- `alternative_lexicalization_spans`: exact source evidence for AltLex and AltLexC.

Type-specific validation forbids evidence in the wrong field and forbids senses for EntRel, Hypophora, and NoRel.

## PdtbAnalysis

- `relations`: ordered relation collection, including a valid empty list.

Relation IDs are unique. `validate_source(source)` proves every quoted span against the source.
Validated relation, argument, sense, and evidence collections are immutable internally and
serialize as ordinary JSON arrays.

## Native payload

The payload preserves relation type, Arg1/Arg2, all spans, all senses, and extraction evidence without conversion to another discourse formalism.

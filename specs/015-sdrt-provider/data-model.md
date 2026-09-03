# Data Model: SDRT Provider

## ElementaryDiscourseUnit

- `unit_id`: unique snake-style identity.
- `text`: non-empty exact source slice.
- `start`, `end`: zero-based half-open character offsets; `start < end`.

EDUs are strictly ordered and non-overlapping by their offsets.

## ComplexDiscourseUnit

- `unit_id`: unique across EDUs and CDUs.
- `members`: at least two unique EDU/CDU identities.

Every member resolves. Nested membership is acyclic. A CDU becomes completed when all of its transitive EDU members have been introduced.

## SdrtRelation

- `relation_id`: unique identity.
- `source_id`, `target_id`: distinct resolving discourse-unit identities.
- `label`: non-empty relation label.
- `structural_type`: `coordinating` or `subordinating`.

The directed relation graph is acyclic. The same ordered pair may carry multiple compatible labels, but never both structural classes.

## SdrtAnalysis

- `edus`: one or more EDUs.
- `cdus`: zero or more CDUs.
- `relations`: zero or more SDRT relations.

Validation derives reference integrity, acyclicity, connectivity, and right-frontier compliance. `validate_source(source)` additionally proves every EDU quote is the exact source slice.

## Native payload

The payload contains the ordered EDUs, CDUs, relations, counts, and extraction evidence. It does not flatten CDU scope or relabel structural types.

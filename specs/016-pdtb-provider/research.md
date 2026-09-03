# Research: PDTB Provider

## Primary authority

The Penn Discourse Treebank 3.0 Annotation Manual by Webber, Prasad, Lee, and Joshi is the contract authority: <https://catalog.ldc.upenn.edu/docs/LDC2019T05/PDTB3-Annotation-Manual.pdf>.

The LDC release page confirms the 2019 release, stand-off annotation, and corrected post-release corpus counts: <https://catalog.ldc.upenn.edu/LDC2019T05>.

## Decisions

### Preserve all relation types

**Decision**: Close relation type to Explicit, Implicit, AltLex, AltLexC, EntRel, Hypophora, or NoRel.

**Rationale**: The manual's PDTB-3 distribution and definitions include all seven. Omitting AltLexC or Hypophora would silently implement PDTB-2-era coverage.

### Preserve the exact PDTB-3 sense hierarchy

**Decision**: Ship a closed enum of every leaf in Table 1, including directional and belief/speech-act variants. Permit multiple unique senses on one relation.

**Rationale**: The manual explicitly permits multiple senses and distinguishes asymmetric directions at level 3.

### Enforce type-specific evidence

**Decision**: Explicit uses source connective spans; Implicit uses inferred connective text; AltLex/AltLexC use exact source evidence; EntRel/Hypophora/NoRel carry neither evidence nor senses.

**Rationale**: These differences are the semantic reason the relation types exist.

### Preserve argument labels independently of source order

**Decision**: Arg1/Arg2 are named fields and their spans are not globally sorted against each other.

**Rationale**: PDTB-3 labels inter-sentential/coordinating arguments by position but labels intra-sentential subordinating structures syntactically, with the subordinate structure as Arg2.

### Use exact local offsets

**Decision**: The API uses Python Unicode character offsets and proves each quote against the submitted source.

**Rationale**: It preserves the stand-off principle without pretending the API has the corpus file's byte-offset context.

## Rejected alternatives

- Reusing an RST/SDRT edge type: erases PDTB relation type and connective grounding.
- Free-form sense strings: allows stale, misspelled, or invented labels.
- Treating Hypophora as a sense: the manual defines it as a relation type without a connective or sense.

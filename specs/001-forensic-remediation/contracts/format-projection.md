# Format Projection Contract

For Docling 1.2, DocLang 1.1, and Markdown 1.1 envelopes:

1. Every EDU object requires `id`, `text`, `char_span`, `edu_span`, and its format source reference.
2. Every relation object requires `id`, `kind`, `text`, `char_span`, `edu_span`, source/target IDs,
   relation, and nuclearity/direction as applicable.
3. `char_span` uses zero-based half-open source coordinates and must satisfy
   `text == source_text[start:end]`.
4. `edu_span` uses one-based inclusive leaf ordinals. Leaves have `(n,n)`; internal nodes cover the
   minimum/maximum ordinal of all descendant leaves.
5. Node IDs are opaque identities and MUST NOT be interpreted as EDU ordinals.
6. `to_format_analysis()` and conversion to canonical `RstAnalysis` consume the same shared
   authoritative projection.
7. Cache identity includes format, envelope schema, source bytes, normalized source basename, parser
   identity, inventory, model revision, and every behavior-affecting option.
8. Pre-bump cache records cannot deserialize as current hits.

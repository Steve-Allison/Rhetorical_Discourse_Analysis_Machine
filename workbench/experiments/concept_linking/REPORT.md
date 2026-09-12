# Docling NLP 1.4.0 evaluation

Recommendation: keep Docling NLP out of production linking. On this fixed test set,
term extraction lowered canonical candidate recall from 14/14 to 5/14. It added one
valid unknown phrase, but no additional correctly linked Central concept. Unknown-phrase
suggestions may merit a separate curation experiment; this result does not justify adoption.

## Fixed inputs and method

`gold.json` was written and its SHA-256 frozen in `gold.sha256` before either method ran.
It contains 12 synthetic Adobe, learning, visual and narrative passages, with 15 annotated
occurrences (14 mapped, one deliberately unknown). It includes literal scaffolding as a
negative, multiple meanings, substring boundaries, repeated mentions, combining accents,
an accented name, an emoji, and whitespace changes. Expected annotations were authored
separately from extractor outputs; this was not an independent human annotation study.
The sample is too small and synthetic to estimate production corpus accuracy.

Both methods use the identical shared `ContentInventory` surfaces in `prepared.json`.
The baseline scans Central directly. The primary experiment resolves occurrence-level
`term` extraction outputs with the same linker. An additional, explicitly diagnostic
terms-plus-names run investigates named products classified as `name/person-name` by
upstream. It is not a replacement primary experiment selected after seeing results.
No hashes or suffix-derived relationships are interpreted as canonical IDs or edges.

Scoring uses exact occurrence ranges. Nested lexical subterms absent from the gold count
as spurious predictions, even where their words have an independent ontology sense.
A correct candidate inclusion means the annotated ID occurs among candidates, not that
ambiguity has been semantically resolved. All occurrences are retained in `metrics.json`.

## Measurements

| Measure | Direct Central | NLP terms | Terms + names diagnostic |
|---|---:|---:|---:|
| Predicted occurrences | 25 | 24 | 33 |
| Correct exact occurrences | 14 | 6 | 14 |
| Mention precision | 56.0% | 25.0% | 42.4% |
| Mention recall | 93.3% | 40.0% | 93.3% |
| Correct canonical inclusion | 14/14 | 5/14 | 13/14 |
| Ambiguous occurrences | 3 | 1 | 1 |
| Spurious occurrences | 11 | 18 | 19 |
| Non-gold canonical candidates | 17 | 3 | 3 |
| Unmapped extracted occurrences | 0 | 18 | 19 |
| Additional valid occurrences | 0 | 1 | 1 |
| Execution seconds, excluding initialization | 2.458 | 2.425 | 2.461 |

The additional occurrence is the deliberately unknown phrase “quantum banana tutoring”.
Direct matching never claims complete coverage of unknown concepts. Baseline precision
also shows why a lexical candidate must never automatically become a CSM binding.

Peak process RSS on this macOS host was 132,202,496 bytes for the baseline and
618,545,152 bytes for the isolated NLP process. NLP initialization took 0.889 seconds.
These are single-run process high-water marks, not isolated per-model allocations;
OS caches and concurrent machine activity affect timing. Extraction and deterministic
resolution time are included for the NLP methods, while initialization/downloads are not.

## Offset fidelity

All 33 retained occurrences were checked against actual upstream text. Upstream `char_i`
and `char_j` are UTF-8 byte offsets: eight cases differ from Python character offsets.
For example, the emoji/accent prefix places Adobe Analytics at byte 18 but character 14.
The adapter decodes byte prefixes and slices strictly, then verifies the original quote.
One newline becomes a space upstream. This is accepted only after a full-text check proves
position-preserving whitespace substitution; any length-changing or other normalization
raises an error. No offset guessing or fuzzy reconstruction is used.

## Isolation and reproduction

The separate `pixi.toml`/`pixi.lock` pins released `docling-nlp==1.4.0` with Python 3.14.
Installation succeeded with its own dependency solution, including the older pandas/Rich
requirements. RDAM's production requirements were not downgraded or extended.
The first extraction downloads upstream pretrained resources through the package helper;
`extracted.json` records their hashes, package version, native outputs and timing.
Subsequent runs use those installed resources. Initial installation requires network access;
production deterministic linking does not.

From the RDAM root:

```sh
pixi run --locked python workbench/experiments/concept_linking/prepare.py
pixi run --manifest-path workbench/experiments/concept_linking/pixi.toml --locked extract
pixi run --locked python workbench/experiments/concept_linking/score.py
```

Changing `gold.json` without its frozen digest fails. The scorer rejects differing gold
or ontology identities. Results identify Central 4.0.0 with digest
`5acb0b5d2815471bad2478991410a90cb4b913c45a28ea482a47cf6f5a4761f2`.
The baseline was rerun after removing incidental PyTorch imports; NLP output and frozen
annotations were unchanged. Current measurements are in `metrics.json`.

Upstream: [released project](https://pypi.org/project/docling-nlp/1.4.0/),
[source](https://github.com/docling-project/docling-nlp).

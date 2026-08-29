"""Multilingual discourse connective lexical inventories mapped to Central ontology concepts."""

from dataclasses import dataclass

from isanlp_rst.contracts.enums import NuclearityPatternEnum


@dataclass(frozen=True, slots=True)
class MarkerRule:
    """A discourse connective rule mapping lexical cues to canonical relation concepts."""

    cue: str
    coarse_concept: str
    fine_label: str
    default_nuclearity: NuclearityPatternEnum
    is_multiword: bool = False


# Canonical multilingual connective inventories
MULTILINGUAL_MARKER_RULES: dict[str, tuple[MarkerRule, ...]] = {
    "en": (
        # Contrast / Adversative
        MarkerRule("however", "Contrast", "contrast", NuclearityPatternEnum.NS),
        MarkerRule("nevertheless", "Contrast", "contrast", NuclearityPatternEnum.NS),
        MarkerRule("nonetheless", "Contrast", "contrast", NuclearityPatternEnum.NS),
        MarkerRule("in contrast", "Contrast", "contrast", NuclearityPatternEnum.NS, is_multiword=True),
        MarkerRule("on the other hand", "Contrast", "contrast", NuclearityPatternEnum.NS, is_multiword=True),
        MarkerRule("on the contrary", "Contrast", "antithesis", NuclearityPatternEnum.NS, is_multiword=True),
        MarkerRule("although", "Contrast", "concession", NuclearityPatternEnum.SN),
        MarkerRule("even though", "Contrast", "concession", NuclearityPatternEnum.SN, is_multiword=True),
        MarkerRule("even if", "Contrast", "concession", NuclearityPatternEnum.SN, is_multiword=True),
        MarkerRule("despite", "Contrast", "concession", NuclearityPatternEnum.SN),
        MarkerRule("in spite of", "Contrast", "concession", NuclearityPatternEnum.SN, is_multiword=True),
        MarkerRule("whereas", "Contrast", "contrast", NuclearityPatternEnum.NN),
        MarkerRule("while", "Contrast", "contrast", NuclearityPatternEnum.SN),
        MarkerRule("yet", "Contrast", "contrast", NuclearityPatternEnum.NS),
        MarkerRule("but", "Contrast", "contrast", NuclearityPatternEnum.NS),
        MarkerRule("conversely", "Contrast", "contrast", NuclearityPatternEnum.NS),
        # Cause / Causal
        MarkerRule("as a result", "Cause", "result", NuclearityPatternEnum.NS, is_multiword=True),
        MarkerRule("consequently", "Cause", "result", NuclearityPatternEnum.NS),
        MarkerRule("therefore", "Cause", "result", NuclearityPatternEnum.NS),
        MarkerRule("thus", "Cause", "result", NuclearityPatternEnum.NS),
        MarkerRule("hence", "Cause", "result", NuclearityPatternEnum.NS),
        MarkerRule("because", "Cause", "cause", NuclearityPatternEnum.SN),
        MarkerRule("due to", "Cause", "cause", NuclearityPatternEnum.SN, is_multiword=True),
        MarkerRule("owing to", "Cause", "cause", NuclearityPatternEnum.SN, is_multiword=True),
        MarkerRule("for this reason", "Cause", "result", NuclearityPatternEnum.NS, is_multiword=True),
        # Condition / Contingency
        MarkerRule("if", "Condition", "condition", NuclearityPatternEnum.SN),
        MarkerRule("unless", "Condition", "condition", NuclearityPatternEnum.SN),
        MarkerRule("provided that", "Condition", "condition", NuclearityPatternEnum.SN, is_multiword=True),
        MarkerRule("as long as", "Condition", "condition", NuclearityPatternEnum.SN, is_multiword=True),
        MarkerRule("assuming that", "Condition", "condition", NuclearityPatternEnum.SN, is_multiword=True),
        MarkerRule("in case", "Condition", "contingency", NuclearityPatternEnum.SN, is_multiword=True),
        MarkerRule("otherwise", "Condition", "otherwise", NuclearityPatternEnum.NS),
        # Explanation / Evidence
        MarkerRule("for example", "Explanation", "evidence", NuclearityPatternEnum.NS, is_multiword=True),
        MarkerRule("for instance", "Explanation", "evidence", NuclearityPatternEnum.NS, is_multiword=True),
        MarkerRule("specifically", "Elaboration", "elaboration-additional", NuclearityPatternEnum.NS),
        MarkerRule("in fact", "Explanation", "evidence", NuclearityPatternEnum.NS, is_multiword=True),
        MarkerRule("indeed", "Explanation", "evidence", NuclearityPatternEnum.NS),
        MarkerRule("namely", "Elaboration", "elaboration-additional", NuclearityPatternEnum.NS),
        MarkerRule("that is", "Elaboration", "elaboration-additional", NuclearityPatternEnum.NS, is_multiword=True),
        # Enablement / Purpose
        MarkerRule("in order to", "Enablement", "purpose", NuclearityPatternEnum.NS, is_multiword=True),
        MarkerRule("so that", "Enablement", "purpose", NuclearityPatternEnum.NS, is_multiword=True),
        MarkerRule("so as to", "Enablement", "purpose", NuclearityPatternEnum.NS, is_multiword=True),
        MarkerRule("to that end", "Enablement", "purpose", NuclearityPatternEnum.NS, is_multiword=True),
        # Temporal / Sequence
        MarkerRule("firstly", "Temporal", "sequence", NuclearityPatternEnum.NN),
        MarkerRule("secondly", "Temporal", "sequence", NuclearityPatternEnum.NN),
        MarkerRule("subsequently", "Temporal", "sequence", NuclearityPatternEnum.NN),
        MarkerRule("afterwards", "Temporal", "sequence", NuclearityPatternEnum.NN),
        MarkerRule("after that", "Temporal", "sequence", NuclearityPatternEnum.NN, is_multiword=True),
        MarkerRule("meanwhile", "Temporal", "temporal-same-time", NuclearityPatternEnum.NN),
        MarkerRule("simultaneously", "Temporal", "temporal-same-time", NuclearityPatternEnum.NN),
        MarkerRule("as soon as", "Temporal", "temporal-before", NuclearityPatternEnum.SN, is_multiword=True),
        # Joint / List
        MarkerRule("furthermore", "Joint", "list", NuclearityPatternEnum.NN),
        MarkerRule("moreover", "Joint", "list", NuclearityPatternEnum.NN),
        MarkerRule("in addition", "Joint", "list", NuclearityPatternEnum.NN, is_multiword=True),
        MarkerRule("additionally", "Joint", "list", NuclearityPatternEnum.NN),
        MarkerRule("besides", "Joint", "list", NuclearityPatternEnum.NN),
        # Comparison
        MarkerRule("similarly", "Comparison", "comparison", NuclearityPatternEnum.NN),
        MarkerRule("likewise", "Comparison", "comparison", NuclearityPatternEnum.NN),
    ),
    "ru": (
        # Contrast / Adversative
        MarkerRule("однако", "Contrast", "contrast", NuclearityPatternEnum.NS),
        MarkerRule("тем не менее", "Contrast", "contrast", NuclearityPatternEnum.NS, is_multiword=True),
        MarkerRule("все же", "Contrast", "contrast", NuclearityPatternEnum.NS, is_multiword=True),
        MarkerRule("напротив", "Contrast", "antithesis", NuclearityPatternEnum.NS),
        MarkerRule("хотя", "Contrast", "concession", NuclearityPatternEnum.SN),
        MarkerRule("несмотря на то что", "Contrast", "concession", NuclearityPatternEnum.SN, is_multiword=True),
        MarkerRule("в то время как", "Contrast", "contrast", NuclearityPatternEnum.NN, is_multiword=True),
        MarkerRule("но", "Contrast", "contrast", NuclearityPatternEnum.NS),
        MarkerRule("а", "Contrast", "contrast", NuclearityPatternEnum.NS),
        # Cause / Causal
        MarkerRule("в результате", "Cause", "result", NuclearityPatternEnum.NS, is_multiword=True),
        MarkerRule("следовательно", "Cause", "result", NuclearityPatternEnum.NS),
        MarkerRule("поэтому", "Cause", "result", NuclearityPatternEnum.NS),
        MarkerRule("таким образом", "Cause", "result", NuclearityPatternEnum.NS, is_multiword=True),
        MarkerRule("потому что", "Cause", "cause", NuclearityPatternEnum.SN, is_multiword=True),
        MarkerRule("так как", "Cause", "cause", NuclearityPatternEnum.SN, is_multiword=True),
        MarkerRule("из-за того что", "Cause", "cause", NuclearityPatternEnum.SN, is_multiword=True),
        # Condition / Contingency
        MarkerRule("если", "Condition", "condition", NuclearityPatternEnum.SN),
        MarkerRule("если бы", "Condition", "condition", NuclearityPatternEnum.SN, is_multiword=True),
        MarkerRule("при условии что", "Condition", "condition", NuclearityPatternEnum.SN, is_multiword=True),
        MarkerRule("в случае если", "Condition", "condition", NuclearityPatternEnum.SN, is_multiword=True),
        MarkerRule("иначе", "Condition", "otherwise", NuclearityPatternEnum.NS),
        # Explanation / Evidence
        MarkerRule("например", "Explanation", "evidence", NuclearityPatternEnum.NS),
        MarkerRule("к примеру", "Explanation", "evidence", NuclearityPatternEnum.NS, is_multiword=True),
        MarkerRule("в частности", "Elaboration", "elaboration-additional", NuclearityPatternEnum.NS, is_multiword=True),
        MarkerRule("на самом деле", "Explanation", "evidence", NuclearityPatternEnum.NS, is_multiword=True),
        MarkerRule("действительно", "Explanation", "evidence", NuclearityPatternEnum.NS),
        MarkerRule("то есть", "Elaboration", "elaboration-additional", NuclearityPatternEnum.NS, is_multiword=True),
        # Enablement / Purpose
        MarkerRule("для того чтобы", "Enablement", "purpose", NuclearityPatternEnum.NS, is_multiword=True),
        MarkerRule("чтобы", "Enablement", "purpose", NuclearityPatternEnum.NS),
        MarkerRule("с целью", "Enablement", "purpose", NuclearityPatternEnum.NS, is_multiword=True),
        # Temporal / Sequence
        MarkerRule("во-первых", "Temporal", "sequence", NuclearityPatternEnum.NN),
        MarkerRule("во-вторых", "Temporal", "sequence", NuclearityPatternEnum.NN),
        MarkerRule("затем", "Temporal", "sequence", NuclearityPatternEnum.NN),
        MarkerRule("после этого", "Temporal", "sequence", NuclearityPatternEnum.NN, is_multiword=True),
        MarkerRule("в то же время", "Temporal", "temporal-same-time", NuclearityPatternEnum.NN, is_multiword=True),
        MarkerRule("одновременно", "Temporal", "temporal-same-time", NuclearityPatternEnum.NN),
        MarkerRule("как только", "Temporal", "temporal-before", NuclearityPatternEnum.SN, is_multiword=True),
        # Joint / List
        MarkerRule("кроме того", "Joint", "list", NuclearityPatternEnum.NN, is_multiword=True),
        MarkerRule("более того", "Joint", "list", NuclearityPatternEnum.NN, is_multiword=True),
        MarkerRule("также", "Joint", "list", NuclearityPatternEnum.NN),
        MarkerRule("к тому же", "Joint", "list", NuclearityPatternEnum.NN, is_multiword=True),
    ),
    "es": (
        # Contrast
        MarkerRule("sin embargo", "Contrast", "contrast", NuclearityPatternEnum.NS, is_multiword=True),
        MarkerRule("no obstante", "Contrast", "contrast", NuclearityPatternEnum.NS, is_multiword=True),
        MarkerRule("por el contrario", "Contrast", "antithesis", NuclearityPatternEnum.NS, is_multiword=True),
        MarkerRule("aunque", "Contrast", "concession", NuclearityPatternEnum.SN),
        MarkerRule("a pesar de que", "Contrast", "concession", NuclearityPatternEnum.SN, is_multiword=True),
        MarkerRule("pero", "Contrast", "contrast", NuclearityPatternEnum.NS),
        # Cause
        MarkerRule("por lo tanto", "Cause", "result", NuclearityPatternEnum.NS, is_multiword=True),
        MarkerRule("en consecuencia", "Cause", "result", NuclearityPatternEnum.NS, is_multiword=True),
        MarkerRule("por consiguiente", "Cause", "result", NuclearityPatternEnum.NS, is_multiword=True),
        MarkerRule("porque", "Cause", "cause", NuclearityPatternEnum.SN),
        MarkerRule("ya que", "Cause", "cause", NuclearityPatternEnum.SN, is_multiword=True),
        # Condition
        MarkerRule("si", "Condition", "condition", NuclearityPatternEnum.SN),
        MarkerRule("a menos que", "Condition", "condition", NuclearityPatternEnum.SN, is_multiword=True),
        MarkerRule("siempre que", "Condition", "condition", NuclearityPatternEnum.SN, is_multiword=True),
        # Explanation / Purpose / Joint
        MarkerRule("por ejemplo", "Explanation", "evidence", NuclearityPatternEnum.NS, is_multiword=True),
        MarkerRule("para que", "Enablement", "purpose", NuclearityPatternEnum.NS, is_multiword=True),
        MarkerRule("con el fin de", "Enablement", "purpose", NuclearityPatternEnum.NS, is_multiword=True),
        MarkerRule("además", "Joint", "list", NuclearityPatternEnum.NN),
        MarkerRule("asimismo", "Joint", "list", NuclearityPatternEnum.NN),
        MarkerRule("después", "Temporal", "sequence", NuclearityPatternEnum.NN),
    ),
    "de": (
        # Contrast
        MarkerRule("jedoch", "Contrast", "contrast", NuclearityPatternEnum.NS),
        MarkerRule("dennoch", "Contrast", "contrast", NuclearityPatternEnum.NS),
        MarkerRule("obwohl", "Contrast", "concession", NuclearityPatternEnum.SN),
        MarkerRule("aber", "Contrast", "contrast", NuclearityPatternEnum.NS),
        # Cause
        MarkerRule("deshalb", "Cause", "result", NuclearityPatternEnum.NS),
        MarkerRule("daher", "Cause", "result", NuclearityPatternEnum.NS),
        MarkerRule("weil", "Cause", "cause", NuclearityPatternEnum.SN),
        MarkerRule("da", "Cause", "cause", NuclearityPatternEnum.SN),
        # Condition
        MarkerRule("wenn", "Condition", "condition", NuclearityPatternEnum.SN),
        MarkerRule("falls", "Condition", "condition", NuclearityPatternEnum.SN),
        # Explanation / Purpose / Joint
        MarkerRule("beispielsweise", "Explanation", "evidence", NuclearityPatternEnum.NS),
        MarkerRule("zum beispiel", "Explanation", "evidence", NuclearityPatternEnum.NS, is_multiword=True),
        MarkerRule("um zu", "Enablement", "purpose", NuclearityPatternEnum.NS, is_multiword=True),
        MarkerRule("damit", "Enablement", "purpose", NuclearityPatternEnum.NS),
        MarkerRule("außerdem", "Joint", "list", NuclearityPatternEnum.NN),
        MarkerRule("ferner", "Joint", "list", NuclearityPatternEnum.NN),
    ),
    "fr": (
        # Contrast
        MarkerRule("cependant", "Contrast", "contrast", NuclearityPatternEnum.NS),
        MarkerRule("néanmoins", "Contrast", "contrast", NuclearityPatternEnum.NS),
        MarkerRule("bien que", "Contrast", "concession", NuclearityPatternEnum.SN, is_multiword=True),
        MarkerRule("mais", "Contrast", "contrast", NuclearityPatternEnum.NS),
        # Cause
        MarkerRule("par conséquent", "Cause", "result", NuclearityPatternEnum.NS, is_multiword=True),
        MarkerRule("donc", "Cause", "result", NuclearityPatternEnum.NS),
        MarkerRule("parce que", "Cause", "cause", NuclearityPatternEnum.SN, is_multiword=True),
        MarkerRule("puisque", "Cause", "cause", NuclearityPatternEnum.SN),
        # Condition
        MarkerRule("si", "Condition", "condition", NuclearityPatternEnum.SN),
        MarkerRule("à condition que", "Condition", "condition", NuclearityPatternEnum.SN, is_multiword=True),
        # Explanation / Purpose / Joint
        MarkerRule("par exemple", "Explanation", "evidence", NuclearityPatternEnum.NS, is_multiword=True),
        MarkerRule("afin de", "Enablement", "purpose", NuclearityPatternEnum.NS, is_multiword=True),
        MarkerRule("pour que", "Enablement", "purpose", NuclearityPatternEnum.NS, is_multiword=True),
        MarkerRule("de plus", "Joint", "list", NuclearityPatternEnum.NN, is_multiword=True),
        MarkerRule("en outre", "Joint", "list", NuclearityPatternEnum.NN, is_multiword=True),
    ),
    "zh": (
        # Contrast
        MarkerRule("但是", "Contrast", "contrast", NuclearityPatternEnum.NS),
        MarkerRule("然而", "Contrast", "contrast", NuclearityPatternEnum.NS),
        MarkerRule("虽然", "Contrast", "concession", NuclearityPatternEnum.SN),
        MarkerRule("尽管", "Contrast", "concession", NuclearityPatternEnum.SN),
        # Cause
        MarkerRule("因此", "Cause", "result", NuclearityPatternEnum.NS),
        MarkerRule("所以", "Cause", "result", NuclearityPatternEnum.NS),
        MarkerRule("因为", "Cause", "cause", NuclearityPatternEnum.SN),
        # Condition
        MarkerRule("如果", "Condition", "condition", NuclearityPatternEnum.SN),
        MarkerRule("只要", "Condition", "condition", NuclearityPatternEnum.SN),
        # Explanation / Purpose / Joint
        MarkerRule("例如", "Explanation", "evidence", NuclearityPatternEnum.NS),
        MarkerRule("比如", "Explanation", "evidence", NuclearityPatternEnum.NS),
        MarkerRule("为了", "Enablement", "purpose", NuclearityPatternEnum.NS),
        MarkerRule("此外", "Joint", "list", NuclearityPatternEnum.NN),
        MarkerRule("而且", "Joint", "list", NuclearityPatternEnum.NN),
    ),
    "pt": (
        MarkerRule("no entanto", "Contrast", "contrast", NuclearityPatternEnum.NS, is_multiword=True),
        MarkerRule("portanto", "Cause", "result", NuclearityPatternEnum.NS),
        MarkerRule("se", "Condition", "condition", NuclearityPatternEnum.SN),
        MarkerRule("por exemplo", "Explanation", "evidence", NuclearityPatternEnum.NS, is_multiword=True),
        MarkerRule("além disso", "Joint", "list", NuclearityPatternEnum.NN, is_multiword=True),
    ),
    "nl": (
        MarkerRule("echter", "Contrast", "contrast", NuclearityPatternEnum.NS),
        MarkerRule("daarom", "Cause", "result", NuclearityPatternEnum.NS),
        MarkerRule("als", "Condition", "condition", NuclearityPatternEnum.SN),
        MarkerRule("bijvoorbeeld", "Explanation", "evidence", NuclearityPatternEnum.NS),
        MarkerRule("bovendien", "Joint", "list", NuclearityPatternEnum.NN),
    ),
    "eu": (
        MarkerRule("ordea", "Contrast", "contrast", NuclearityPatternEnum.NS),
        MarkerRule("beraz", "Cause", "result", NuclearityPatternEnum.NS),
        MarkerRule("baldin eta", "Condition", "condition", NuclearityPatternEnum.SN, is_multiword=True),
        MarkerRule("adibidez", "Explanation", "evidence", NuclearityPatternEnum.NS),
        MarkerRule("gainera", "Joint", "list", NuclearityPatternEnum.NN),
    ),
}

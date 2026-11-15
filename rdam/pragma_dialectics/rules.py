"""The 10 Pragma-Dialectical Rules for a Critical Discussion (van Eemeren & Grootendorst 2004)."""

from dataclasses import dataclass
from typing import Final, Literal

type DiscussionStage = Literal["confrontation", "opening", "argumentation", "concluding"]

type CriticalDiscussionRuleId = Literal[
    "rule_1_freedom",
    "rule_2_burden_of_proof",
    "rule_3_standpoint",
    "rule_4_relevance",
    "rule_5_unexpressed_premise",
    "rule_6_starting_point",
    "rule_7_validity",
    "rule_8_argument_scheme",
    "rule_9_closure",
    "rule_10_usage",
]


@dataclass(frozen=True, slots=True)
class CriticalDiscussionRule:
    rule_id: CriticalDiscussionRuleId
    number: int
    title: str
    primary_stages: tuple[DiscussionStage, ...]
    norm: str
    recognized_fallacies: frozenset[str]


CRITICAL_DISCUSSION_RULES: Final[dict[CriticalDiscussionRuleId, CriticalDiscussionRule]] = {
    "rule_1_freedom": CriticalDiscussionRule(
        rule_id="rule_1_freedom",
        number=1,
        title="Freedom Rule",
        primary_stages=("confrontation",),
        norm="Parties must not prevent each other from advancing standpoints or casting doubt on standpoints.",
        recognized_fallacies=frozenset(
            {"ad_hominem", "ad_baculum", "ad_misericordiam_confrontation", "declaring_standpoint_sacrosanct"}
        ),
    ),
    "rule_2_burden_of_proof": CriticalDiscussionRule(
        rule_id="rule_2_burden_of_proof",
        number=2,
        title="Burden-of-Proof Rule",
        primary_stages=("opening",),
        norm="A party who advances a standpoint is obliged to defend it if asked to do so.",
        recognized_fallacies=frozenset(
            {"shifting_burden_of_proof", "evading_burden_of_proof", "immunizing_standpoint"}
        ),
    ),
    "rule_3_standpoint": CriticalDiscussionRule(
        rule_id="rule_3_standpoint",
        number=3,
        title="Standpoint Rule",
        primary_stages=("confrontation", "argumentation"),
        norm="A party's attack on a standpoint must relate to the standpoint that has indeed been advanced by the other party.",
        recognized_fallacies=frozenset({"straw_man", "distorting_standpoint", "fictitious_standpoint"}),
    ),
    "rule_4_relevance": CriticalDiscussionRule(
        rule_id="rule_4_relevance",
        number=4,
        title="Relevance Rule",
        primary_stages=("argumentation",),
        norm="A party may defend a standpoint only by advancing argumentation relating to that standpoint.",
        recognized_fallacies=frozenset(
            {"ignoratio_elenchi", "irrelevant_argumentation", "non_argumentative_means_of_persuasion"}
        ),
    ),
    "rule_5_unexpressed_premise": CriticalDiscussionRule(
        rule_id="rule_5_unexpressed_premise",
        number=5,
        title="Unexpressed-Premise Rule",
        primary_stages=("argumentation",),
        norm="A party may not falsely present something as a premise left unexpressed by the other party or deny a premise left implicit by themselves.",
        recognized_fallacies=frozenset({"magnifying_unexpressed_premise", "denying_unexpressed_premise"}),
    ),
    "rule_6_starting_point": CriticalDiscussionRule(
        rule_id="rule_6_starting_point",
        number=6,
        title="Starting-Point Rule",
        primary_stages=("opening", "argumentation"),
        norm="A party may not falsely present a premise as an accepted starting point or deny an established starting point.",
        recognized_fallacies=frozenset(
            {"petitio_principii", "complex_question", "falsely_presenting_starting_point", "denying_accepted_starting_point"}
        ),
    ),
    "rule_7_validity": CriticalDiscussionRule(
        rule_id="rule_7_validity",
        number=7,
        title="Validity Rule",
        primary_stages=("argumentation",),
        norm="Reasoning that in an argumentation is presented as formally conclusive may not contain logical invalidity.",
        recognized_fallacies=frozenset(
            {"affirming_the_consequent", "denying_the_antecedent", "division", "composition", "formal_invalidity"}
        ),
    ),
    "rule_8_argument_scheme": CriticalDiscussionRule(
        rule_id="rule_8_argument_scheme",
        number=8,
        title="Argument-Scheme Rule",
        primary_stages=("argumentation",),
        norm="A standpoint may not be regarded as conclusively defended if the defence does not take place by means of an appropriate argument scheme that is correctly applied.",
        recognized_fallacies=frozenset(
            {
                "ad_verecundiam",
                "ad_populum",
                "hasty_generalization",
                "false_analogy",
                "post_hoc_ergo_propter_hoc",
                "slippery_slope",
                "ad_consequentiam",
            }
        ),
    ),
    "rule_9_closure": CriticalDiscussionRule(
        rule_id="rule_9_closure",
        number=9,
        title="Closure Rule",
        primary_stages=("concluding",),
        norm="A failed defence must result in the protagonist retracting the standpoint, and a conclusive defence must result in the antagonist retracting doubt.",
        recognized_fallacies=frozenset(
            {"ad_ignorantiam", "refusing_to_retract_standpoint", "refusing_to_retract_doubt"}
        ),
    ),
    "rule_10_usage": CriticalDiscussionRule(
        rule_id="rule_10_usage",
        number=10,
        title="Language-Use Rule",
        primary_stages=("confrontation", "opening", "argumentation", "concluding"),
        norm="Parties must not use formulations that are insufficiently clear or confusingly ambiguous.",
        recognized_fallacies=frozenset({"equivocation", "amphiboly", "obscurity", "loaded_vagueness"}),
    ),
}


__all__ = [
    "CRITICAL_DISCUSSION_RULES",
    "CriticalDiscussionRule",
    "CriticalDiscussionRuleId",
    "DiscussionStage",
]

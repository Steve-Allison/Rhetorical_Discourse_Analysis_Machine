"""Coarse scoring is inventory-bound and does not redefine native semantics."""

import pytest

from workbench.evaluation.rst.label_projection import gum_coarse_projection


def test_projection_preserves_compound_inventory_members_and_groups_gold_subtypes() -> None:
    mapping = gum_coarse_projection(
        ("adversative-concession", "adversative-contrast", "same-unit"),
        ("adversative_NS", "adversative_NN", "same-unit_NN"),
    )
    assert dict(mapping) == {
        "adversative": "adversative", "same-unit": "same-unit",
        "adversative-concession": "adversative", "adversative-contrast": "adversative",
    }


@pytest.mark.parametrize("inventory", [(), ("cause",), ("cause_SS",), ("cause_NS", "Cause_NS")])
def test_invalid_model_inventory_is_rejected(inventory: tuple[str, ...]) -> None:
    with pytest.raises(ValueError, match="inventory|class"):
        gum_coarse_projection(("causal-cause",), inventory)


def test_unknown_gold_family_is_not_silently_passed_through() -> None:
    with pytest.raises(ValueError, match="no supported GUM coarse family"):
        gum_coarse_projection(("unknown-relation",), ("causal_NS",))


def test_projection_does_not_rewrite_unsupported_nuclearity() -> None:
    # The model lacks topic_NS. Mapping a relation family must not turn it into
    # contingency or alter gold nuclearity to make it fit a trained class.
    mapping = gum_coarse_projection(("topic-question",), ("topic_SN",))
    assert mapping["topic-question"] == "topic"


def test_unirst_harmonization_requires_explicit_native_alias() -> None:
    labels = ("Condition_NS", "Condition_SN")
    with pytest.raises(ValueError, match="no supported GUM coarse family"):
        gum_coarse_projection(("contingency-condition",), labels)
    mapping = gum_coarse_projection(
        ("contingency-condition",), labels, native_aliases={"condition": "contingency"},
    )
    assert mapping["condition"] == mapping["contingency-condition"] == "contingency"
    with pytest.raises(ValueError, match="absent"):
        gum_coarse_projection((), labels, native_aliases={"unknown": "contingency"})

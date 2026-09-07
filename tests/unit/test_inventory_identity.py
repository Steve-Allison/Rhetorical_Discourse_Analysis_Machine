"""Named inventories resolve to their existing classifier position."""

import pytest

from rdam.rst.universal_parser.inventory import resolve_inventory_index


@pytest.mark.parametrize("requested", ("GUM", "gum", " GUM "))
def test_mixed_case_inventory_retains_ordinal(requested: str) -> None:
    names = ["RuRSTB", "GUM", "RST-DT-tr", "GUM10-tr"]
    assert resolve_inventory_index(names, requested) == 1
    assert names == ["RuRSTB", "GUM", "RST-DT-tr", "GUM10-tr"]


def test_unknown_inventory_is_not_aliased_to_a_different_scheme() -> None:
    with pytest.raises(ValueError, match="Unknown relinventory"):
        resolve_inventory_index(["RuRSTB", "GUM"], "eng.erst.gum")


def test_ambiguous_inventory_does_not_choose_a_classifier_silently() -> None:
    with pytest.raises(ValueError, match="Ambiguous relinventory"):
        resolve_inventory_index(["GUM", "gum"], "gum")

"""DMRST ``nucs_and_rels`` must match UniRST ``rpartition`` semantics."""

import pytest

from workbench.archive.legacy_2021.dmrst_parser.src.parser.data import nucs_and_rels as dmrst_nucs
from workbench.archive.legacy_2021.universal_parser.src.parser.data import nucs_and_rels as unirst_nucs


@pytest.mark.parametrize(
    "label",
    [
        "Elaboration_NS",
        "Attribution_SN",
        "Joint_NN",
        "same-unit_NN",
        "restatement-partial_SN",
        "topic-question_SN",
    ],
)
def test_dmrst_nucs_and_rels_matches_unirst(label: str) -> None:
    table = [label]
    assert dmrst_nucs(0, table) == unirst_nucs(0, table)


def test_dmrst_same_unit_keeps_hyphenated_relation_name() -> None:
    nuc_l, nuc_r, rel_l, rel_r = dmrst_nucs(0, ["same-unit_NN"])
    assert (nuc_l, nuc_r) == ("Nucleus", "Nucleus")
    assert (rel_l, rel_r) == ("same-unit", "same-unit")


def test_dmrst_ns_satellite_on_right() -> None:
    nuc_l, nuc_r, rel_l, rel_r = dmrst_nucs(0, ["elaboration_NS"])
    assert nuc_l == "Nucleus"
    assert nuc_r == "Satellite"
    assert rel_l == "span"
    assert rel_r == "elaboration"

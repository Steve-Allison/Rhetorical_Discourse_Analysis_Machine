"""Tests for the RST-tree serialisation helpers (dict + optional pydantic)."""

import json

from isanlp_rst.annotation_rst import DiscourseUnit

from isanlp_rst.utils.serialization import tree_from_dict, tree_to_dict
from isanlp_rst.utils.serialization_pydantic import PydanticDiscourseUnit, RstNode


def _sample_tree() -> DiscourseUnit:
    """A two-leaf RST tree: root (elaboration / NS) over two EDUs."""
    left = DiscourseUnit(id=1, start=0, end=8, text="Left edu.")
    right = DiscourseUnit(id=2, start=10, end=19, text="Right edu.")
    return DiscourseUnit(
        id=3,
        left=left,
        right=right,
        start=0,
        end=19,
        text="Left edu.  Right edu.",
        relation="elaboration",
        nuclearity="NS",
        proba=0.91,
        entropy=0.34,
    )


def test_tree_to_dict_captures_full_field_set() -> None:
    d = tree_to_dict(_sample_tree())
    assert d["id"] == 3
    assert d["relation"] == "elaboration"
    assert d["nuclearity"] == "NS"
    assert d["proba"] == 0.91
    assert d["entropy"] == 0.34  # full field set, not the legacy 7
    assert d["left"]["text"] == "Left edu."
    assert d["right"]["id"] == 2


def test_tree_to_dict_omits_none_and_orig_text() -> None:
    d = tree_to_dict(_sample_tree())
    # leaves carry no proba/entropy -> omitted, not serialised as null
    assert "proba" not in d["left"]
    assert "entropy" not in d["left"]
    # orig_text (the whole-document string) is never serialised per node
    assert "orig_text" not in d
    assert "orig_text" not in d["left"]


def test_tree_to_dict_is_json_serialisable() -> None:
    json.dumps(tree_to_dict(_sample_tree()))  # must not raise


def test_dict_round_trip_is_a_fixpoint() -> None:
    original = tree_to_dict(_sample_tree())
    rebuilt = tree_to_dict(tree_from_dict(original))
    assert rebuilt == original


def test_empty_edges() -> None:
    assert tree_to_dict(None) == {}
    assert tree_from_dict({}) is None


# --- pydantic model (requires the `pydantic` extra) ---


def test_pydantic_discourse_unit_alias_and_round_trip() -> None:
    assert PydanticDiscourseUnit is RstNode
    tree = _sample_tree()
    model = PydanticDiscourseUnit.from_tree(tree)
    assert model is not None
    # model -> DiscourseUnit -> dict must match the direct dict serialisation
    assert tree_to_dict(model.to_tree()) == tree_to_dict(tree)


def test_rstnode_validates_tree_to_dict_output() -> None:
    model = PydanticDiscourseUnit.model_validate(tree_to_dict(_sample_tree()))
    assert model.relation == "elaboration"
    assert model.left is not None and model.left.text == "Left edu."


def test_rstnode_from_none_is_none() -> None:
    assert PydanticDiscourseUnit.from_tree(None) is None
    assert RstNode.from_tree(None) is None


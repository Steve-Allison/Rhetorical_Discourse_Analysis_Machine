"""Unit tests for ``extract_root_tree`` and DMRST relation-table normalize."""

from pathlib import Path

import pytest
from isanlp_rst.annotation_rst import DiscourseUnit

from isanlp_rst.dmrst_parser.predictor import PredictorDMRST
from isanlp_rst.parser import Parser
from isanlp_rst.utils.parse_result import ParseFailedError, extract_root_tree


def test_extract_root_tree_happy_path():
    root = object()
    assert extract_root_tree({"rst": [root]}) is root


def test_extract_root_tree_missing_key():
    with pytest.raises(ParseFailedError, match="missing the 'rst' key"):
        extract_root_tree({"other": []})


def test_extract_root_tree_empty_list():
    with pytest.raises(ParseFailedError, match="empty"):
        extract_root_tree({"rst": []})


def test_extract_root_tree_none_payload():
    with pytest.raises(ParseFailedError, match="is None"):
        extract_root_tree({"rst": None})


def test_extract_root_tree_none_root():
    with pytest.raises(ParseFailedError, match=r"\['rst'\]\[0\] is None"):
        extract_root_tree({"rst": [None]})


def test_extract_root_tree_not_mapping():
    with pytest.raises(ParseFailedError, match="must be a mapping"):
        extract_root_tree([1, 2, 3])


def test_parser_typed_boundary_returns_discourse_unit() -> None:
    class FakePredictor(PredictorDMRST):
        def parse_rst(self, text: str) -> dict[str, list[DiscourseUnit]]:
            return {"rst": [DiscourseUnit(id=1, start=0, end=len(text), text=text)]}

    parser = Parser.__new__(Parser)
    parser.predictor = FakePredictor.__new__(FakePredictor)
    root = parser.parse_tree("Typed boundary.")
    assert isinstance(root, DiscourseUnit)
    assert root.text == "Typed boundary."


def test_dmrst_read_relation_table_strips_blanks(tmp_path: Path):
    path = tmp_path / "relation_table.txt"
    path.write_text("elaboration\n\n  contrast  \n\n", encoding="utf-8")
    assert PredictorDMRST._read_relation_table(str(path)) == [
        "elaboration",
        "contrast",
    ]


def test_dmrst_read_relation_table_empty_raises(tmp_path: Path):
    path = tmp_path / "relation_table.txt"
    path.write_text("\n\n  \n", encoding="utf-8")
    with pytest.raises(ValueError, match="no non-blank labels"):
        PredictorDMRST._read_relation_table(str(path))

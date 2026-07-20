"""Unit tests for ``isanlp_rst.utils.du_converter.DUConverter``.

Focuses on the review-fix contracts: ``fix_segmented_strings`` must
not produce ``i=-1`` / empty wrong segments, and ``_get_child`` must
raise when a constituent span is missing.
"""

from __future__ import annotations

import pytest
from isanlp.annotation_rst import DiscourseUnit

from isanlp_rst.utils.du_converter import DUConverter


def test_fix_segmented_strings_first_token_covers_segment() -> None:
    """When the first gold token already covers the whitespace-stripped
    predicted length, consume that one token — never ``i=-1``."""
    predicted = ["hello"]
    gold = ["hello", "world"]
    fixed = DUConverter.fix_segmented_strings(predicted, gold)
    assert fixed == ["hello"]


def test_fix_segmented_strings_empty_predicted_segment() -> None:
    predicted = ["", "abc"]
    gold = ["a", "b", "c"]
    fixed = DUConverter.fix_segmented_strings(predicted, gold)
    assert len(fixed) == 2
    assert fixed[0] == ""
    assert fixed[1] == "a b c"
    assert "".join(fixed[1].split()) == "abc"


def test_fix_segmented_strings_multi_token() -> None:
    predicted = ["helloworld"]
    gold = ["hello", "world"]
    fixed = DUConverter.fix_segmented_strings(predicted, gold)
    assert fixed == ["hello world"]
    assert "".join(fixed[0].split()) == "helloworld"


def test_get_child_missing_span_raises() -> None:
    """A non-leaf constituent whose span is absent from ``rels`` must
    raise ``ValueError`` instead of returning ``None``."""
    edus = [
        DiscourseUnit(id=0, text="a", start=0, end=1, relation="elementary"),
        DiscourseUnit(id=1, text="b", start=2, end=3, relation="elementary"),
        DiscourseUnit(id=2, text="c", start=4, end=5, relation="elementary"),
    ]
    # Root covers 0..2; left span 0..1 is non-leaf but has no matching rel.
    rels = [
        (0, 1, "elaboration", "NS", 2, 2, 0.0),
    ]
    conv = DUConverter({"tokens": []})
    with pytest.raises(ValueError):
        conv.construct_tree(0, edus, rels)

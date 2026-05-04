"""Tests for the JSON tree serialisers.

These tests do not require ``isanlp`` to be installed — they use a
small stand-in DiscourseUnit implemented as a plain class with the
expected attributes. This keeps the test fast and platform-portable.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from isanlp_rst.utils.serialization import tree_from_dict, tree_to_dict


class _Node:
    """Minimal stand-in for ``isanlp.annotation_rst.DiscourseUnit``."""

    def __init__(
        self,
        id: int,
        relation: str | None = None,
        nuclearity: str | None = None,
        start: int | None = None,
        end: int | None = None,
        text: str | None = None,
        proba: float | None = None,
        left: Any | None = None,
        right: Any | None = None,
    ) -> None:
        self.id = id
        self.relation = relation
        self.nuclearity = nuclearity
        self.start = start
        self.end = end
        self.text = text
        self.proba = proba
        self.left = left
        self.right = right


def _make_simple_tree() -> _Node:
    """A 3-node tree: root with two leaf children."""
    left = _Node(id=1, relation="elementary", start=0, end=10, text="Left text.")
    right = _Node(id=2, relation="elementary", start=11, end=20, text="Right text.")
    return _Node(
        id=0,
        relation="Elaboration",
        nuclearity="NS",
        start=0,
        end=20,
        text="Left text. Right text.",
        proba=0.92,
        left=left,
        right=right,
    )


class TestTreeToDict:
    def test_returns_empty_dict_for_none(self) -> None:
        assert tree_to_dict(None) == {}

    def test_serialises_required_attrs(self) -> None:
        out = tree_to_dict(_Node(id=42, relation="Background", nuclearity="SN"))
        assert out["id"] == 42
        assert out["relation"] == "Background"
        assert out["nuclearity"] == "SN"

    def test_omits_none_attrs(self) -> None:
        # `relation` is None — must not appear in output.
        out = tree_to_dict(_Node(id=1))
        assert "id" in out
        assert "relation" not in out
        assert "left" not in out
        assert "right" not in out

    def test_serialises_recursive_children(self) -> None:
        root = _make_simple_tree()
        out = tree_to_dict(root)
        assert "left" in out
        assert "right" in out
        assert out["left"]["id"] == 1
        assert out["right"]["id"] == 2

    def test_output_is_json_serialisable(self) -> None:
        out = tree_to_dict(_make_simple_tree())
        # Must not raise.
        encoded = json.dumps(out)
        assert len(encoded) > 0


class TestTreeFromDict:
    def test_returns_none_for_empty_dict(self) -> None:
        assert tree_from_dict({}) is None

    def test_falls_back_to_dict_when_isanlp_unavailable(self) -> None:
        """If ``isanlp`` isn't installed, returns the dict unchanged."""
        try:
            import isanlp.annotation_rst  # noqa: F401
            pytest.skip("isanlp is installed; can't exercise the fallback path")
        except ImportError:
            pass
        out = tree_from_dict({"id": 1, "relation": "Elaboration"})
        # Either a DiscourseUnit (skipped above) or the dict unchanged.
        assert out == {"id": 1, "relation": "Elaboration"}


class TestRoundTrip:
    def test_round_trip_via_json_preserves_tree_shape(self) -> None:
        root = _make_simple_tree()
        out = tree_to_dict(root)
        restored = tree_from_dict(json.loads(json.dumps(out)))

        # `restored` is either a DiscourseUnit (if isanlp installed) or
        # the dict (if not). In both cases the public attrs should match.
        if isinstance(restored, dict):
            assert restored["relation"] == "Elaboration"
            assert restored["left"]["id"] == 1
            assert restored["right"]["id"] == 2
        else:
            assert restored.relation == "Elaboration"
            assert restored.left.id == 1
            assert restored.right.id == 2

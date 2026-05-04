"""Tests for Parser construction-time behaviour.

These tests cover the parts of :class:`isanlp_rst.parser.Parser` that
do not require loading a model — argument validation, version
checking, and helper-method input validation.

A separate, model-loading smoke test lives in ``test_parser_smoke.py``
and is gated behind the ``RUN_MODEL_TESTS`` environment variable.
"""

from __future__ import annotations

from typing import Any, Sequence

import pytest


class TestVersionValidation:
    def test_unknown_version_raises_with_full_list(self) -> None:
        from isanlp_rst.parser import Parser

        with pytest.raises(NotImplementedError) as exc_info:
            Parser(hf_model_version="not-a-real-version")

        msg = str(exc_info.value)
        for known in ("rstdt", "gumrrg", "rstreebank", "unirst", "rrtrrg"):
            assert known in msg, f"Expected {known!r} in error message"

    def test_available_versions_constant_includes_dmrst_and_universal(self) -> None:
        from isanlp_rst.parser import Parser

        assert set(Parser.DMRST_PARSERS).issubset(set(Parser.AVAILABLE_VERSIONS))
        assert set(Parser.UNIVERSAL_PARSERS).issubset(set(Parser.AVAILABLE_VERSIONS))


def _make_parser_with_stubbed_predictor(
    parse_rst_impl=None, cache: Any | None = None
):
    """Construct a Parser bypassing __init__ (no model load) with a stubbed predictor.

    Returns the parser plus the list that records invocations. ``parse_rst_impl``
    can override the default predictor behaviour; defaults to
    ``lambda text: {"rst": [f"tree-for-{text}"]}``.
    """
    from isanlp_rst.parser import Parser

    parser = Parser.__new__(Parser)
    parser._cache = cache  # type: ignore[attr-defined]

    invocations: list[str] = []

    if parse_rst_impl is None:
        def parse_rst_impl(text: str):  # noqa: E731 — readable closure
            return {"rst": [f"tree-for-{text}"]}

    class _StubPredictor:
        def parse_rst(self_inner, text: str):  # noqa: N805
            invocations.append(text)
            return parse_rst_impl(text)

    parser.predictor = _StubPredictor()  # type: ignore[attr-defined]
    return parser, invocations


class TestParseSegmentsInputValidation:
    """`parse_segments` validates inputs without loading a model."""

    def test_empty_segments_raises(self) -> None:
        parser, _ = _make_parser_with_stubbed_predictor()
        with pytest.raises(ValueError, match="at least one segment"):
            parser.parse_segments([])

    def test_only_whitespace_segments_raises(self) -> None:
        parser, _ = _make_parser_with_stubbed_predictor()
        with pytest.raises(ValueError, match="only empty segments"):
            parser.parse_segments(["   ", "\n", ""])

    def test_segments_are_joined_with_separator(self) -> None:
        parser, invocations = _make_parser_with_stubbed_predictor()
        parser.parse_segments(["alpha", "beta", "gamma"], join_with=" | ")
        assert invocations == ["alpha | beta | gamma"]

    def test_empty_segments_filtered_before_join(self) -> None:
        parser, invocations = _make_parser_with_stubbed_predictor()
        parser.parse_segments(["alpha", "", "beta", "  "], join_with=",")
        assert invocations == ["alpha,beta"]


class TestParseBatchInputValidation:
    def test_empty_strings_yield_none_when_skip_empty(self) -> None:
        parser, _ = _make_parser_with_stubbed_predictor()
        result = parser.parse_batch(["a", "", "b", "  "])
        assert len(result) == 4
        assert result[1] is None
        assert result[3] is None
        assert result[0] == {"rst": ["tree-for-a"]}
        assert result[2] == {"rst": ["tree-for-b"]}

    def test_order_preserved(self) -> None:
        parser, _ = _make_parser_with_stubbed_predictor()
        inputs: Sequence[str] = ["one", "two", "three"]
        result = parser.parse_batch(inputs)
        assert [r["rst"][0] for r in result if r is not None] == [
            "tree-for-one", "tree-for-two", "tree-for-three"
        ]

    def test_skip_empty_false_raises_on_empty_string(self) -> None:
        parser, _ = _make_parser_with_stubbed_predictor()
        with pytest.raises(ValueError, match="Cannot parse empty text"):
            parser.parse_batch(["a", ""], skip_empty=False)


class TestCacheBehaviour:
    """The cache short-circuits the predictor when present."""

    def test_cache_hit_skips_predictor(self) -> None:
        class _Cache:
            def get(self, text):
                return {"rst": ["from-cache"]} if text == "hello" else None

            def put(self, text, result):
                pass

        parser, invocations = _make_parser_with_stubbed_predictor(cache=_Cache())
        result = parser("hello")
        assert result == {"rst": ["from-cache"]}
        assert invocations == []  # predictor never called

    def test_cache_miss_invokes_predictor_and_stores(self) -> None:
        stored: dict[str, dict] = {}

        class _Cache:
            def get(self, text):
                return None

            def put(self, text, result):
                stored[text] = result

        parser, invocations = _make_parser_with_stubbed_predictor(cache=_Cache())
        result = parser("hello")
        assert invocations == ["hello"]
        assert stored == {"hello": {"rst": ["tree-for-hello"]}}
        assert result == {"rst": ["tree-for-hello"]}

    def test_cache_put_failure_does_not_break_parse(self) -> None:
        class _Cache:
            def get(self, text):
                return None

            def put(self, text, result):
                raise RuntimeError("simulated cache failure")

        parser, _ = _make_parser_with_stubbed_predictor(cache=_Cache())
        # Must not raise — the warning gets logged.
        result = parser("hello")
        assert result == {"rst": ["tree-for-hello"]}


class TestEmptyTextValidation:
    def test_empty_string_raises(self) -> None:
        parser, _ = _make_parser_with_stubbed_predictor()
        with pytest.raises(ValueError, match="Cannot parse empty text"):
            parser("")

    def test_whitespace_only_raises(self) -> None:
        parser, _ = _make_parser_with_stubbed_predictor()
        with pytest.raises(ValueError, match="Cannot parse empty text"):
            parser("   \n  ")

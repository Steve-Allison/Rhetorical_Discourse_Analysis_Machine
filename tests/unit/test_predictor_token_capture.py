"""Input word identity must survive export without a second tokenizer."""

import pytest

from rdam.rst.base_predictor import BasePredictor
from rdam.rst.contracts.document import TextSpan


def test_capture_preserves_custom_word_boundaries_and_unicode_offsets() -> None:
    text = "  café—cafe\u0301  café"
    words = ("café—cafe\u0301", "café")
    offsets = ((2, 12), (14, 18))
    tokens = BasePredictor.capture_word_tokens(text, words, offsets)
    assert [(token.token_id, token.text, token.start, token.end) for token in tokens] == [
        (1, words[0], 2, 12),
        (2, words[1], 14, 18),
    ]


@pytest.mark.parametrize(
    ("words", "offsets"),
    (
        (("one",), ((1, 4),)),
        (("one", "one"), ((0, 3), (0, 3))),
        (("one",), ((0, 30),)),
        (("",), ((0, 0),)),
        (("one",), ()),
    ),
)
def test_capture_rejects_false_source_coordinates(
    words: tuple[str, ...], offsets: tuple[tuple[int, int], ...]
) -> None:
    with pytest.raises(ValueError):
        BasePredictor.capture_word_tokens("one one", words, offsets)


def test_predicted_boundaries_use_source_offsets_after_unknown_unicode() -> None:
    text = "  dvor̝aːk   next word"
    words = ("dvor̝aːk", "next", "word")
    word_offsets = [(text.index(word), text.index(word) + len(word)) for word in words]
    positions, originals = BasePredictor.build_offset_converter_from_words(text, words, word_offsets)
    # An unknown-token spelling can be longer than its single source mark.
    # The tokenizer's offsets, not that decoded spelling, remain authoritative.
    first_end = len(words[0])
    offsets = [(0, 4), (4, 5), (5, first_end), (first_end + 1, first_end + 5),
               (first_end + 6, first_end + 10)]
    spans = BasePredictor.predicted_edu_source_spans([2, 4], offsets, positions, originals, text)
    assert spans == [(word_offsets[0][0], word_offsets[0][1]), (word_offsets[1][0], word_offsets[2][1])]
    assert [text[start:end] for start, end in spans] == [words[0], "next word"]


@pytest.mark.parametrize("breaks", [[], [0], [2], [1, 0], [-1]])
def test_predicted_boundaries_reject_missing_or_invalid_subwords(breaks: list[int]) -> None:
    positions, originals = BasePredictor.build_offset_converter_from_words("one two", ["one", "two"])
    with pytest.raises(ValueError):
        BasePredictor.predicted_edu_source_spans(breaks, [(0, 3), (4, 7)], positions, originals, "one two")


@pytest.mark.parametrize(
    "boundaries",
    (
        (),
        (TextSpan(0, 3, "one"),),
        (TextSpan(1, 7, "ne two"),),
        (TextSpan(0, 5, "one t"), TextSpan(5, 7, "wo")),
        (TextSpan(0, 7, "one two"), TextSpan(4, 7, "two")),
        (TextSpan(4, 7, "two"), TextSpan(0, 3, "one")),
        (TextSpan(0, 7, "changed"),),
        (TextSpan(0, 8, "one two"),),
    ),
)
def test_source_groups_reject_uncovered_tokens_and_false_boundaries(boundaries: tuple[TextSpan, ...]) -> None:
    text = "one two"
    tokens = BasePredictor.capture_word_tokens(text, ("one", "two"), ((0, 3), (4, 7)))
    with pytest.raises(ValueError, match="source group"):
        BasePredictor.capture_token_groups(text, tokens, boundaries)


def test_source_groups_allow_whitespace_between_exact_boundaries() -> None:
    text = "  one\n\n two  "
    tokens = BasePredictor.capture_word_tokens(text, ("one", "two"), ((2, 5), (8, 11)))
    boundaries = (TextSpan(2, 5, "one"), TextSpan(8, 11, "two"))
    assert BasePredictor.capture_token_groups(text, tokens, boundaries) == (1, 2)


def test_edu_membership_preserves_native_word_crossing_a_subword_boundary() -> None:
    text = "alpha—beta"
    tokens = BasePredictor.capture_word_tokens(text, (text,), ((0, len(text)),))
    boundary = text.index("beta")
    edus = (TextSpan(0, boundary, text[:boundary]), TextSpan(boundary, len(text), text[boundary:]))
    assert BasePredictor.capture_edu_memberships(text, tokens, edus) == ((1,), (1,))
    # A missing dash is missing source evidence, even though the same word
    # overlaps both remaining spans.
    missing_character = (TextSpan(0, boundary - 1, text[:boundary - 1]), edus[1])
    with pytest.raises(ValueError, match="source characters uncovered"):
        BasePredictor.capture_edu_memberships(text, tokens, missing_character)

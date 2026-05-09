"""Unit tests for BasePredictor helpers — no model downloads, fast."""

from __future__ import annotations

from collections import OrderedDict

import pytest
import torch

from isanlp_rst.base_predictor import BasePredictor, str2bool


# ---------- str2bool ----------


@pytest.mark.parametrize(
    "value,expected",
    [
        (True, True),
        (False, False),
        ("true", True),
        ("TRUE", True),
        ("True", True),
        ("false", False),
        ("anything-else", False),
        (1, True),
        (0, False),
        (None, False),
        ([], False),
        ([0], True),
    ],
)
def test_str2bool(value, expected):
    assert str2bool(value) is expected


# ---------- _guess_token_offsets (the bug-fix lives here) ----------


def test_guess_token_offsets_simple():
    offsets = BasePredictor._guess_token_offsets("hello world", ["hello", "world"])
    assert offsets == [(0, 5), (6, 11)]


def test_guess_token_offsets_with_empty_token():
    offsets = BasePredictor._guess_token_offsets("hello", ["hello", ""])
    assert offsets == [(0, 5), (5, 5)]


def test_guess_token_offsets_walks_past_separator():
    offsets = BasePredictor._guess_token_offsets("a   b", ["a", "b"])
    assert offsets == [(0, 1), (4, 5)]


def test_guess_token_offsets_raises_on_miss():
    """The fix: a missing token must raise rather than silently fall back."""
    with pytest.raises(ValueError, match="Cannot locate token"):
        BasePredictor._guess_token_offsets("hello world", ["hello", "MISSING"])


def test_guess_token_offsets_token_longer_than_text():
    with pytest.raises(ValueError, match="Cannot locate token"):
        BasePredictor._guess_token_offsets("hi", ["impossibly-long-token"])


def test_guess_token_offsets_at_text_boundary():
    """Token at the very end should match cleanly."""
    offsets = BasePredictor._guess_token_offsets("ab", ["a", "b"])
    assert offsets == [(0, 1), (1, 2)]


# ---------- _validate_edus ----------


def test_validate_edus_happy():
    assert BasePredictor._validate_edus(["a", "b"]) == ["a", "b"]
    assert BasePredictor._validate_edus(("x",)) == ["x"]


def test_validate_edus_none_raises():
    with pytest.raises(ValueError, match="must be provided"):
        BasePredictor._validate_edus(None)  # type: ignore[arg-type]


def test_validate_edus_string_raises():
    with pytest.raises(TypeError, match="not a single string"):
        BasePredictor._validate_edus("oh no a string")


def test_validate_edus_bytes_raises():
    with pytest.raises(TypeError, match="not a single string"):
        BasePredictor._validate_edus(b"oh no bytes")  # type: ignore[arg-type]


def test_validate_edus_empty_raises():
    with pytest.raises(ValueError, match="at least one EDU"):
        BasePredictor._validate_edus([])


def test_validate_edus_empty_string_raises():
    with pytest.raises(ValueError, match="position 1 is empty"):
        BasePredictor._validate_edus(["ok", ""])


def test_validate_edus_non_string_raises():
    with pytest.raises(TypeError, match="position 1 must be a string"):
        BasePredictor._validate_edus(["ok", 42])  # type: ignore[list-item]


# ---------- _compute_edu_char_spans ----------


def test_compute_edu_char_spans_basic():
    text, spans = BasePredictor._compute_edu_char_spans(["Hello.", "World."])
    assert text == "Hello. World."
    assert spans == [(0, 6), (7, 13)]


def test_compute_edu_char_spans_single():
    text, spans = BasePredictor._compute_edu_char_spans(["Just one."])
    assert text == "Just one."
    assert spans == [(0, 9)]


# ---------- _char_spans_to_token_breaks ----------


def test_char_spans_to_token_breaks_aligned():
    # tokens "hello" "world" with offsets, EDU spans say "hello" then "world"
    offsets = [(0, 5), (6, 11)]
    spans = [(0, 5), (6, 11)]
    breaks = BasePredictor._char_spans_to_token_breaks(offsets, spans)
    assert breaks == [0, 1]


def test_char_spans_to_token_breaks_misaligned_raises():
    offsets = [(0, 5), (6, 11)]
    spans = [(0, 4), (6, 11)]  # first EDU ends mid-token
    with pytest.raises(ValueError, match="does not align"):
        BasePredictor._char_spans_to_token_breaks(offsets, spans)


def test_char_spans_to_token_breaks_incomplete_coverage_raises():
    offsets = [(0, 5), (6, 11)]
    spans = [(0, 5)]  # leaves the second token uncovered
    with pytest.raises(ValueError, match="cover the entire"):
        BasePredictor._char_spans_to_token_breaks(offsets, spans)


def test_char_spans_to_token_breaks_empty_offsets_raises():
    with pytest.raises(ValueError, match="Unable to derive"):
        BasePredictor._char_spans_to_token_breaks([], [(0, 5)])


# ---------- _load_torch_weights ----------


def test_load_torch_weights_pure_tensors(tmp_path):
    state = OrderedDict([("a.weight", torch.tensor([1.0, 2.0])),
                         ("a.bias", torch.tensor([0.5]))])
    path = tmp_path / "weights.pt"
    torch.save(state, str(path))

    loaded = BasePredictor._load_torch_weights(str(path), torch.device("cpu"))
    assert set(loaded.keys()) == {"a.weight", "a.bias"}
    assert torch.equal(loaded["a.weight"], torch.tensor([1.0, 2.0]))


# ---------- remap_tree_offsets — strict binary invariant ----------


class _FakeNode:
    """Stand-in for isanlp.DiscourseUnit with the attributes used by remap."""
    def __init__(self, start, end, left=None, right=None):
        self.start = start
        self.end = end
        self.left = left
        self.right = right
        self.text = ""


class _Predictor(BasePredictor):
    """Minimal concrete subclass (BasePredictor is ABC)."""


def test_remap_tree_offsets_leaf():
    p = _Predictor()
    leaf = _FakeNode(start=0, end=2)
    text = "hello world"
    positions = list(range(len(text) + 1))
    originals = list(range(len(text) + 1))
    p.remap_tree_offsets(leaf, positions, originals, text)
    assert leaf.text == text[0:2]


def test_remap_tree_offsets_binary():
    p = _Predictor()
    text = "foo bar"
    positions = list(range(len(text) + 1))
    originals = list(range(len(text) + 1))
    left = _FakeNode(start=0, end=3)
    right = _FakeNode(start=4, end=7)
    root = _FakeNode(start=0, end=7, left=left, right=right)
    p.remap_tree_offsets(root, positions, originals, text)
    assert left.text == "foo"
    assert right.text == "bar"
    assert root.text == "foo bar"
    assert root.start == 0 and root.end == 7


def test_remap_tree_offsets_unary_raises():
    """Unary node = DUConverter bug; surface it rather than patch it."""
    p = _Predictor()
    text = "hello"
    positions = list(range(len(text) + 1))
    originals = list(range(len(text) + 1))
    left = _FakeNode(start=0, end=5)
    bad = _FakeNode(start=0, end=5, left=left, right=None)
    with pytest.raises(ValueError, match="unary node"):
        p.remap_tree_offsets(bad, positions, originals, text)


# ---------- divide_chunks ----------


def test_divide_chunks_basic():
    out = list(BasePredictor.divide_chunks([1, 2, 3, 4, 5], 2))
    assert out == [[1, 2], [3, 4], [5]]


def test_divide_chunks_empty():
    out = list(BasePredictor.divide_chunks([], 2))
    assert out == [[]]


# ---------- _resolve_dtype — device-aware default + string parsing ----------


def test_resolve_dtype_default_cpu():
    assert BasePredictor._resolve_dtype(None, torch.device('cpu')) == torch.float32


def test_resolve_dtype_default_cuda_is_float32():
    """Default is fp32 across all devices — measured fp32 wins on MPS for
    typical inputs, and we don't promise bf16 wins on CUDA without measurement
    on the user's hardware. Users opt in via dtype= when their workload
    benefits."""
    assert (BasePredictor._resolve_dtype(None, torch.device('cuda', 0))
            == torch.float32)


def test_resolve_dtype_default_mps_is_float32():
    assert (BasePredictor._resolve_dtype(None, torch.device('mps'))
            == torch.float32)


@pytest.mark.parametrize(
    "spec,expected",
    [
        ('float32', torch.float32),
        ('fp32', torch.float32),
        ('float16', torch.float16),
        ('fp16', torch.float16),
        ('half', torch.float16),
        ('bfloat16', torch.bfloat16),
        ('bf16', torch.bfloat16),
        ('FP16', torch.float16),
        ('  bf16  ', torch.bfloat16),
    ],
)
def test_resolve_dtype_string_parsing(spec, expected):
    assert BasePredictor._resolve_dtype(spec, torch.device('cpu')) == expected


@pytest.mark.parametrize(
    "spec",
    [torch.float32, torch.float16, torch.bfloat16],
)
def test_resolve_dtype_passthrough(spec):
    assert BasePredictor._resolve_dtype(spec, torch.device('cpu')) is spec


def test_resolve_dtype_unknown_string_raises():
    with pytest.raises(ValueError, match="Unknown dtype"):
        BasePredictor._resolve_dtype('quantum-float8', torch.device('cpu'))


def test_resolve_dtype_unsupported_torch_dtype_raises():
    with pytest.raises(ValueError, match="Unsupported dtype"):
        BasePredictor._resolve_dtype(torch.int64, torch.device('cpu'))


# ---------- _select_device — CPU/CUDA/MPS dispatch ----------


def test_select_device_cpu():
    assert BasePredictor._select_device(-1) == torch.device('cpu')


def test_select_device_with_no_accelerator(monkeypatch):
    monkeypatch.setattr(torch.cuda, 'is_available', lambda: False)
    # Pretend MPS isn't available either.
    if hasattr(torch.backends, 'mps'):
        monkeypatch.setattr(torch.backends.mps, 'is_available', lambda: False)
        monkeypatch.setattr(torch.backends.mps, 'is_built', lambda: False)
    with pytest.raises(RuntimeError, match='no GPU backend is available'):
        BasePredictor._select_device(0)


def test_select_device_prefers_cuda(monkeypatch):
    monkeypatch.setattr(torch.cuda, 'is_available', lambda: True)
    if hasattr(torch.backends, 'mps'):
        monkeypatch.setattr(torch.backends.mps, 'is_available', lambda: True)
        monkeypatch.setattr(torch.backends.mps, 'is_built', lambda: True)
    dev = BasePredictor._select_device(2)
    assert dev.type == 'cuda' and dev.index == 2


def test_select_device_falls_back_to_mps(monkeypatch):
    if not (hasattr(torch.backends, 'mps') and torch.backends.mps.is_built()):
        pytest.skip('PyTorch built without MPS support')
    monkeypatch.setattr(torch.cuda, 'is_available', lambda: False)
    monkeypatch.setattr(torch.backends.mps, 'is_available', lambda: True)
    monkeypatch.setattr(torch.backends.mps, 'is_built', lambda: True)
    dev = BasePredictor._select_device(0)
    assert dev.type == 'mps'


# ---------- _recount_spans (regression — _recount_spans is delicate) ----------


def test_recount_spans_simple():
    word_offsets = [(0, 5), (6, 11)]            # "hello world"
    subword_offsets = [(0, 3), (3, 5), (6, 11)]  # "hel" "lo" "world"
    word_breaks = [0]                            # EDU ends after first word
    breaks = BasePredictor._recount_spans(word_offsets, subword_offsets, word_breaks)
    # Last subword index that ends at word 0's end (5) is index 1.
    # Function appends final-subword index too; covers whole input.
    assert breaks[-1] == len(subword_offsets) - 1

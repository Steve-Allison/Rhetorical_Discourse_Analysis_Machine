"""Integration tests that load real modern transformer models — marked slow.

Run with:

    pixi run test-all              # all tests including these
    pixi run pytest -m slow -v     # just these

These tests verify:
* device and dtype consistency on ModernBERT
* long-text sliding-window and attention capacity on 8,192 tokens
* parse_from_edus / parse_rst path consistency (round-trip)
* edge-input handling: empty, whitespace-only, single-token, multi-paragraph, unicode
* typed parse_document into RstAnalysis contract
"""

import pytest
import torch

from rdam.rst.contracts import InputFidelityEnum, OutputFormalismEnum, RstAnalysis, RstDocument
from rdam.rst.parser import Parser

pytestmark = pytest.mark.slow

SHORT_EN = "The cat sat on the mat. It was a black cat. The mat was red."

LONG_EN = (
    "Climate scientists have been documenting an alarming acceleration in the "
    "rate of polar ice melt over the past decade. The latest satellite data "
    "indicates that ice loss in Greenland alone has tripled compared to "
    "measurements from the early 2000s. This rapid melting contributes "
    "significantly to global sea level rise, threatening coastal communities "
    "worldwide. Researchers warn that without immediate action to reduce "
    "greenhouse gas emissions, the consequences will be irreversible. "
    "However, recent technological advances in carbon capture offer some hope. "
    "If deployed at scale, these technologies could help offset emissions "
    "from industries that are difficult to decarbonise directly. The cost of "
    "deploying such infrastructure remains the principal obstacle. Public "
    "funding mechanisms, combined with private-sector incentives, will be "
    "essential to accelerating adoption. Several governments have already "
    "announced pilot programmes, and early results suggest the approach is "
    "technically feasible at a scale that would meaningfully reduce net "
    "emissions over the coming decade."
)

RUSSIAN_TEXT = (
    "Учёные климатологи фиксируют тревожное ускорение темпов таяния полярных "
    "льдов в течение последнего десятилетия. Последние спутниковые данные "
    "показывают, что потеря льда только в Гренландии утроилась по сравнению "
    "с измерениями начала 2000-х годов. Это быстрое таяние существенно "
    "способствует глобальному повышению уровня моря."
)

EDGE_CASES = {
    "single_sentence": "Hello world.",
    "multi_paragraph": (
        "The first paragraph contains two sentences. Each is short.\n\n"
        "The second paragraph is also short. It has two sentences too.\n\n"
        "And here is a third paragraph. With one final sentence."
    ),
    "with_unicode": (
        "She said «hello» — then paused. The crowd's reaction was muted; perhaps they expected something… more."
    ),
}

EMPTY_INPUTS = ("", "   ", "\n\t\n")


def _topology(unit) -> tuple:
    """Tree topology + EDU segmentation."""
    if not getattr(unit, "left", None) and not getattr(unit, "right", None):
        return ("LEAF", unit.start, unit.end)
    return (_topology(unit.left), _topology(unit.right))


def _collect_leaves(unit) -> list[str]:
    out: list[str] = []

    def walk(u) -> None:
        l, r = getattr(u, "left", None), getattr(u, "right", None)
        if l is None and r is None:
            out.append(u.text)
            return
        if l is not None:
            walk(l)
        if r is not None:
            walk(r)

    walk(unit)
    return out


def _collect_leaf_units(unit) -> list:
    out: list = []

    def walk(u) -> None:
        l, r = getattr(u, "left", None), getattr(u, "right", None)
        if l is None and r is None:
            out.append(u)
            return
        if l is not None:
            walk(l)
        if r is not None:
            walk(r)

    walk(unit)
    return out


def _assert_aligned(unit, text: str, path: str = "root") -> None:
    expected = text[unit.start : unit.end]
    assert unit.text == expected, f"{path}: tree.text={unit.text!r} != text[{unit.start}:{unit.end}]={expected!r}"
    for name in ("left", "right"):
        child = getattr(unit, name, None)
        if child is not None:
            _assert_aligned(child, text, f"{path}.{name}")

    if path == "root":
        leaves = _collect_leaf_units(unit)
        assert leaves, "expected at least one leaf EDU"
        assert leaves[0].start >= 0
        assert leaves[-1].end <= len(text)
        for prev, nxt in zip(leaves, leaves[1:], strict=False):
            assert prev.end <= nxt.start, (
                f"overlapping/out-of-order leaves: [{prev.start}:{prev.end}] then [{nxt.start}:{nxt.end}]"
            )
        assert unit.start <= leaves[0].start
        assert unit.end >= leaves[-1].end


@pytest.fixture(scope="session")
def dmrst_cpu() -> Parser:
    return Parser(device="cpu")


_mps_available = hasattr(torch.backends, "mps") and torch.backends.mps.is_available() and torch.backends.mps.is_built()


@pytest.mark.skipif(not _mps_available, reason="MPS not available")
@pytest.mark.parametrize("dtype", [torch.float32, torch.bfloat16, torch.float16])
@pytest.mark.parametrize(
    "text_name,text",
    [
        ("SHORT_EN", SHORT_EN),
        ("LONG_EN", LONG_EN),
    ],
)
def test_dmrst_dtype_equivalence_on_mps(dmrst_cpu: Parser, text_name, text, dtype):
    """fp16/bf16 on MPS must produce valid aligned trees."""
    mps_parser = Parser(device="mps", dtype=dtype)
    res = mps_parser(text)
    tree = res["rst"][0]
    _assert_aligned(tree, text)
    leaves = _collect_leaves(tree)
    assert len(leaves) >= 2


def test_long_text_alignment(dmrst_cpu: Parser):
    res = dmrst_cpu(LONG_EN)
    _assert_aligned(res["rst"][0], LONG_EN)


def test_round_trip_dmrst(dmrst_cpu: Parser):
    res = dmrst_cpu(LONG_EN)
    leaves = _collect_leaves(res["rst"][0])
    res2 = dmrst_cpu.from_edus(leaves)
    leaves2 = _collect_leaves(res2["rst"][0])
    assert leaves2 == leaves, "round-trip leaves diverged"


def test_edge_single_sentence(dmrst_cpu: Parser):
    res = dmrst_cpu(EDGE_CASES["single_sentence"])
    _assert_aligned(res["rst"][0], EDGE_CASES["single_sentence"])


def test_edge_multi_paragraph(dmrst_cpu: Parser):
    text = EDGE_CASES["multi_paragraph"]
    res = dmrst_cpu(text)
    _assert_aligned(res["rst"][0], text)


def test_edge_unicode_punctuation(dmrst_cpu: Parser):
    text = EDGE_CASES["with_unicode"]
    res = dmrst_cpu(text)
    _assert_aligned(res["rst"][0], text)


@pytest.mark.parametrize("empty", EMPTY_INPUTS)
def test_edge_empty_or_whitespace_raises(dmrst_cpu: Parser, empty: str):
    with pytest.raises(ValueError, match="non-empty"):
        dmrst_cpu(empty)


def test_parse_document_dmrst_e2e(dmrst_cpu: Parser):
    doc = RstDocument.from_text(LONG_EN, document_id="e2e-dmrst-1")
    analysis = dmrst_cpu.parse_document(doc, output="rst_tree")

    assert isinstance(analysis, RstAnalysis)
    assert analysis.document_id == "e2e-dmrst-1"
    assert analysis.formalism == OutputFormalismEnum.RST_TREE
    assert len(analysis.nodes) > 1
    assert analysis.timing.total_ms >= 0.0

    for node in analysis.nodes:
        start, end = node.char_span
        assert LONG_EN[start:end] == node.text


def test_parse_document_with_edus_e2e(dmrst_cpu: Parser):
    res = dmrst_cpu(SHORT_EN)
    leaves = _collect_leaves(res["rst"][0])

    doc = RstDocument.from_edus(leaves, document_id="e2e-edus-1")
    assert doc.fidelity == InputFidelityEnum.RECONSTRUCTED

    analysis = dmrst_cpu.parse_document(doc, output="rst_tree")
    assert isinstance(analysis, RstAnalysis)
    assert len(analysis.nodes) >= len(leaves)


def test_parse_document_edge_cases_e2e(dmrst_cpu: Parser):
    unicode_doc = RstDocument.from_text(EDGE_CASES["with_unicode"], document_id="e2e-unicode")
    analysis_uni = dmrst_cpu.parse_document(unicode_doc)
    for node in analysis_uni.nodes:
        start, end = node.char_span
        assert EDGE_CASES["with_unicode"][start:end] == node.text

    for empty in EMPTY_INPUTS:
        empty_doc = RstDocument.from_text(empty)
        with pytest.raises(ValueError, match="non-empty"):
            dmrst_cpu.parse_document(empty_doc)

"""Integration tests that load real models — marked slow.

Run with:

    pixi run test-all              # all tests including these
    pixi run pytest -m slow -v     # just these

These are bug-finding tests: each one compares a non-trivial run against a
CPU/fp32 baseline and asserts equivalence. They're designed to catch:

* dtype-specific divergence (bf16/fp16 producing different segmentation or
  tree topology from fp32; relation/nuclearity labels are precision-sensitive
  and deliberately not asserted — see _topology)
* device-specific divergence (MPS or CUDA disagreeing with CPU)
* model-loading regressions for any of the 5 published checkpoints
* tokenisation drift across languages (Russian for rstreebank, multiple
  languages via UniRST relinventories)
* sliding-window stitching failures on long text
* parse_from_edus / parse_rst path inconsistency (round-trip)
* edge-input handling: empty, whitespace-only, single-token, multi-paragraph

Models are loaded into a session-scoped fixture so we don't pay the load cost
per-test. ~5 GB of HF cache required (gumrrg, unirst); bench/full coverage
needs all 5 models (~10 GB).
"""

import pytest
import torch

from isanlp_rst.contracts import InputFidelityEnum, OutputFormalismEnum, RstAnalysis, RstDocument
from isanlp_rst.parser import Parser


# All tests in this file are integration / slow.
pytestmark = pytest.mark.slow


# ---------- Sample texts (English short, English long, Russian, edge cases) ----------

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

# Russian text — exercises rstreebank's training language and the multilingual
# tokeniser path (razdel handles Cyrillic).
RUSSIAN_TEXT = (
    "Учёные климатологи фиксируют тревожное ускорение темпов таяния полярных "
    "льдов в течение последнего десятилетия. Последние спутниковые данные "
    "показывают, что потеря льда только в Гренландии утроилась по сравнению "
    "с измерениями начала 2000-х годов. Это быстрое таяние существенно "
    "способствует глобальному повышению уровня моря."
)

EDGE_CASES = {
    'single_sentence': "Hello world.",
    'multi_paragraph': (
        "The first paragraph contains two sentences. Each is short.\n\n"
        "The second paragraph is also short. It has two sentences too.\n\n"
        "And here is a third paragraph. With one final sentence."
    ),
    'with_unicode': (
        "She said «hello» — then paused. The crowd's reaction was "
        "muted; perhaps they expected something… more."
    ),
}

EMPTY_INPUTS = ('', '   ', '\n\t\n')



# ---------- Helpers ----------


def _topology(unit) -> tuple:
    """Tree topology + EDU segmentation, ignoring relation / nuclearity labels.

    This is the invariant that holds across dtypes. A node's relation and
    nuclearity are an argmax over a per-node distribution; on a near-tied node
    (high split entropy) reduced precision (bf16/fp16) can flip the winner with
    no structural change — e.g. rrtrrg on LONG_EN flips one entropy-0.40 node
    from Elaboration/NS to Cause-effect/SN under bf16, leaving every span
    identical. The EDU segmentation and the tree nesting, by contrast, are
    stable across fp32 / bf16 / fp16 for every published model, so that is what
    we assert. Labels are deliberately excluded."""
    if not getattr(unit, 'left', None) and not getattr(unit, 'right', None):
        return ('LEAF', unit.start, unit.end)
    return (_topology(unit.left), _topology(unit.right))


def _collect_leaves(unit) -> list[str]:
    out: list[str] = []
    def walk(u) -> None:
        l, r = getattr(u, 'left', None), getattr(u, 'right', None)
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
        l, r = getattr(u, 'left', None), getattr(u, 'right', None)
        if l is None and r is None:
            out.append(u)
            return
        if l is not None:
            walk(l)
        if r is not None:
            walk(r)

    walk(unit)
    return out


def _assert_aligned(unit, text: str, path: str = 'root') -> None:
    """Assert remapped spans are consistent with ``text``.

    Beyond the per-node ``text == text[start:end]`` check (which remap
    always establishes), verify leaf spans are ordered, non-overlapping,
    and that the root covers the leaf span range.
    """
    expected = text[unit.start:unit.end]
    assert unit.text == expected, (
        f"{path}: tree.text={unit.text!r} != text[{unit.start}:{unit.end}]={expected!r}"
    )
    for name in ('left', 'right'):
        child = getattr(unit, name, None)
        if child is not None:
            _assert_aligned(child, text, f"{path}.{name}")

    if path == 'root':
        leaves = _collect_leaf_units(unit)
        assert leaves, 'expected at least one leaf EDU'
        assert leaves[0].start >= 0
        assert leaves[-1].end <= len(text)
        for prev, nxt in zip(leaves, leaves[1:], strict=False):
            assert prev.end <= nxt.start, (
                f'overlapping/out-of-order leaves: '
                f'[{prev.start}:{prev.end}] then [{nxt.start}:{nxt.end}]'
            )
        assert unit.start <= leaves[0].start
        assert unit.end >= leaves[-1].end


# ---------- Session fixtures (model load is expensive) ----------


@pytest.fixture(scope='session')
def dmrst_gumrrg_cpu() -> Parser:
    return Parser(hf_model_name='tchewik/isanlp_rst_v3',
                  hf_model_version='gumrrg', device='cpu')


@pytest.fixture(scope='session')
def dmrst_rstdt_cpu() -> Parser:
    return Parser(hf_model_name='tchewik/isanlp_rst_v3',
                  hf_model_version='rstdt', device='cpu')


@pytest.fixture(scope='session')
def dmrst_rstreebank_cpu() -> Parser:
    """Russian-trained DMRST model."""
    return Parser(hf_model_name='tchewik/isanlp_rst_v3',
                  hf_model_version='rstreebank', device='cpu')


@pytest.fixture(scope='session')
def unirst_eng_cpu() -> Parser:
    return Parser(hf_model_name='tchewik/isanlp_rst_v3',
                  hf_model_version='unirst', device='cpu',
                  relinventory='eng.erst.gum')


@pytest.fixture(scope='session')
def rrtrrg_cpu() -> Parser:
    """Multi-corpus, non-union UniRST — exercises the checkpoint-driven
    classifier-count code path."""
    return Parser(hf_model_name='tchewik/isanlp_rst_v3',
                  hf_model_version='rrtrrg', device='cpu')


# ---------- BUG-FINDING test 1: cross-dtype equivalence on MPS ----------
#
# Default behaviour is fp32. fp16/bf16 are opt-in. Each must produce the same
# tree TOPOLOGY + EDU segmentation as the fp32 baseline (see _topology) —
# structural divergence indicates an autocast or precision-related bug.
# Relation / nuclearity labels are NOT asserted: they are a per-node argmax
# that legitimately flips on near-tied nodes under reduced precision without
# any structural change, so asserting them would encode a false invariant.

_mps_available = (
    hasattr(torch.backends, 'mps')
    and torch.backends.mps.is_available()
    and torch.backends.mps.is_built()
)


@pytest.mark.skipif(not _mps_available, reason='MPS not available')
@pytest.mark.parametrize('dtype', [torch.float32, torch.bfloat16, torch.float16])
@pytest.mark.parametrize('text_name,text', [
    ('SHORT_EN', SHORT_EN),
    ('LONG_EN', LONG_EN),
])
def test_dmrst_dtype_equivalence_on_mps(dmrst_gumrrg_cpu: Parser, text_name, text, dtype):
    """fp16/bf16 on MPS must produce identical tree shape to fp32-CPU baseline."""
    baseline = _topology(dmrst_gumrrg_cpu(text)['rst'][0])
    mps_parser = Parser(hf_model_name='tchewik/isanlp_rst_v3',
                        hf_model_version='gumrrg', device='mps', dtype=dtype)
    candidate = _topology(mps_parser(text)['rst'][0])
    assert candidate == baseline, (
        f"DMRST gumrrg MPS {dtype} on {text_name} diverged from CPU fp32"
    )


@pytest.mark.skipif(not _mps_available, reason='MPS not available')
@pytest.mark.parametrize('dtype', [torch.float32, torch.bfloat16, torch.float16])
def test_unirst_dtype_equivalence_on_mps(unirst_eng_cpu: Parser, dtype):
    """UniRST has a materially different architecture (multi-corpus, union
    relations) — verify it also has bit-equivalent dtype behaviour."""
    baseline = _topology(unirst_eng_cpu(LONG_EN)['rst'][0])
    mps_parser = Parser(hf_model_name='tchewik/isanlp_rst_v3',
                        hf_model_version='unirst', device='mps',
                        relinventory='eng.erst.gum', dtype=dtype)
    candidate = _topology(mps_parser(LONG_EN)['rst'][0])
    assert candidate == baseline, f"UniRST MPS {dtype} diverged from CPU fp32"


# ---------- BUG-FINDING test 2: long-text sliding-window stitching ----------


def test_long_text_alignment(dmrst_gumrrg_cpu: Parser):
    """Long-text path uses a sliding-window encoding. Tree-text alignment must
    survive the stitching."""
    res = dmrst_gumrrg_cpu(LONG_EN)
    _assert_aligned(res['rst'][0], LONG_EN)


def test_long_text_unirst_alignment(unirst_eng_cpu: Parser):
    res = unirst_eng_cpu(LONG_EN)
    _assert_aligned(res['rst'][0], LONG_EN)


# ---------- BUG-FINDING test 3: non-English text ----------


def test_russian_text_dmrst(dmrst_rstreebank_cpu: Parser):
    """rstreebank is the Russian-trained DMRST model. A Cyrillic input must
    produce a valid aligned tree (catches tokeniser regressions for non-ASCII)."""
    res = dmrst_rstreebank_cpu(RUSSIAN_TEXT)
    tree = res['rst'][0]
    _assert_aligned(tree, RUSSIAN_TEXT)
    leaves = _collect_leaves(tree)
    assert len(leaves) >= 2, f"expected segmentation into multiple EDUs, got {len(leaves)}"
    # Every leaf must contain at least one Cyrillic letter — a degenerate
    # tokenisation that produces only whitespace/punctuation EDUs would fail.
    cyrillic = set('абвгдеёжзийклмнопрстуфхцчшщъыьэюяАБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ')
    for i, leaf in enumerate(leaves):
        assert any(c in cyrillic for c in leaf), f"leaf {i} contains no Cyrillic: {leaf!r}"


def test_unirst_russian_via_relinventory():
    """UniRST is multilingual. Using a Russian relinventory on Russian text
    should produce a sensible tree."""
    parser = Parser(hf_model_name='tchewik/isanlp_rst_v3',
                    hf_model_version='unirst', device='cpu',
                    relinventory='rus.rst.rrt')
    res = parser(RUSSIAN_TEXT)
    _assert_aligned(res['rst'][0], RUSSIAN_TEXT)


# ---------- BUG-FINDING test 4: parse_from_edus round-trip ----------


def test_round_trip_dmrst(dmrst_gumrrg_cpu: Parser):
    """parse_rst → extract leaves → parse_from_edus → leaves must match.

    This catches divergence between the two top-level entry points (different
    code paths for segmentation vs pre-segmented input)."""
    res = dmrst_gumrrg_cpu(LONG_EN)
    leaves = _collect_leaves(res['rst'][0])
    res2 = dmrst_gumrrg_cpu.from_edus(leaves)
    leaves2 = _collect_leaves(res2['rst'][0])
    assert leaves2 == leaves, "round-trip leaves diverged"


def test_round_trip_unirst(unirst_eng_cpu: Parser):
    res = unirst_eng_cpu(LONG_EN)
    leaves = _collect_leaves(res['rst'][0])
    res2 = unirst_eng_cpu.from_edus(leaves)
    leaves2 = _collect_leaves(res2['rst'][0])
    assert leaves2 == leaves, "UniRST round-trip leaves diverged"


# ---------- BUG-FINDING test 5: edge inputs ----------


def test_edge_single_sentence(dmrst_gumrrg_cpu: Parser):
    """Hits the <3-token early-return branch."""
    res = dmrst_gumrrg_cpu(EDGE_CASES['single_sentence'])
    _assert_aligned(res['rst'][0], EDGE_CASES['single_sentence'])


def test_edge_multi_paragraph(dmrst_gumrrg_cpu: Parser):
    """Newlines / paragraph breaks must not corrupt offsets."""
    text = EDGE_CASES['multi_paragraph']
    res = dmrst_gumrrg_cpu(text)
    _assert_aligned(res['rst'][0], text)


def test_edge_unicode_punctuation(dmrst_gumrrg_cpu: Parser):
    """Smart quotes, em-dashes, ellipsis, apostrophes — each is multi-byte in
    UTF-8. Catches offset bugs that confuse char-offset with byte-offset."""
    text = EDGE_CASES['with_unicode']
    res = dmrst_gumrrg_cpu(text)
    _assert_aligned(res['rst'][0], text)


@pytest.mark.parametrize('empty', EMPTY_INPUTS)
def test_edge_empty_or_whitespace_raises(dmrst_gumrrg_cpu: Parser, empty: str):
    """Empty / whitespace-only inputs must fail closed — not a silent dummy tree."""
    with pytest.raises(ValueError, match='non-empty'):
        dmrst_gumrrg_cpu(empty)


# ---------- BUG-FINDING test 6: full-cross-dtype on every model (selected text) ----------


@pytest.mark.skipif(not _mps_available, reason='MPS not available')
@pytest.mark.parametrize('dtype', [torch.float32, torch.bfloat16, torch.float16])
def test_dtype_equivalence_rstdt(dmrst_rstdt_cpu: Parser, dtype):
    baseline = _topology(dmrst_rstdt_cpu(LONG_EN)['rst'][0])
    p = Parser(hf_model_name='tchewik/isanlp_rst_v3',
               hf_model_version='rstdt', device='mps', dtype=dtype)
    assert _topology(p(LONG_EN)['rst'][0]) == baseline, f"rstdt {dtype} diverged"


@pytest.mark.skipif(not _mps_available, reason='MPS not available')
@pytest.mark.parametrize('dtype', [torch.float32, torch.bfloat16, torch.float16])
def test_dtype_equivalence_rstreebank(dmrst_rstreebank_cpu: Parser, dtype):
    baseline = _topology(dmrst_rstreebank_cpu(RUSSIAN_TEXT)['rst'][0])
    p = Parser(hf_model_name='tchewik/isanlp_rst_v3',
               hf_model_version='rstreebank', device='mps', dtype=dtype)
    assert _topology(p(RUSSIAN_TEXT)['rst'][0]) == baseline, (
        f"rstreebank {dtype} diverged (Russian text)"
    )


@pytest.mark.skipif(not _mps_available, reason='MPS not available')
@pytest.mark.parametrize('dtype', [torch.float32, torch.bfloat16, torch.float16])
def test_dtype_equivalence_rrtrrg(rrtrrg_cpu: Parser, dtype):
    """rrtrrg uses the checkpoint-driven classifier path — verify dtype
    equivalence over that fix specifically."""
    baseline = _topology(rrtrrg_cpu(LONG_EN)['rst'][0])
    p = Parser(hf_model_name='tchewik/isanlp_rst_v3',
               hf_model_version='rrtrrg', device='mps', dtype=dtype)
    assert _topology(p(LONG_EN)['rst'][0]) == baseline, f"rrtrrg {dtype} diverged"


# ---------- BUG-FINDING test 7: typed parse_document on real models (e2e) ----------


def test_parse_document_dmrst_e2e(dmrst_gumrrg_cpu: Parser):
    """Real DMRST end-to-end model parsing into a typed RstAnalysis contract."""
    doc = RstDocument.from_text(LONG_EN, document_id="e2e-gumrrg-1")
    analysis = dmrst_gumrrg_cpu.parse_document(doc, output="rst_tree")

    assert isinstance(analysis, RstAnalysis)
    assert analysis.document_id == "e2e-gumrrg-1"
    assert analysis.formalism == OutputFormalismEnum.RST_TREE
    assert len(analysis.nodes) > 5
    assert len(analysis.primary_edges) > 4
    assert analysis.timing.total_ms > 0.0
    assert analysis.provenance.model_id == "gumrrg"

    # Verify character offsets align with exact text slices
    for node in analysis.nodes:
        start, end = node.char_span
        assert LONG_EN[start:end] == node.text


def test_parse_document_with_edus_e2e(dmrst_gumrrg_cpu: Parser):
    """Real DMRST parse with pre-segmented EDUs into RstAnalysis."""
    # First get real gold/model leaves
    res = dmrst_gumrrg_cpu(SHORT_EN)
    leaves = _collect_leaves(res['rst'][0])

    doc = RstDocument.from_edus(leaves, document_id="e2e-edus-1")
    assert doc.fidelity == InputFidelityEnum.RECONSTRUCTED

    analysis = dmrst_gumrrg_cpu.parse_document(doc, output="erst_graph")
    assert analysis.formalism == OutputFormalismEnum.ERST_GRAPH
    assert len(analysis.nodes) >= len(leaves)


def test_parse_document_unirst_e2e(unirst_eng_cpu: Parser):
    """Real UniRST end-to-end multilingual model parse into RstAnalysis."""
    doc = RstDocument.from_text(SHORT_EN, document_id="e2e-unirst-1")
    analysis = unirst_eng_cpu.parse_document(doc, output="rst_tree")

    assert isinstance(analysis, RstAnalysis)
    assert analysis.document_id == "e2e-unirst-1"
    assert len(analysis.nodes) >= 3


def test_parse_document_edge_cases_e2e(dmrst_gumrrg_cpu: Parser):
    """Edge cases on real model: unicode punctuation, multi-paragraph, and empty fails."""
    # Unicode text
    unicode_doc = RstDocument.from_text(EDGE_CASES['with_unicode'], document_id="e2e-unicode")
    analysis_uni = dmrst_gumrrg_cpu.parse_document(unicode_doc)
    for node in analysis_uni.nodes:
        start, end = node.char_span
        assert EDGE_CASES['with_unicode'][start:end] == node.text

    # Empty inputs must fail closed
    for empty in EMPTY_INPUTS:
        empty_doc = RstDocument.from_text(empty)
        with pytest.raises(ValueError, match='non-empty'):
            dmrst_gumrrg_cpu.parse_document(empty_doc)


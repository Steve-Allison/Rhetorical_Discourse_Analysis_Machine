"""End-to-end smoke test for both parser families.

Run after any predictor change:

    pixi run python scripts/smoke_test.py
    pixi run python scripts/smoke_test.py --quick   # gumrrg + unirst only
    pixi run python scripts/smoke_test.py --full    # all 5 hf_model_versions

Verifies:
  - Both families load on CPU through the public ``Parser`` façade.
  - ``parse_rst`` returns a tree whose every node aligns to the original text.
  - ``parse_from_edus`` round-trips: leaves equal the input EDUs.
  - Façade dispatch: ``family=`` override, ``hf_model_version`` routing,
    ``model_dir`` auto-detection.
  - Façade error paths raise the documented exceptions.
  - Edge cases: 1-EDU input, ``<3`` token early-return, malformed EDU input,
    ``_guess_token_offsets`` raise-on-miss in real flow.
"""

import argparse
import json
import pickle
import sys
import tempfile
import traceback
from collections.abc import Callable, Sequence
from pathlib import Path

from huggingface_hub.errors import EntryNotFoundError

from isanlp_rst.parser import Parser


SAMPLE_TEXT = "The cat sat on the mat. It was a black cat. The mat was red."
SAMPLE_EDUS: Sequence[str] = (
    "The cat sat on the mat.",
    "It was a black cat.",
    "The mat was red.",
)
QUICK_VERSIONS = ('gumrrg', 'unirst')
FULL_VERSIONS = ('gumrrg', 'rstdt', 'rstreebank', 'rrtrrg', 'unirst')

# Load failures from Parser() / HF download / torch / UniRST pickle import.
_LOAD_ERRORS = (
    OSError,
    RuntimeError,
    ValueError,
    EntryNotFoundError,
    pickle.UnpicklingError,
)
# Named-check failures: asserts plus parse/payload errors after a successful load.
_CHECK_ERRORS = (
    AssertionError,
    KeyError,
    IndexError,
    OSError,
    RuntimeError,
    TypeError,
    ValueError,
)

failures: list[str] = []


def _check(name: str, fn: Callable[[], None]) -> None:
    print(f"  • {name} ... ", end='', flush=True)
    try:
        fn()
    except _CHECK_ERRORS:
        failures.append(name)
        print('FAIL')
        traceback.print_exc()
    else:
        print('OK')


def _assert_tree_aligned(tree, original_text: str, path: str = "root") -> None:
    assert 0 <= tree.start <= tree.end <= len(original_text), (
        f"{path}: bad bounds ({tree.start}, {tree.end}) for text len {len(original_text)}"
    )
    expected = original_text[tree.start : tree.end]
    assert tree.text == expected, (
        f"{path}: tree.text={tree.text!r} != "
        f"original_text[{tree.start}:{tree.end}]={expected!r}"
    )
    left = getattr(tree, "left", None)
    right = getattr(tree, "right", None)
    if left is not None:
        _assert_tree_aligned(left, original_text, f"{path}.left")
    if right is not None:
        _assert_tree_aligned(right, original_text, f"{path}.right")


def _collect_leaves(tree) -> list[str]:
    leaves: list[str] = []

    def walk(unit) -> None:
        left = getattr(unit, "left", None)
        right = getattr(unit, "right", None)
        if left is None and right is None:
            leaves.append(unit.text)
            return
        if left is not None:
            walk(left)
        if right is not None:
            walk(right)

    walk(tree)
    return leaves


# ---- Façade error/dispatch tests (no model load) ----


def test_facade_no_args() -> None:
    try:
        Parser()
    except ValueError as exc:
        assert 'hf_model_version' in str(exc) or 'model_dir' in str(exc), str(exc)
    else:
        raise AssertionError("Parser() should raise ValueError")


def test_facade_bad_version() -> None:
    try:
        Parser(hf_model_version='not-a-real-version')
    except ValueError as exc:
        assert 'Unknown hf_model_version' in str(exc), str(exc)
    else:
        raise AssertionError("Parser(hf_model_version='nope') should raise")


def test_facade_bad_family() -> None:
    try:
        Parser(family='not-a-family', hf_model_version='gumrrg')
    except ValueError as exc:
        assert 'Unknown family' in str(exc), str(exc)
    else:
        raise AssertionError("Parser(family='nope') should raise")


def test_facade_empty_model_dir() -> None:
    try:
        Parser(model_dir='/tmp/__definitely_not_a_model__', hf_model_name=None)
    except ValueError as exc:
        assert 'auto-detect' in str(exc), str(exc)
    else:
        raise AssertionError("Parser(model_dir=<empty>) should raise")


def test_facade_detect_dmrst_local(tmp_dir: Path) -> None:
    """Auto-detect DMRST signature from a local dir containing relation_table.txt."""
    family = Parser._detect_family_from_model_dir(str(tmp_dir / 'dmrst_dir'))
    assert family == 'dmrst', f"expected 'dmrst', got {family!r}"


def test_facade_detect_unirst_local(tmp_dir: Path) -> None:
    """Auto-detect UniRST signature from data_manager_*.pickle."""
    family = Parser._detect_family_from_model_dir(str(tmp_dir / 'unirst_dir'))
    assert family == 'unirst', f"expected 'unirst', got {family!r}"


def test_facade_detect_unirst_via_config(tmp_dir: Path) -> None:
    """Auto-detect UniRST signature from config.json data.corpora."""
    family = Parser._detect_family_from_model_dir(str(tmp_dir / 'unirst_via_config'))
    assert family == 'unirst', f"expected 'unirst', got {family!r}"


def _seed_detection_dirs(base: Path) -> None:
    dmrst_dir = base / 'dmrst_dir'
    dmrst_dir.mkdir(exist_ok=True)
    (dmrst_dir / 'relation_table.txt').write_text(
        'elaboration\ncontrast\n', encoding='utf-8',
    )

    unirst_dir = base / 'unirst_dir'
    unirst_dir.mkdir(exist_ok=True)
    (unirst_dir / 'data_manager_eng.rst.gum.pickle').write_bytes(b'fake')

    config_dir = base / 'unirst_via_config'
    config_dir.mkdir(exist_ok=True)
    (config_dir / 'config.json').write_text(
        json.dumps({'data': {'corpora': ['eng.rst.rstdt']}}),
        encoding='utf-8',
    )


# ---- Family-level integration tests ----


def _run_family(version: str, device: str = 'cpu', dtype=None, **extras) -> None:
    """Load via Parser façade, parse_rst + parse_from_edus + edge cases."""
    print(f"\n=== {version} (device={device}, dtype={dtype}) ===", flush=True)
    parser = Parser(hf_model_name='tchewik/isanlp_rst_v3',
                    hf_model_version=version,
                    device=device,
                    dtype=dtype,
                    **extras)
    print(f"  device: {parser.predictor._device}, "
          f"dtype: {parser.predictor._dtype}")

    _check('parse_rst basic', lambda: _check_parse_rst(parser, SAMPLE_TEXT))
    _check('parse_rst tiny (<3 tokens)', lambda: _check_parse_rst(parser, "Hi."))
    _check('parse_from_edus round-trip',
           lambda: _check_from_edus(parser, list(SAMPLE_EDUS)))
    _check('parse_from_edus single EDU',
           lambda: _check_from_edus(parser, ["Just one EDU here."]))
    _check('parse_from_edus empty raises',
           lambda: _expect_raises(lambda: parser.from_edus([]), ValueError))
    _check('parse_from_edus empty-string EDU raises',
           lambda: _expect_raises(lambda: parser.from_edus(['ok', '']), ValueError))
    _check('parse_from_edus string-not-list raises',
           lambda: _expect_raises(lambda: parser.from_edus('a single string'), TypeError))


def _check_parse_rst(parser, text: str) -> None:
    res = parser(text)
    tree = res['rst'][0]
    _assert_tree_aligned(tree, text)


def _check_from_edus(parser, edus: list[str]) -> None:
    res = parser.from_edus(edus)
    leaves = _collect_leaves(res['rst'][0])
    assert leaves == edus, f"leaves {leaves} != input {edus}"


def _expect_raises(fn, exc_cls) -> None:
    try:
        fn()
    except exc_cls:
        return
    raise AssertionError(f"expected {exc_cls.__name__}, no exception raised")


# ---- UniRST-specific: _guess_token_offsets raise-on-miss in real flow ----


def test_unirst_guess_offsets_raises(unirst_predictor) -> None:
    """When pre-tokenized words don't appear in the text, parse_rst must raise.

    Exercises ``BasePredictor._guess_token_offsets`` via the only public path
    that uses it: ``PredictorUniRST.parse_rst(text, tokens=[...])`` without
    ``token_offsets``.
    """
    text = "hello world"
    bad_tokens = ['hello', 'NOPE']
    try:
        unirst_predictor.parse_rst(text, tokens=bad_tokens)
    except ValueError as exc:
        assert 'Cannot locate token' in str(exc), str(exc)
        return
    raise AssertionError("Expected ValueError from _guess_token_offsets miss")


# ---- Main ----


def main() -> int:
    ap = argparse.ArgumentParser()
    grp = ap.add_mutually_exclusive_group()
    grp.add_argument('--quick', action='store_true', help='gumrrg + unirst only (default)')
    grp.add_argument('--full', action='store_true', help='all 5 hf_model_versions')
    ap.add_argument('--device', default='cpu',
                    help="Compute device: 'auto'|'cpu'|'mps'|'cuda'|'cuda:N' "
                         "(default: cpu). 'auto' picks CUDA, else MPS, else CPU.")
    ap.add_argument('--dtype', default=None,
                    help='Inference dtype: fp32/fp16/bf16 (default: fp32 on '
                         'every device). Tree shape is bit-equivalent across '
                         'all three.')
    args = ap.parse_args()

    versions = FULL_VERSIONS if args.full else QUICK_VERSIONS

    print("=== Façade dispatch & error paths (no model load) ===", flush=True)
    _check('Parser() with no args raises', test_facade_no_args)
    _check('Parser(hf_model_version=bad) raises', test_facade_bad_version)
    _check('Parser(family=bad) raises', test_facade_bad_family)
    _check('Parser(model_dir=empty) raises', test_facade_empty_model_dir)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        _seed_detection_dirs(tmp_path)
        _check('detect_family_from_model_dir DMRST',
               lambda: test_facade_detect_dmrst_local(tmp_path))
        _check('detect_family_from_model_dir UniRST (pickle)',
               lambda: test_facade_detect_unirst_local(tmp_path))
        _check('detect_family_from_model_dir UniRST (config.corpora)',
               lambda: test_facade_detect_unirst_via_config(tmp_path))

    print(f"\n=== Loading {len(versions)} model version(s): {versions} ===", flush=True)

    unirst_parser_for_offset_check: Parser | None = None

    for version in versions:
        extras = {'relinventory': 'eng.erst.gum'} if version == 'unirst' else {}
        try:
            _run_family(version, device=args.device, **extras)
            if version == 'unirst':
                unirst_parser_for_offset_check = Parser(
                    hf_model_name='tchewik/isanlp_rst_v3',
                    hf_model_version='unirst',
                    device=args.device,
                    relinventory='eng.erst.gum',
                )
        except _LOAD_ERRORS:
            failures.append(f'load:{version}')
            print(f'  LOAD FAILED for {version}')
            traceback.print_exc()

    if unirst_parser_for_offset_check is not None:
        print("\n=== _guess_token_offsets raise-on-miss (UniRST tokens path) ===",
              flush=True)
        _check('parse_rst with mismatched tokens raises ValueError',
               lambda: test_unirst_guess_offsets_raises(
                   unirst_parser_for_offset_check.predictor))

    print("\n" + "=" * 60)
    if failures:
        print(f"FAIL — {len(failures)} failure(s):")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("PASS — all checks succeeded")
    return 0


if __name__ == "__main__":
    sys.exit(main())

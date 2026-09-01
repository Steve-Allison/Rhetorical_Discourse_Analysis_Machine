"""End-to-end smoke test for the production ModernBERT parser family.

Run after any predictor change:

    pixi run smoke            # façade checks + the first discovered release, on CPU
    pixi run smoke-full       # every release in the store, on CPU
    pixi run smoke-mps        # first release, on MPS
    pixi run smoke-full-mps   # every release, on MPS

Only immutable local releases are loaded, through the public
``Parser.from_model_release`` façade from ``--store`` (default
``models/model-releases``). Nothing is downloaded. DMRST and UniRST are archived
from production (``isanlp_rst/parser.py``), so the smoke asserts that requesting
them fails deterministically instead of loading them.

Verifies:
  - Façade error paths raise the documented exceptions, including the archived
    legacy families and unsafe release identifiers.
  - Every release in the store validates, loads on the requested device, and
    reports a release identity matching its directory name.
  - ``parse_rst`` returns a tree whose every node aligns to the original text.
  - ``from_edus`` round-trips: leaves equal the input EDUs; malformed input raises.
  - ``parse_document`` yields an ``RstAnalysis`` whose canonical serialization
    round-trips byte-equal (serialized-contract compatibility, FR-011).
  - ``erst_graph`` output is produced by a validated completion bundle, or refused
    with ``ErstCapabilityError`` — never fabricated.
"""

import argparse
from collections.abc import Callable, Sequence
import json
from pathlib import Path
import sys
import tempfile
import traceback

from isanlp_rst.annotation_rst import DiscourseUnit
from isanlp_rst.contracts import OutputFormalismEnum, RstDocument, analysis_from_json, to_json
from isanlp_rst.erst import ErstCapabilityError
from isanlp_rst.model_loading.release import MODEL_RELEASE_MANIFEST, ModelReleaseError
from isanlp_rst.parser import Parser

SAMPLE_TEXT = "The cat sat on the mat. It was a black cat. The mat was red."
SAMPLE_EDUS: Sequence[str] = (
    "The cat sat on the mat.",
    "It was a black cat.",
    "The mat was red.",
)
MODERNBERT_RUNTIME_CONTRACT = "isanlp_rst.parser/modernbert-v1"
DEFAULT_STORE = Path("models/model-releases")

# Load failures from release validation, safetensors loading, torch, or the façade.
_LOAD_ERRORS = (
    ModelReleaseError,
    OSError,
    RuntimeError,
    ValueError,
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
    print(f"  • {name} ... ", end="", flush=True)
    try:
        fn()
    except _CHECK_ERRORS:
        failures.append(name)
        print("FAIL")
        traceback.print_exc()
    else:
        print("OK")


def _expect_raises(fn: Callable[[], object], exc_cls: type[BaseException], fragment: str) -> None:
    try:
        fn()
    except exc_cls as exc:
        assert fragment in str(exc), f"expected {fragment!r} in {exc_cls.__name__}: {exc}"
        return
    raise AssertionError(f"expected {exc_cls.__name__} containing {fragment!r}; no exception raised")


def _assert_tree_aligned(tree: DiscourseUnit, original_text: str, path: str = "root") -> None:
    start, end = tree.start, tree.end
    assert start is not None and end is not None, f"{path}: node carries no original-text offsets"
    assert 0 <= start <= end <= len(original_text), (
        f"{path}: bad bounds ({start}, {end}) for text len {len(original_text)}"
    )
    expected = original_text[start:end]
    assert tree.text == expected, f"{path}: tree.text={tree.text!r} != original_text[{start}:{end}]={expected!r}"
    if tree.left is not None:
        _assert_tree_aligned(tree.left, original_text, f"{path}.left")
    if tree.right is not None:
        _assert_tree_aligned(tree.right, original_text, f"{path}.right")


def _collect_leaves(tree: DiscourseUnit) -> list[str]:
    leaves: list[str] = []

    def walk(unit: DiscourseUnit) -> None:
        if unit.left is None and unit.right is None:
            leaves.append(unit.text)
            return
        if unit.left is not None:
            walk(unit.left)
        if unit.right is not None:
            walk(unit.right)

    walk(tree)
    return leaves


# ---- Façade error/dispatch checks (no model load) ----


def _facade_checks(store: Path) -> None:
    _check(
        "Parser() with no args raises",
        lambda: _expect_raises(Parser, ValueError, "hf_model_version"),
    )
    _check(
        "Parser(hf_model_version=bad) raises",
        lambda: _expect_raises(lambda: Parser(hf_model_version="not-a-real-version"), ValueError, "Unknown hf_model_version"),
    )
    _check(
        "archived DMRST version is refused without loading",
        lambda: _expect_raises(lambda: Parser(hf_model_version="gumrrg"), ValueError, "archived from production"),
    )
    _check(
        "archived UniRST version is refused without loading",
        lambda: _expect_raises(lambda: Parser(hf_model_version="unirst"), ValueError, "archived from production"),
    )
    _check(
        "Parser(family=bad) raises",
        lambda: _expect_raises(
            lambda: Parser(family="not-a-family", hf_model_version="modernbert"), ValueError, "Unknown family"
        ),
    )
    with tempfile.TemporaryDirectory() as tmp:
        _check(
            "Parser(model_dir=empty) raises",
            lambda: _expect_raises(lambda: Parser(model_dir=tmp, hf_model_name=None), ValueError, "auto-detect"),
        )
    _check(
        "from_model_release rejects an unsafe release_id",
        lambda: _expect_raises(
            lambda: Parser.from_model_release(store, "../escape", family="modernbert"),
            ModelReleaseError,
            "unsafe release_id",
        ),
    )
    _check(
        "from_model_release rejects an unpromoted release_id",
        lambda: _expect_raises(
            lambda: Parser.from_model_release(store, "not-a-promoted-release", family="modernbert"),
            ModelReleaseError,
            "real local directory",
        ),
    )


# ---- Release discovery ----


def _discover_releases(store: Path) -> tuple[str, ...]:
    """Every store child carrying a manifest for the ModernBERT runtime contract.

    Discovery only reads the manifest's ``runtime_contract``; full validation happens
    on load, so a corrupt member is reported as a load failure rather than skipped.
    """

    if not store.is_dir():
        raise FileNotFoundError(f"model store does not exist: {store}")
    found: list[str] = []
    for child in sorted(store.iterdir()):
        manifest = child / MODEL_RELEASE_MANIFEST
        if not child.is_dir() or not manifest.is_file():
            continue
        try:
            contract = json.loads(manifest.read_bytes()).get("runtime_contract")
        except (OSError, ValueError):
            contract = None
        if contract == MODERNBERT_RUNTIME_CONTRACT or contract is None:
            found.append(child.name)
    return tuple(found)


# ---- Per-release checks ----


def _run_release(store: Path, release_id: str, *, device: str, dtype: str | None) -> None:
    print(f"\n=== {release_id} (device={device}, dtype={dtype}) ===", flush=True)
    parser = Parser.from_model_release(store, release_id, family="modernbert", device=device, dtype=dtype)
    print(f"  device: {parser.predictor._device}, dtype: {parser.predictor._dtype}")

    _check("release identity matches the store directory", lambda: _check_identity(parser, release_id))
    _check("parse_rst basic", lambda: _check_parse_rst(parser, SAMPLE_TEXT))
    _check("parse_rst single EDU", lambda: _check_parse_rst(parser, "Hi."))
    _check("from_edus round-trip", lambda: _check_from_edus(parser, list(SAMPLE_EDUS)))
    _check("from_edus single EDU", lambda: _check_from_edus(parser, ["Just one EDU here."]))
    _check(
        "from_edus empty raises",
        lambda: _expect_raises(lambda: parser.from_edus([]), ValueError, "non-empty"),
    )
    _check(
        "from_edus empty-string EDU raises",
        lambda: _expect_raises(lambda: parser.from_edus(["ok", ""]), ValueError, "EDU"),
    )
    _check("parse_document rst_tree serializes byte-equal after round-trip", lambda: _check_rst_tree_document(parser))
    _check("erst_graph is real or refused, never fabricated", lambda: _check_erst_graph(parser))


def _check_identity(parser: Parser, release_id: str) -> None:
    identity = parser.model_release_identity
    assert identity is not None, "released parser reports no model_release_identity"
    assert identity.release_id == release_id, f"identity {identity.release_id!r} != store name {release_id!r}"
    assert identity.runtime_contract == MODERNBERT_RUNTIME_CONTRACT, identity.runtime_contract


def _check_parse_rst(parser: Parser, text: str) -> None:
    tree = parser(text)["rst"][0]
    _assert_tree_aligned(tree, text)


def _check_from_edus(parser: Parser, edus: list[str]) -> None:
    leaves = _collect_leaves(parser.from_edus(edus)["rst"][0])
    assert leaves == edus, f"leaves {leaves} != input {edus}"


def _check_rst_tree_document(parser: Parser) -> None:
    document = RstDocument.from_text(SAMPLE_TEXT, document_id="smoke")
    analysis = parser.parse_document(document, output="rst_tree")
    assert analysis.formalism is OutputFormalismEnum.RST_TREE, analysis.formalism
    assert analysis.nodes, "rst_tree analysis has no nodes"
    serialized = to_json(analysis)
    assert to_json(analysis_from_json(serialized)) == serialized, "canonical serialization is not round-trip stable"


def _check_erst_graph(parser: Parser) -> None:
    document = RstDocument.from_text(SAMPLE_TEXT, document_id="smoke-erst")
    if parser.erst_checkpoint is None:
        _expect_raises(
            lambda: parser.parse_document(document, output="erst_graph"),
            ErstCapabilityError,
            "validated completion bundle",
        )
        print("(no bundle: refused) ", end="")
        return
    analysis = parser.parse_document(document, output="erst_graph")
    assert analysis.formalism is OutputFormalismEnum.ERST_GRAPH, analysis.formalism
    print("(bundle loaded) ", end="")


# ---- Main ----


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    grp = ap.add_mutually_exclusive_group()
    grp.add_argument("--quick", action="store_true", help="first discovered release only (default)")
    grp.add_argument("--full", action="store_true", help="every release in the store")
    ap.add_argument("--store", type=Path, default=DEFAULT_STORE, help=f"immutable release store (default: {DEFAULT_STORE})")
    ap.add_argument(
        "--device",
        default="cpu",
        help="Compute device: 'auto'|'cpu'|'mps'|'cuda'|'cuda:N' (default: cpu). 'auto' picks CUDA, else MPS, else CPU.",
    )
    ap.add_argument(
        "--dtype",
        default=None,
        help="Inference dtype passed to the predictor (default: the release's 'auto' resolution).",
    )
    args = ap.parse_args()
    store: Path = args.store.resolve()

    print("=== Façade dispatch & error paths (no model load) ===", flush=True)
    _facade_checks(store)

    try:
        releases = _discover_releases(store)
    except FileNotFoundError as exc:
        failures.append("store:missing")
        print(f"\nFAIL — {exc}")
        return 1
    if not releases:
        failures.append("store:empty")
        print(f"\nFAIL — no ModernBERT releases found in {store}")
        return 1
    selected = releases if args.full else releases[:1]
    print(f"\n=== Loading {len(selected)} of {len(releases)} release(s) from {store}: {selected} ===", flush=True)

    for release_id in selected:
        try:
            _run_release(store, release_id, device=args.device, dtype=args.dtype)
        except _LOAD_ERRORS:
            failures.append(f"load:{release_id}")
            print(f"  LOAD FAILED for {release_id}")
            traceback.print_exc()

    print("\n" + "=" * 60)
    if failures:
        print(f"FAIL — {len(failures)} failure(s):")
        for name in failures:
            print(f"  - {name}")
        return 1
    print("PASS — all checks succeeded")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Production smoke: every ModernBERT release in the local store, on every available device.

This replaces the former ``scripts/smoke_test.py`` and ``scripts/cuda_smoke.py`` so the
smoke runs under ``pixi run test-all`` (and ``pixi run smoke``) and cannot rot unnoticed.
Releases are loaded only through the public ``Parser.from_model_release`` façade from
``models/model-releases``; nothing is downloaded. The archived DMRST and UniRST families
are asserted to be *refused*, never loaded.

The model-loading tests are ``slow`` and skip, visibly, when the local store holds no
release — which is the case on CI, where model weights are not in git.
"""

import json
from pathlib import Path

import pytest
import torch

from rdam.rst.annotation_rst import DiscourseUnit
from rdam.rst.contracts import OutputFormalismEnum, RstDocument, analysis_from_json, to_json
from rdam.rst.erst import ErstCapabilityError
from rdam.rst.model_loading.release import MODEL_RELEASE_MANIFEST, ModelReleaseError
from rdam.rst.parser import Parser

STORE = Path(__file__).resolve().parents[2] / "models" / "model-releases"
MODERNBERT_RUNTIME_CONTRACT = "isanlp_rst.parser/modernbert-v1"
ARCHIVED_VERSIONS = ("gumrrg", "rstdt", "rstreebank", "rrtrrg", "unirst")
SAMPLE_TEXT = "The cat sat on the mat. It was a black cat. The mat was red."
SAMPLE_EDUS = ["The cat sat on the mat.", "It was a black cat.", "The mat was red."]


def _releases(store: Path) -> tuple[str, ...]:
    """Every store child carrying a manifest for the ModernBERT runtime contract.

    Discovery reads only ``runtime_contract``; full validation happens on load, so a
    corrupt member fails its load test rather than being skipped.
    """

    if not store.is_dir():
        return ()
    found: list[str] = []
    for child in sorted(store.iterdir()):
        manifest = child / MODEL_RELEASE_MANIFEST
        if not child.is_dir() or not manifest.is_file():
            continue
        try:
            contract = json.loads(manifest.read_bytes()).get("runtime_contract")
        except (OSError, ValueError):
            contract = None
        if contract in (MODERNBERT_RUNTIME_CONTRACT, None):
            found.append(child.name)
    return tuple(found)


def _devices() -> tuple[str, ...]:
    devices = ["cpu"]
    if torch.backends.mps.is_available():
        devices.append("mps")
    if torch.cuda.is_available():
        devices.append("cuda")
    return tuple(devices)


RELEASES = _releases(STORE)
DEVICES = _devices()


def _assert_aligned(tree: DiscourseUnit, text: str, path: str = "root") -> None:
    start, end = tree.start, tree.end
    assert start is not None and end is not None, f"{path}: node carries no original-text offsets"
    assert 0 <= start <= end <= len(text), f"{path}: bad bounds ({start}, {end}) for text len {len(text)}"
    assert tree.text == text[start:end], f"{path}: tree.text={tree.text!r} != text[{start}:{end}]"
    if tree.left is not None:
        _assert_aligned(tree.left, text, f"{path}.left")
    if tree.right is not None:
        _assert_aligned(tree.right, text, f"{path}.right")


def _leaves(tree: DiscourseUnit) -> list[str]:
    if tree.left is None and tree.right is None:
        return [tree.text]
    leaves: list[str] = []
    if tree.left is not None:
        leaves.extend(_leaves(tree.left))
    if tree.right is not None:
        leaves.extend(_leaves(tree.right))
    return leaves


# ---- Façade refusals: fast, no model load ----


class TestFacadeRefusals:
    def test_unknown_version_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="Unknown hf_model_version"):
            Parser(hf_model_version="nonexistent-version")

    def test_unknown_family_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="Unknown family"):
            Parser(family="nonexistent-family", hf_model_version="gumrrg")

    def test_unsafe_release_id_is_rejected(self, tmp_path: Path) -> None:
        with pytest.raises(ModelReleaseError, match="unsafe release_id"):
            Parser.from_model_release(tmp_path, "../escape", family="dmrst")

    def test_unpromoted_release_id_is_rejected(self, tmp_path: Path) -> None:
        with pytest.raises(ModelReleaseError, match="real local directory"):
            Parser.from_model_release(tmp_path, "not-a-promoted-release", family="dmrst")


# ---- Release smoke: slow, one load per (release, device) ----


@pytest.fixture(
    scope="module",
    params=[(release, device) for release in RELEASES for device in DEVICES],
    ids=[f"{release}@{device}" for release in RELEASES for device in DEVICES],
)
def loaded(request: pytest.FixtureRequest) -> tuple[Parser, str, str]:
    release_id, device = request.param
    parser = Parser.from_model_release(STORE, release_id, family="modernbert", device=device)
    return parser, release_id, device


@pytest.mark.slow
class TestReleaseSmoke:
    def test_loads_on_requested_device_with_matching_identity(self, loaded: tuple[Parser, str, str]) -> None:
        parser, release_id, device = loaded
        assert parser.predictor._device.type == device
        identity = parser.model_release_identity
        assert identity is not None, "released parser reports no model_release_identity"
        assert identity.release_id == release_id
        assert identity.runtime_contract == MODERNBERT_RUNTIME_CONTRACT

    def test_parse_rst_aligns_every_node_to_the_text(self, loaded: tuple[Parser, str, str]) -> None:
        parser, _, _ = loaded
        _assert_aligned(parser(SAMPLE_TEXT)["rst"][0], SAMPLE_TEXT)

    def test_parse_rst_single_edu(self, loaded: tuple[Parser, str, str]) -> None:
        parser, _, _ = loaded
        _assert_aligned(parser("Hi.")["rst"][0], "Hi.")

    def test_from_edus_round_trips_leaves(self, loaded: tuple[Parser, str, str]) -> None:
        parser, _, _ = loaded
        assert _leaves(parser.from_edus(SAMPLE_EDUS)["rst"][0]) == SAMPLE_EDUS

    def test_from_edus_single_edu(self, loaded: tuple[Parser, str, str]) -> None:
        parser, _, _ = loaded
        assert _leaves(parser.from_edus(["Just one EDU here."])["rst"][0]) == ["Just one EDU here."]

    def test_from_edus_rejects_empty_input(self, loaded: tuple[Parser, str, str]) -> None:
        parser, _, _ = loaded
        with pytest.raises(ValueError, match="non-empty"):
            parser.from_edus([])

    def test_from_edus_rejects_empty_string_edu(self, loaded: tuple[Parser, str, str]) -> None:
        parser, _, _ = loaded
        with pytest.raises(ValueError, match="EDU"):
            parser.from_edus(["ok", ""])

    def test_rst_tree_document_serializes_byte_equal_after_round_trip(self, loaded: tuple[Parser, str, str]) -> None:
        parser, _, _ = loaded
        analysis = parser.parse_document(RstDocument.from_text(SAMPLE_TEXT, document_id="smoke"), output="rst_tree")
        assert analysis.formalism is OutputFormalismEnum.RST_TREE
        assert analysis.nodes
        serialized = to_json(analysis)
        assert to_json(analysis_from_json(serialized)) == serialized

    def test_erst_graph_is_real_or_refused_never_fabricated(self, loaded: tuple[Parser, str, str]) -> None:
        parser, _, _ = loaded
        document = RstDocument.from_text(SAMPLE_TEXT, document_id="smoke-erst")
        if parser.erst_checkpoint is None:
            with pytest.raises(ErstCapabilityError, match="validated completion bundle"):
                parser.parse_document(document, output="erst_graph")
            return
        assert parser.parse_document(document, output="erst_graph").formalism is OutputFormalismEnum.ERST_GRAPH

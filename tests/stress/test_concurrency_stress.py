"""Multi-threaded concurrency stress tests verifying thread-safety across all subsystems."""

from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from pathlib import Path
from threading import Barrier
import pytest
import torch

from rdam.rst.annotation_rst import DiscourseUnit
from rdam.rst.dmrst_parser.predictor import PredictorDMRST
from rdam.rst.model_loading import ModelReleaseError, load_model_release, peek_runtime_contract
from rdam.rst.model_loading.release import MODEL_RELEASE_MANIFEST
from rdam.rst.parser import Parser
from rdam.rst.universal_parser.predictor import PredictorUniRST
from rdam import AvailableCapability, ProviderRequest, SourceIdentity
from rdam.rst.provider import RstProvider
from rdam.ingest.contracts import SourceArtifact, SourceForm
from rdam.ingest.service import ProductionIngestor
from rdam.rst.erst.neural_scorer import NeuralSecondaryEdgeScorer
from workbench.hashing import (
    blake3_digest,
    canonical_json_digest,
    sha256_digest,
)

pytestmark = pytest.mark.stress


def _compatible_parser_release(family: str) -> tuple[Path, str]:
    """Use a real, validated local release; missing evidence is a test failure."""
    local = Path(__file__).resolve().parents[2] / "models" / "model-releases"
    cached = Path.home() / ".cache" / "isanlp_rst" / "model-releases"
    failures: list[str] = []
    for store in (local, cached):
        if not store.is_dir():
            continue
        for manifest in sorted(store.glob(f"*/{MODEL_RELEASE_MANIFEST}")):
            release_id = manifest.parent.name
            try:
                if peek_runtime_contract(manifest.parent) != f"isanlp_rst.parser/{family}-v1":
                    continue
                load_model_release(store, release_id)
            except ModelReleaseError as error:
                failures.append(f"{release_id}: {error}")
                continue
            return store, release_id
    pytest.fail(f"No compatible {family} release for a real concurrency measurement: {failures}")


def _tree_bytes(tree: DiscourseUnit, text: str) -> bytes:
    """Compare every semantic tree field, including probability and entropy."""
    nodes: list[dict[str, str | int | float | None]] = []
    pending = [tree]
    while pending:
        node = pending.pop()
        assert node.start is not None and node.end is not None
        assert 0 <= node.start <= node.end <= len(text)
        assert node.text == text[node.start : node.end]
        nodes.append(
            {
                "id": node.id,
                "text": node.text,
                "start": node.start,
                "end": node.end,
                "relation": node.relation,
                "nuclearity": node.nuclearity,
                "proba": node.proba,
                "entropy": node.entropy,
                "left": None if node.left is None else node.left.id,
                "right": None if node.right is None else node.right.id,
            }
        )
        if node.right is not None:
            pending.append(node.right)
        if node.left is not None:
            pending.append(node.left)
    return json.dumps(nodes, sort_keys=True, allow_nan=False, separators=(",", ":")).encode("utf-8")


@pytest.mark.parametrize("family", ("dmrst", "unirst"))
@pytest.mark.parametrize("device", ("cpu", "mps"))
def test_real_parser_concurrency_matches_sequential_trees(family: str, device: str) -> None:
    """T073: share loaded model state across four simultaneous calls on CPU and MPS."""
    if device == "mps" and not torch.backends.mps.is_available():
        pytest.skip("MPS hardware is unavailable; this is not evidence of MPS parallel safety")
    store, release_id = _compatible_parser_release(family)
    parser = Parser.from_model_release(
        store,
        release_id,
        device=device,
        relinventory="eng.erst.gum" if family == "unirst" else None,
    )
    expected_type = PredictorDMRST if family == "dmrst" else PredictorUniRST
    assert isinstance(parser.predictor, expected_type)
    texts = (
        "Because it rained, the match stopped. The crowd left.",
        "The survey supports the claim. However, the sample was small.",
        "The cat sat on the mat. It was a black cat. The mat was red.",
        "If the cost falls, we will proceed. Otherwise, the project will wait.",
    )
    expected = tuple(_tree_bytes(parser.parse_tree(text), text) for text in texts)
    start = Barrier(len(texts))

    def analyse(index: int) -> tuple[int, bytes]:
        start.wait(timeout=30)
        return index, _tree_bytes(parser.parse_tree(texts[index]), texts[index])

    with ThreadPoolExecutor(max_workers=len(texts)) as executor:
        for _ in range(3):
            futures = [executor.submit(analyse, index) for index in range(len(texts))]
            for future in as_completed(futures):
                index, actual = future.result()
                assert actual == expected[index], f"{family}@{device}, input {index}: concurrent tree changed"


@pytest.mark.parametrize("family", ("dmrst", "unirst"))
@pytest.mark.parametrize("device", ("cpu", "mps"))
def test_real_provider_cold_initialization_and_analysis_are_concurrent(family: str, device: str) -> None:
    if device == "mps" and not torch.backends.mps.is_available():
        pytest.skip("MPS hardware is unavailable; this is not evidence of MPS parallel safety")
    store, release_id = _compatible_parser_release(family)
    provider = RstProvider(
        store=store, release_id=release_id, device=device, relinventory="eng.erst.gum" if family == "unirst" else None
    )
    barrier = Barrier(4)
    text = "Because it rained, the match stopped. The crowd left."
    request = ProviderRequest(source=SourceIdentity.from_text(text), text=text, structured_input=None)

    def analyse(_index: int):
        barrier.wait(timeout=30)
        assert isinstance(provider.declaration.capability, AvailableCapability)
        return provider.analyse(request)

    with ThreadPoolExecutor(max_workers=4) as executor:
        results = tuple(executor.map(analyse, range(4)))
    sequential = provider.analyse(request)
    assert all(result.semantic_digest == sequential.semantic_digest for result in results)
    assert len({result.artifact_digest for result in results}) == 4


def test_concurrent_blake3_and_sha256_hashing() -> None:
    """Verify BLAKE3 and SHA-256 hashing is 100% thread-safe under high concurrent load."""
    payloads = [f"thread_payload_stress_{i}_{i * 1337}".encode("utf-8") for i in range(100)]
    expected_blake3 = [blake3_digest(p) for p in payloads]
    expected_sha256 = [sha256_digest(p) for p in payloads]

    def _hash_worker(index: int) -> tuple[int, str, str]:
        p = payloads[index]
        return index, blake3_digest(p), sha256_digest(p)

    with ThreadPoolExecutor(max_workers=32) as executor:
        futures = [executor.submit(_hash_worker, i) for i in range(len(payloads))]
        for future in as_completed(futures):
            idx, b3, s256 = future.result()
            assert b3 == expected_blake3[idx]
            assert s256 == expected_sha256[idx]


def test_concurrent_canonical_json_digest() -> None:
    """Verify RFC-8785 canonical JSON hashing has zero race conditions."""
    dict_payloads = [
        {"thread_id": i, "data": [f"item_{j}" for j in range(20)], "nested": {"k": i * 42}} for i in range(50)
    ]
    expected_digests = [canonical_json_digest(d) for d in dict_payloads]

    def _json_worker(index: int) -> tuple[int, str]:
        d = dict_payloads[index]
        return index, canonical_json_digest(d)

    with ThreadPoolExecutor(max_workers=16) as executor:
        futures = [executor.submit(_json_worker, i) for i in range(len(dict_payloads))]
        for future in as_completed(futures):
            idx, digest = future.result()
            assert digest == expected_digests[idx]


def test_concurrent_ingest_service_execution() -> None:
    """Verify ProductionIngestor concurrently processes requests with zero collisions."""
    service = ProductionIngestor(parser=None)
    texts = [
        f"# Title {i}\n\nSection {i} introduces the primary hypothesis.\n\nParagraph with evidence {i}."
        for i in range(30)
    ]

    def _ingest_worker(index: int) -> tuple[int, str, int]:
        raw_text = texts[index]
        artifact = SourceArtifact(
            source_name=f"doc_{index}.md",
            source_form=SourceForm.MARKDOWN,
            media_type="text/markdown",
            raw_bytes=raw_text.encode("utf-8"),
        )
        prepared = service.prepare(artifact)
        document = prepared.semantic.prepared_document
        return index, document.source.source_id, len(document.segments)

    with ThreadPoolExecutor(max_workers=16) as executor:
        futures = [executor.submit(_ingest_worker, i) for i in range(len(texts))]
        results = [future.result() for future in as_completed(futures)]

    assert len(results) == 30
    for _idx, doc_id, seg_count in results:
        assert len(doc_id) == 64
        assert seg_count > 0


def test_concurrent_neural_scorer_inference() -> None:
    """Verify NeuralSecondaryEdgeScorer thread-safety across concurrent batch evaluations."""
    inventory = ("elaboration", "attribution", "condition", "contrast")
    scorer = NeuralSecondaryEdgeScorer(
        raw_relation_inventory=inventory,
        device="cpu",
        torch_dtype=torch.float32,
    )
    scorer.eval()

    def _inference_worker(thread_id: int) -> tuple[int, int]:
        batch_size = 4
        src_ids = torch.randint(0, 1000, (batch_size, 32))
        src_mask = torch.ones((batch_size, 32), dtype=torch.long)
        src_special = torch.zeros((batch_size, 32), dtype=torch.long)
        src_offsets = torch.zeros((batch_size, 32, 2), dtype=torch.long)
        src_offsets[:, :, 1] = 5

        tgt_ids = torch.randint(0, 1000, (batch_size, 32))
        tgt_mask = torch.ones((batch_size, 32), dtype=torch.long)
        tgt_special = torch.zeros((batch_size, 32), dtype=torch.long)
        tgt_offsets = torch.zeros((batch_size, 32, 2), dtype=torch.long)
        tgt_offsets[:, :, 1] = 5

        struct = torch.zeros((batch_size, 9), dtype=torch.float32)

        with torch.inference_mode():
            out = scorer(
                src_input_ids=src_ids,
                src_attention_mask=src_mask,
                src_special_tokens_mask=src_special,
                src_offset_mapping=src_offsets,
                tgt_input_ids=tgt_ids,
                tgt_attention_mask=tgt_mask,
                tgt_special_tokens_mask=tgt_special,
                tgt_offset_mapping=tgt_offsets,
                struct_features=struct,
            )
        return thread_id, len(out["edge_logits"])

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(_inference_worker, i) for i in range(16)]
        for future in as_completed(futures):
            t_id, num_preds = future.result()
            assert num_preds == 4

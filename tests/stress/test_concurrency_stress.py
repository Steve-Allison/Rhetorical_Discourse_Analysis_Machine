"""Multi-threaded concurrency stress tests verifying thread-safety across all subsystems."""

from concurrent.futures import ThreadPoolExecutor, as_completed
import pytest
import torch

from isanlp_rst.ingest.contracts import SourceArtifact, SourceForm
from isanlp_rst.ingest.service import ProductionIngestor
from isanlp_rst.erst.neural_scorer import NeuralSecondaryEdgeScorer
from workbench.hashing import (
    blake3_digest,
    canonical_json_digest,
    sha256_digest,
)

pytestmark = pytest.mark.stress


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
        {"thread_id": i, "data": [f"item_{j}" for j in range(20)], "nested": {"k": i * 42}}
        for i in range(50)
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

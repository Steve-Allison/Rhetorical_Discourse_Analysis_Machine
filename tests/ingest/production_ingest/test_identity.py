from datetime import UTC, datetime

from isanlp_rst.ingest.contracts import CacheStatus, ExecutionReceipt, SourceArtifact, SourceForm
from isanlp_rst.ingest.identity import canonical_json_bytes, semantic_sha256


def test_canonical_json_is_order_independent_and_unicode_stable() -> None:
    left = {"z": "é", "a": [1, None, True]}
    right = {"a": [1, None, True], "z": "é"}
    assert canonical_json_bytes(left) == canonical_json_bytes(right)
    assert semantic_sha256(left) == semantic_sha256(right)


def test_complete_source_identity_changes_for_every_governed_dimension() -> None:
    base = SourceArtifact.from_bytes(
        b"same",
        source_form=SourceForm.TEXT,
        source_name="a.txt",
        media_type="text/plain",
        original_source="local:a",
    )
    variants = (
        SourceArtifact.from_bytes(b"different", source_form=SourceForm.TEXT, source_name="a.txt", media_type="text/plain", original_source="local:a"),
        SourceArtifact.from_bytes(b"same", source_form=SourceForm.TEXT, source_name="b.txt", media_type="text/plain", original_source="local:a"),
        SourceArtifact.from_bytes(b"same", source_form=SourceForm.MARKDOWN, source_name="a.txt", media_type="text/plain", original_source="local:a"),
        SourceArtifact.from_bytes(b"same", source_form=SourceForm.TEXT, source_name="a.txt", media_type="text/plain", original_source="local:b"),
    )
    assert all(item.source_id != base.source_id for item in variants)


def test_execution_observations_are_not_semantic_identity() -> None:
    first = ExecutionReceipt(run_id="a", started_at=datetime(2026, 1, 1, tzinfo=UTC), cache_status=CacheStatus.MISS)
    second = ExecutionReceipt(run_id="b", started_at=datetime(2026, 1, 2, tzinfo=UTC), cache_status=CacheStatus.HIT)
    assert first.semantic_payload() == second.semantic_payload() == {}

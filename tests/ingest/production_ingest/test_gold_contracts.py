from datetime import UTC, datetime
from pathlib import PurePosixPath

import pytest
from pydantic import ValidationError

from rdam.rst.ingest.contracts import SourceForm
from tools.production_ingest.contracts import (
    GoldSetManifest,
    GoldSource,
    ProvenanceClass,
    REQUIRED_RISKS,
)


def _source(index: int) -> GoldSource:
    forms = tuple(SourceForm)
    risks = tuple(REQUIRED_RISKS) if index in {0, 1} else ("clean_short_prose",)
    return GoldSource(
        source_id=f"gold-{index:02}",
        relative_path=PurePosixPath(f"sources/source-{index:02}.dat"),
        source_form=forms[index % len(forms)],
        sha256=f"{index + 1:064x}",
        size_bytes=100 + index,
        provenance_class=ProvenanceClass.REAL if index < 14 else ProvenanceClass.NORMATIVE,
        risk_classes=risks,
        expected_outcome="success",
        expectation_ref=PurePosixPath(f"expectations/gold-{index:02}.json"),
        rst_gold_ref=PurePosixPath(f"rst/gold-{index:02}.rs4") if index < 12 else None,
        redistributable=index >= 14,
    )


def test_gold_manifest_enforces_depth_forms_risks_and_rst_gold() -> None:
    manifest = GoldSetManifest(
        frozen_at=datetime(2026, 8, 25, tzinfo=UTC),
        sources=tuple(_source(index) for index in range(20)),
        expectation_digest="a" * 64,
    )
    assert len(manifest.sources) == 20
    assert manifest.rst_gold_count == 12


def test_gold_manifest_rejects_shallow_set() -> None:
    with pytest.raises(ValidationError, match="at least 20"):
        GoldSetManifest(
            frozen_at=datetime(2026, 8, 25, tzinfo=UTC),
            sources=tuple(_source(index) for index in range(19)),
            expectation_digest="a" * 64,
        )


def test_gold_contract_has_no_source_text_field() -> None:
    assert "text" not in GoldSource.model_fields

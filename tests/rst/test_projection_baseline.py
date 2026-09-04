"""The real RST provider's projection path preserves the immutable pre-feature evidence."""

from pathlib import Path

import pytest

from rdam import ProviderRequest, SourceIdentity, canonical_json_bytes, AggregateRequest, Machine, Technique, ExecutionPolicy
from rdam.rst.provider import RstProvider
from tests.integration.test_production_smoke import STORE
from tools.production_boundary.rst_baseline import DifferenceClass, TEXT, diff_records


@pytest.mark.slow
def test_real_rst_projection_matches_pre_feature_baseline() -> None:
    release_id = "gumrrg-eb1d5745f3a1"
    if not (STORE / release_id).is_dir():
        pytest.skip("the recorded Feature 017 baseline release is not installed")
    provider = RstProvider(store=STORE, release_id=release_id, device="cpu")
    result = provider.analyse(ProviderRequest(
        source=SourceIdentity.from_text(TEXT, source_name="baseline.txt"),
        text=TEXT,
        structured_input=None,
    ))
    baseline = Path("specs/017-universal-source-pipeline/evidence/baseline-dmrst-current/analyse-text.json")
    differences = diff_records(baseline.read_bytes(), canonical_json_bytes(result.payload))
    assert not [item for item in differences if item.classification is DifferenceClass.ANALYTICAL]


@pytest.mark.slow
def test_real_rst_aggregate_semantics_do_not_include_execution_timing() -> None:
    provider = RstProvider(store=STORE, release_id="gumrrg-eb1d5745f3a1", device="cpu")
    request = AggregateRequest.for_text(TEXT, (Technique.RST,))
    first = Machine([provider], execution_policy=ExecutionPolicy(max_workers=1)).analyse(request)
    second = Machine([provider], execution_policy=ExecutionPolicy(max_workers=4)).analyse(request)
    assert first.semantic_digest == second.semantic_digest

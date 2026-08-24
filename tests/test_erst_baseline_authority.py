"""Published eRST baseline authority and fail-closed blocker tests."""

from datetime import date

from pydantic import ValidationError
import pytest

from isanlp_rst.contracts.erst import CorpusLicenseClass, CorpusPartition
from isanlp_rst.contracts.research import (
    AuthoritySearchEvidence,
    BaselineAuthorityBlocker,
    BaselineCorpusSource,
    ErstBaselineAuthorityReceipt,
    ModelRevisionAuthority,
    ResearchArtifact,
)


def _sources() -> tuple[BaselineCorpusSource, ...]:
    partitions = (
        (CorpusPartition.TRAIN, 165),
        (CorpusPartition.DEV, 24),
        (CorpusPartition.TEST, 24),
    )
    sources: list[BaselineCorpusSource] = []
    index = 0
    for partition, count in partitions:
        for _ in range(count):
            sources.append(
                BaselineCorpusSource(
                    document_id=f"GUM_academic_doc{index:03d}",
                    source_path=f"rst/rstweb/GUM_academic_doc{index:03d}.rs4",
                    source_sha256=f"{index + 1:064x}",
                    partition=partition,
                    license_class=CorpusLicenseClass.CC_BY,
                )
            )
            index += 1
    return tuple(sources)


def _artifact(name: str, fill: str) -> ResearchArtifact:
    return ResearchArtifact(
        name=name,
        url=f"https://example.test/{name}",
        sha256=fill * 64,
        license="test-only",
    )


def _receipt(**overrides: object) -> ErstBaselineAuthorityReceipt:
    sources = _sources()
    values: dict[str, object] = {
        "assessed_on": date(2026, 8, 24),
        "paper": _artifact("paper", "a"),
        "baseline_code": _artifact("code", "b"),
        "baseline_model": ModelRevisionAuthority(
            model_id="google/electra-base-discriminator",
            revision="c" * 40,
            license="Apache-2.0",
        ),
        "corpus_revision": "d" * 40,
        "corpus_tree": "e" * 40,
        "splits_sha256": "f" * 64,
        "license_inventory_sha256": "1" * 64,
        "sources": sources,
        "partition_counts": {
            CorpusPartition.TRAIN: 165,
            CorpusPartition.DEV: 24,
            CorpusPartition.TEST: 24,
        },
        "official_scorer": None,
        "scorer_parity_receipt_sha256": None,
        "released_checkpoint": None,
        "released_environment_pins": (),
        "searched_surfaces": (
            AuthoritySearchEvidence(
                surface_url="https://example.test/release",
                checked_resource="complete test release",
                result="no scorer",
                checked_on=date(2026, 8, 24),
            ),
        ),
        "discrepancies": ("No scorer artifact.",),
        "blockers": (
            BaselineAuthorityBlocker.OFFICIAL_SCORER_UNAVAILABLE,
            BaselineAuthorityBlocker.SCORER_PARITY_UNVERIFIED,
        ),
        "ready_for_reproduction": False,
    }
    values.update(overrides)
    return ErstBaselineAuthorityReceipt.model_validate(values)


def test_unresolved_authority_round_trips_with_stable_hash() -> None:
    receipt = _receipt()
    assert not receipt.ready_for_reproduction
    assert len(receipt.sources) == 213
    assert ErstBaselineAuthorityReceipt.model_validate_json(receipt.model_dump_json()) == receipt


def test_missing_scorer_and_parity_require_explicit_blockers() -> None:
    with pytest.raises(ValidationError, match="unavailable blocker"):
        _receipt(blockers=(BaselineAuthorityBlocker.SCORER_PARITY_UNVERIFIED,))
    with pytest.raises(ValidationError, match="unverified blocker"):
        _receipt(blockers=(BaselineAuthorityBlocker.OFFICIAL_SCORER_UNAVAILABLE,))


def test_ready_authority_requires_scorer_parity_and_zero_blockers() -> None:
    receipt = _receipt(
        official_scorer=_artifact("scorer", "2"),
        scorer_parity_receipt_sha256="3" * 64,
        blockers=(),
        ready_for_reproduction=True,
    )
    assert receipt.ready_for_reproduction


def test_partition_counts_are_exact_and_source_hashes_are_disjoint() -> None:
    with pytest.raises(ValidationError, match="165/24/24"):
        _receipt(partition_counts={CorpusPartition.TRAIN: 164})

    sources = list(_sources())
    sources[1] = sources[1].model_copy(update={"source_sha256": sources[0].source_sha256})
    with pytest.raises(ValidationError, match="source hashes"):
        _receipt(sources=tuple(sources))

"""No-waiver production-ingest promotion decision assembly."""

from datetime import UTC, datetime
from pathlib import Path
import subprocess

from rdam.ingest import WRITE_CONTRACT_VERSION
from rdam.ingest.policy import DEFAULT_PREPARATION_POLICY
from rdam.ingest.identity import semantic_sha256, sha256_file
from rdam.rst.model_loading import ParserCapacity, validate_model_release
from tools.production_ingest.contracts import CandidateIdentity, PromotionDecision, SourceGateResult


def build_promotion_decision(
    *,
    repository_root: Path,
    wheel: Path,
    model_release: Path,
    source_results: tuple[SourceGateResult, ...],
) -> PromotionDecision:
    """Build the bounded decision directly from complete source gates."""

    revision = _git(repository_root, "rev-parse", "HEAD")
    dirty = bool(_git(repository_root, "status", "--porcelain", "--untracked-files=no"))
    release = validate_model_release(
        model_release,
        expected_runtime_contract="isanlp_rst.parser/modernbert-v1",
    )
    candidate = CandidateIdentity(
        git_commit=revision,
        git_dirty=dirty,
        wheel_sha256=sha256_file(wheel),
        model_release_id=release.manifest.release_id,
        model_digest=release.analysis_identity(
            ParserCapacity(
                unit="edu_count",
                maximum=512,
                source="isanlp_rst.parser/recursive-v1",
            )
        ).semantic_digest,
        policy_digest=semantic_sha256(DEFAULT_PREPARATION_POLICY),
        result_contract_version=WRITE_CONTRACT_VERSION,
    )
    passed = not dirty and all(
        result.inspected and all(gate_passed for _, gate_passed in result.gates)
        for result in source_results
    )
    return PromotionDecision(
        evidence_date=datetime.now(UTC),
        candidate=candidate,
        source_results=source_results,
        passed=passed,
    )


def _git(repository: Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", *arguments],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


__all__ = ["build_promotion_decision"]

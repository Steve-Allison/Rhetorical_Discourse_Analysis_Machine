"""Repository-only Gold Set, run, and promotion evidence contracts."""

from collections import Counter
from datetime import datetime
from enum import StrEnum
from pathlib import PurePosixPath
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from isanlp_rst.ingest.contracts import SourceForm
from isanlp_rst.ingest.identity import semantic_sha256

REQUIRED_RISKS = frozenset(
    {
        "long_structured_prose",
        "presentation_notes",
        "ocr_heavy",
        "multi_speaker",
        "code_raw_markup_markdown",
        "rich_nested_tables",
        "repeated_content",
        "unicode_coordinates",
    }
)


class ProvenanceClass(StrEnum):
    REAL = "real"
    NORMATIVE = "normative"
    SYNTHETIC = "synthetic"


class _EvidenceModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class GoldSource(_EvidenceModel):
    source_id: str = Field(min_length=1)
    relative_path: PurePosixPath
    source_form: SourceForm
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(gt=0)
    provenance_class: ProvenanceClass
    risk_classes: tuple[str, ...] = Field(min_length=1)
    expected_outcome: str = Field(pattern=r"^(success|failure:[a-z0-9_-]+)$")
    expectation_ref: PurePosixPath
    rst_gold_ref: PurePosixPath | None = None
    redistributable: bool
    original_source_identity: str | None = None
    conversion_provenance_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def safe_relative_references(self) -> Self:
        for path in (self.relative_path, self.expectation_ref, self.rst_gold_ref):
            if path is not None and (path.is_absolute() or ".." in path.parts):
                raise ValueError("Gold Set paths must be safe and relative to an explicit authority root")
        if len(self.risk_classes) != len(set(self.risk_classes)):
            raise ValueError("Gold Set risk classes must be unique per source")
        return self


class GoldSetManifest(_EvidenceModel):
    schema_version: str = "1.0.0"
    frozen_at: datetime
    sources: tuple[GoldSource, ...] = Field(min_length=20)
    expectation_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    manifest_digest: str = ""

    @model_validator(mode="after")
    def deep_complete_authority(self) -> Self:
        if len(self.sources) < 20:
            raise ValueError("Gold Set requires at least 20 deeply verified sources")
        source_ids = [source.source_id for source in self.sources]
        if len(source_ids) != len(set(source_ids)):
            raise ValueError("Gold Set source IDs must be unique")
        required_forms = set(SourceForm)
        present_forms = {source.source_form for source in self.sources}
        if present_forms != required_forms:
            missing = sorted(form.value for form in required_forms - present_forms)
            raise ValueError(f"Gold Set is missing supported source forms: {missing}")
        risk_counts = Counter(risk for source in self.sources for risk in source.risk_classes)
        shallow = sorted(risk for risk in REQUIRED_RISKS if risk_counts[risk] < 2)
        if shallow:
            raise ValueError(f"Gold Set requires at least two examples of each material risk: {shallow}")
        if self.rst_gold_count < 12:
            raise ValueError("Gold Set requires at least 12 EDU/RST-gold sources")
        digest = semantic_sha256(
            {
                "schema_version": self.schema_version,
                "frozen_at": self.frozen_at,
                "sources": self.sources,
                "expectation_digest": self.expectation_digest,
            }
        )
        if self.manifest_digest and self.manifest_digest != digest:
            raise ValueError("Gold Set manifest digest mismatch")
        object.__setattr__(self, "manifest_digest", digest)
        return self

    @property
    def rst_gold_count(self) -> int:
        return sum(source.rst_gold_ref is not None for source in self.sources)


class CandidateIdentity(_EvidenceModel):
    git_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    git_dirty: bool
    wheel_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    model_release_id: str = Field(min_length=1)
    model_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    policy_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    result_contract_version: str = Field(min_length=1)


class FreezeAuthority(_EvidenceModel):
    schema_version: str = "1.0.0"
    frozen_at: datetime
    gold_manifest_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    expectation_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    baseline_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    baseline_wheel_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    model_release_id: str = Field(min_length=1)
    model_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    scorer_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    pixi_lock_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    machine: tuple[tuple[str, str], ...]
    source_results: tuple[tuple[str, str], ...]


class SourceGateResult(_EvidenceModel):
    source_id: str = Field(min_length=1)
    source_form: SourceForm
    gates: tuple[tuple[str, bool], ...]
    metrics: tuple[tuple[str, float], ...] = ()
    inspected: bool = False
    anomaly: str | None = None


class PromotionDecision(_EvidenceModel):
    schema_version: str = "1.0.0"
    evidence_date: datetime
    candidate: CandidateIdentity
    source_results: tuple[SourceGateResult, ...] = Field(min_length=20)
    passed: bool

    @model_validator(mode="after")
    def no_hidden_failure(self) -> Self:
        all_passed = all(all(passed for _, passed in result.gates) and result.inspected for result in self.source_results)
        if self.passed != all_passed:
            raise ValueError("promotion decision must equal all per-source gates and inspections")
        return self


__all__ = [
    "REQUIRED_RISKS",
    "CandidateIdentity",
    "FreezeAuthority",
    "GoldSetManifest",
    "GoldSource",
    "PromotionDecision",
    "ProvenanceClass",
    "SourceGateResult",
]

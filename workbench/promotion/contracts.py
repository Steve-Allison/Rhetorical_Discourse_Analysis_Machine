"""Offline-only contracts for local model-promotion workflows."""

from datetime import datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PromotionReceipt(BaseModel):
    """Immutable evidence for one successful local promotion."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    candidate_path: str
    candidate_manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    release_path: str
    release_manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    verified_files: int = Field(gt=0)
    promoted_at: datetime
    producer_version: str = Field(min_length=1)
    succeeded: bool
    failure_code: str | None = None
    failure_detail: str | None = None

    @model_validator(mode="after")
    def success_fields_are_coherent(self) -> Self:
        if self.succeeded and (self.failure_code is not None or self.failure_detail is not None):
            raise ValueError("successful promotion cannot contain failure fields")
        if not self.succeeded and not self.failure_code:
            raise ValueError("failed promotion requires failure_code")
        return self


__all__ = ["PromotionReceipt"]

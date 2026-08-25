"""Integrity-checked, same-filesystem atomic cache for semantic ingest results."""

import os
from pathlib import Path
import tempfile

from pydantic import ValidationError

from isanlp_rst.ingest.contracts import FailureStage, ProductionAnalysisResult, ProductionIngestError


class ProductionIngestCache:
    """Small local file cache keyed only by a complete analytical fingerprint."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)

    def path_for(self, fingerprint: str) -> Path:
        if len(fingerprint) != 64 or any(character not in "0123456789abcdef" for character in fingerprint):
            raise ValueError("cache fingerprint must be a lowercase SHA-256 digest")
        return self.root / fingerprint[:2] / f"{fingerprint}.json"

    def load(self, fingerprint: str) -> ProductionAnalysisResult | None:
        path = self.path_for(fingerprint)
        if not path.exists():
            return None
        try:
            result = ProductionAnalysisResult.from_json(path.read_bytes())
        except (OSError, UnicodeError, ValueError, ValidationError) as exc:
            raise ProductionIngestError(
                stage=FailureStage.CACHE,
                code="corrupt_cache_entry",
                artifact_id=fingerprint,
                expectation="a complete schema-valid cache payload with matching semantic digest",
                detail=f"cache entry validation failed ({type(exc).__name__})",
            ) from exc
        if result.preparation_receipt.cache_fingerprint != fingerprint:
            raise ProductionIngestError(
                stage=FailureStage.CACHE,
                code="contradictory_cache_identity",
                artifact_id=fingerprint,
                expectation="the stored receipt fingerprint to equal its cache key",
                detail="stored cache fingerprint does not match the requested key",
            )
        return result

    def store(self, fingerprint: str, result: ProductionAnalysisResult) -> None:
        if result.preparation_receipt.cache_fingerprint != fingerprint:
            raise ValueError("result receipt contradicts cache destination")
        path = self.path_for(fingerprint)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = result.to_json().encode("utf-8") + b"\n"
        descriptor, temporary_name = tempfile.mkstemp(prefix=f".{fingerprint}.", suffix=".tmp", dir=path.parent)
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
            directory_fd = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        finally:
            if temporary.exists():
                temporary.unlink()


__all__ = ["ProductionIngestCache"]

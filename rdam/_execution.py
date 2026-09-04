"""Public execution policy for bounded local parallelism and opt-in caching."""

from dataclasses import dataclass
from pathlib import Path

from rdam.frameworks import BOUNDARY_TECHNIQUES


@dataclass(frozen=True, slots=True)
class ExecutionPolicy:
    """Bounded execution settings for one local machine composition."""

    max_workers: int = 4
    cache_directory: Path | None = None

    def __post_init__(self) -> None:
        if (
            type(self.max_workers) is not int
            or not 1 <= self.max_workers <= len(BOUNDARY_TECHNIQUES)
        ):
            raise ValueError(f"max_workers must be between 1 and {len(BOUNDARY_TECHNIQUES)}")
        if self.cache_directory is not None:
            object.__setattr__(self, "cache_directory", Path(self.cache_directory))


__all__ = ["ExecutionPolicy"]

"""Private content-addressed cache for successful native technique results.

Machine._cache_key covers source, projection, provider, contract, model, and
instructions identities directly. Provenance additionally binds the instructions
digest to the source revision; test_cache_key_completeness pins that relationship.
test_cache exercises the external model boundary, exact reuse, and corrupt records.
Dirty/unknown revisions still bypass persistence rather than hiding their status.
"""

from collections.abc import Callable, Generator
from contextlib import contextmanager
import os
from pathlib import Path
import tempfile
from threading import Lock
import warnings

from rdam.contracts import NativeTechniqueResult
from rdam._provenance import INSTRUCTIONS_REVISION_SEPARATOR
from rdam.serialization import load, serialize

_LOCK_REGISTRY_GUARD = Lock()
_LOCK_REGISTRY: dict[tuple[Path, str], tuple[Lock, int]] = {}


def revision_is_cacheable(revision: str | None) -> bool:
    """Only exact, clean source revisions may participate in persistent caching."""

    if revision is None:
        return False
    normalized = revision.strip().lower()
    source_revision = normalized.partition(INSTRUCTIONS_REVISION_SEPARATOR)[0].strip()
    return (
        bool(source_revision)
        and source_revision != "unknown"
        and not source_revision.endswith("-dirty")
        and not normalized.endswith("-dirty")
    )


class ResultCache:
    """Atomic owner-only persistence plus in-process per-key single flight."""

    def __init__(self, directory: Path) -> None:
        self._directory = directory.expanduser().resolve()

    @contextmanager
    def single_flight(self, key: str) -> Generator[None]:
        identity = (self._directory, key)
        with _LOCK_REGISTRY_GUARD:
            lock, references = _LOCK_REGISTRY.get(identity, (Lock(), 0))
            _LOCK_REGISTRY[identity] = (lock, references + 1)
        lock.acquire()
        try:
            yield
        finally:
            lock.release()
            with _LOCK_REGISTRY_GUARD:
                current_lock, current_references = _LOCK_REGISTRY[identity]
                if current_references == 1:
                    del _LOCK_REGISTRY[identity]
                else:
                    _LOCK_REGISTRY[identity] = (current_lock, current_references - 1)

    def load(
        self,
        key: str,
        *,
        validate: Callable[[NativeTechniqueResult], str | None],
    ) -> NativeTechniqueResult | None:
        """Load and fully validate a hit; delete and warn on any corruption."""

        path = self._path(key)
        if not path.is_file():
            return None
        try:
            record = load(path.read_bytes())
            if not isinstance(record, NativeTechniqueResult):
                raise ValueError("cache entry is not a native technique result")
            if violation := validate(record):
                raise ValueError(violation)
        except (OSError, TypeError, UnicodeError, ValueError) as error:
            self._discard(path, error)
            return None
        return record

    def store(self, key: str, result: NativeTechniqueResult) -> None:
        """Atomically store a successful, already-validated native result."""

        self._directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        self._directory.chmod(0o700)
        descriptor, temporary_name = tempfile.mkstemp(prefix=f".{key}.", dir=self._directory)
        temporary = Path(temporary_name)
        replaced = False
        try:
            os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(serialize(result))
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self._path(key))
            replaced = True
            self._path(key).chmod(0o600)
        finally:
            if not replaced:
                temporary.unlink(missing_ok=True)

    def _path(self, key: str) -> Path:
        return self._directory / f"{key}.json"

    @staticmethod
    def _discard(path: Path, error: Exception) -> None:
        try:
            path.unlink(missing_ok=True)
        except OSError as unlink_error:
            warnings.warn(
                f"could not remove corrupt RDAM cache entry {path}: {unlink_error}",
                RuntimeWarning,
                stacklevel=3,
            )
            return
        warnings.warn(
            f"discarded corrupt RDAM cache entry {path}: {error}",
            RuntimeWarning,
            stacklevel=3,
        )


__all__ = ["ResultCache", "revision_is_cacheable"]

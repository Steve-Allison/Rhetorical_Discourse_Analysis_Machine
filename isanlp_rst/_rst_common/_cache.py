"""Optional on-disk result cache for the format-native entry points.

Keyed on the source file's bytes plus every parse-affecting knob, so a
changed file, model, inventory, or knob produces a fresh parse. Values
are pickled result dataclasses — a local single-user cache; do not point
``cache_dir`` at untrusted storage (unpickling executes code).

``tool_version`` is deliberately NOT part of the key: a cached result
keeps the tool_version of the run that produced it.
"""

from __future__ import annotations

import hashlib
import pickle
from collections.abc import Mapping
from pathlib import Path


def result_cache_key(source_bytes: bytes, parts: Mapping[str, object]) -> str:
    """Compute a stable hex key from source bytes + sorted knob parts."""
    h = hashlib.sha256(source_bytes)
    for name in sorted(parts):
        h.update(f"|{name}={parts[name]!r}".encode())
    return h.hexdigest()


def load_cached(cache_dir: Path, key: str) -> object | None:
    """Return the cached value for ``key``, or ``None`` when absent."""
    path = cache_dir / f"{key}.pkl"
    if not path.is_file():
        return None
    with path.open("rb") as f:
        return pickle.load(f)


def store_cached(cache_dir: Path, key: str, value: object) -> None:
    """Persist ``value`` under ``key``, creating ``cache_dir`` if needed."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    with (cache_dir / f"{key}.pkl").open("wb") as f:
        pickle.dump(value, f, protocol=pickle.HIGHEST_PROTOCOL)


__all__ = ["load_cached", "result_cache_key", "store_cached"]

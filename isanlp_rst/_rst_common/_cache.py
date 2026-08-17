"""Optional on-disk result cache for the format-native entry points.

Keyed on the source file's bytes plus every parse-affecting knob, so a
changed file, model, inventory, or knob produces a fresh parse. Values are
stored as versioned JSON (never pickle) so a hostile ``cache_dir`` cannot
execute code on load.

``tool_version`` is deliberately NOT part of the key: a cached result
keeps the tool_version of the run that produced it.
"""

import hashlib
import json
import os
import stat
import tempfile
from collections.abc import Callable, Mapping
from dataclasses import asdict, fields, is_dataclass
from pathlib import Path
from typing import Any, get_args, get_origin, get_type_hints

CACHE_FORMAT_VERSION = 1


def result_cache_key(source_bytes: bytes, parts: Mapping[str, object]) -> str:
    """Compute a stable hex key from source bytes + sorted knob parts.

    Values are serialised with ``repr``. Callers must pass only
    repr-stable scalars (``str``, ``bool``, ``int``, ``float``, ``None``).
    """
    h = hashlib.sha256(source_bytes)
    for name in sorted(parts):
        value = parts[name]
        if type(value) not in (str, bool, int, float, type(None)):
            raise TypeError(
                f"cache knob {name!r} has non-repr-stable type {type(value).__name__}; "
                "pass str/bool/int/float/None only"
            )
        h.update(f"|{name}={value!r}".encode())
    return h.hexdigest()


def _refuse_insecure_cache_dir(cache_dir: Path) -> None:
    """Raise if ``cache_dir`` exists and is group/world-writable."""
    if not cache_dir.exists():
        return
    mode = cache_dir.stat().st_mode
    if mode & (stat.S_IWGRP | stat.S_IWOTH):
        raise PermissionError(
            f"cache_dir {cache_dir} is group/world-writable; "
            "refuse to read or write a shared cache. "
            "Use a private directory (e.g. mode 0o700)."
        )


def _coerce(annotation: Any, value: Any) -> Any:
    """Rebuild nested dataclass / tuple structures from JSON-plain data."""
    if value is None:
        return None

    origin = get_origin(annotation)
    if origin is tuple:
        args = get_args(annotation)
        if not args:
            return tuple(value)
        inner = args[0]
        if len(args) == 2 and args[1] is Ellipsis:
            return tuple(_coerce(inner, item) for item in value)
        return tuple(
            _coerce(args[i] if i < len(args) else Any, item)
            for i, item in enumerate(value)
        )

    if origin is list:
        args = get_args(annotation)
        inner = args[0] if args else Any
        return [_coerce(inner, item) for item in value]

    if origin is dict:
        args = get_args(annotation)
        key_t, val_t = (args + (Any, Any))[:2]
        return {_coerce(key_t, k): _coerce(val_t, v) for k, v in value.items()}

    if isinstance(annotation, type) and is_dataclass(annotation):
        return dataclass_from_dict(annotation, value)

    return value


def dataclass_from_dict[T](cls: type[T], data: Mapping[str, Any]) -> T:
    """Reconstruct a (nested) dataclass instance from ``asdict``-shaped data."""
    if not is_dataclass(cls):
        raise TypeError(f"{cls!r} is not a dataclass")
    if not isinstance(data, Mapping):
        raise TypeError(f"expected mapping for {cls.__name__}, got {type(data).__name__}")

    hints = get_type_hints(cls)
    kwargs: dict[str, Any] = {}
    for field in fields(cls):
        if field.name not in data:
            continue
        annotation = hints.get(field.name, Any)
        kwargs[field.name] = _coerce(annotation, data[field.name])
    return cls(**kwargs)


def load_cached[T](
    cache_dir: Path,
    key: str,
    *,
    rebuild: Callable[[Mapping[str, Any]], T] | None = None,
) -> T | Any | None:
    """Return the cached value for ``key``, or ``None`` when absent/corrupt.

    Prefer passing ``rebuild`` (e.g. ``DoclingRstResult.from_dict``) so the
    payload is rehydrated to the caller's result type. Without ``rebuild``,
    the plain JSON payload is returned (tuples become lists).
    """
    _refuse_insecure_cache_dir(cache_dir)
    path = cache_dir / f"{key}.json"
    if not path.is_file():
        return None
    try:
        with path.open("r", encoding="utf-8") as f:
            envelope = json.load(f)
        if not isinstance(envelope, dict) or envelope.get("v") != CACHE_FORMAT_VERSION:
            return None
        payload = envelope.get("payload")
        if not isinstance(payload, dict):
            return None
        if rebuild is not None:
            return rebuild(payload)
        return payload
    except (OSError, json.JSONDecodeError, TypeError, ValueError, KeyError):
        return None


def store_cached(cache_dir: Path, key: str, value: object) -> None:
    """Persist ``value`` under ``key`` as versioned JSON (atomic replace)."""
    _refuse_insecure_cache_dir(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    _refuse_insecure_cache_dir(cache_dir)

    if is_dataclass(value) and not isinstance(value, type):
        payload: Any = asdict(value)
    elif isinstance(value, Mapping):
        payload = value
    else:
        raise TypeError(
            f"cache value must be a dataclass instance or mapping; "
            f"got {type(value).__name__}"
        )

    envelope = {"v": CACHE_FORMAT_VERSION, "payload": payload}
    text = json.dumps(envelope, ensure_ascii=False, separators=(",", ":"))

    fd, tmp_name = tempfile.mkstemp(prefix=f".{key}.", suffix=".tmp", dir=cache_dir)
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, cache_dir / f"{key}.json")
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise


__all__ = [
    "CACHE_FORMAT_VERSION",
    "dataclass_from_dict",
    "load_cached",
    "result_cache_key",
    "store_cached",
]

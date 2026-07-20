"""Model-identity helpers for format-native result metadata and caching.

An injected ``parser`` is the source of truth for which model produced a
tree. When the caller constructs a fresh ``Parser`` from kwargs, those
kwargs are the identity. Injected parsers are always keyed by ``id(parser)``
so two objects with identical HF attrs cannot share a cache hit (the
documented batch pattern reuses one object and therefore hits).
"""

from __future__ import annotations

from typing import Any


def model_identity_knobs(
    *,
    hf_model_name: str,
    hf_model_version: str,
    relinventory: str | None,
    parser: object | None = None,
) -> dict[str, object]:
    """Return cache-key parts that identify the producing model."""
    if parser is None:
        return {
            "hf_model_name": hf_model_name,
            "hf_model_version": hf_model_version,
            "relinventory": relinventory,
            "parser_source": "construct",
        }

    name = getattr(parser, "hf_model_name", None)
    version = getattr(parser, "hf_model_version", None)
    inv = getattr(parser, "relinventory", None)
    return {
        "hf_model_name": name if name is not None else hf_model_name,
        "hf_model_version": version if version is not None else hf_model_version,
        "relinventory": inv if inv is not None else relinventory,
        "parser_source": "injected",
        "parser_id": id(parser),
    }


def resolve_result_model_meta(
    parser: object | None,
    hf_model_version: str,
    relinventory: str | None,
    *,
    resolve_inventory: Any,
) -> tuple[str, str]:
    """Return ``(model_version, inventory)`` for a result payload.

    Prefer attributes on an injected parser when present so metadata
    cannot disagree with the tree that was actually produced.
    """
    if parser is not None:
        version = getattr(parser, "hf_model_version", None)
        if version is None:
            version = hf_model_version
        inv = getattr(parser, "relinventory", None)
        if inv is None:
            inv = relinventory
        return str(version), resolve_inventory(version, inv)
    return hf_model_version, resolve_inventory(hf_model_version, relinventory)

"""Helpers for unpacking ``Parser`` / predictor call results."""

from collections.abc import Mapping
from typing import Any


class ParseFailedError(RuntimeError):
    """Raised when a parse result has no usable RST root tree."""


def extract_root_tree(result: Mapping[str, Any] | Any) -> Any:
    """Return ``result['rst'][0]``, or raise :class:`ParseFailedError`.

    Preferred over raw ``parser(text)['rst'][0]``, which raises opaque
    ``KeyError`` / ``IndexError`` / ``TypeError`` when the predictor returns
    an empty or malformed payload.
    """
    if not isinstance(result, Mapping):
        raise ParseFailedError(
            f"Parse result must be a mapping with an 'rst' key; "
            f"got {type(result).__name__}."
        )
    try:
        rst = result["rst"]
    except KeyError as exc:
        raise ParseFailedError(
            "Parse result is missing the 'rst' key "
            f"(keys={sorted(result.keys())!r})."
        ) from exc

    if rst is None:
        raise ParseFailedError("Parse result['rst'] is None.")
    try:
        if len(rst) == 0:
            raise ParseFailedError("Parse result['rst'] is empty.")
        root = rst[0]
    except TypeError as exc:
        raise ParseFailedError(
            f"Parse result['rst'] is not a sequence; got {type(rst).__name__}."
        ) from exc

    if root is None:
        raise ParseFailedError("Parse result['rst'][0] is None.")
    return root


__all__ = ["ParseFailedError", "extract_root_tree"]

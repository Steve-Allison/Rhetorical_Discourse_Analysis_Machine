"""Helpers for unpacking ``Parser`` / predictor call results."""

from collections.abc import Mapping, Sequence
from typing import cast


class ParseFailedError(RuntimeError):
    """Raised when a parse result has no usable RST root tree."""


def extract_root_tree(result: object) -> object:
    """Return ``result['rst'][0]``, or raise :class:`ParseFailedError`.

    Preferred over raw ``parser(text)['rst'][0]``, which raises opaque
    ``KeyError`` / ``IndexError`` / ``TypeError`` when the predictor returns
    an empty or malformed payload.
    """
    if not isinstance(result, Mapping):
        raise ParseFailedError(f"Parse result must be a mapping with an 'rst' key; got {type(result).__name__}.")
    payload = cast(Mapping[object, object], result)
    try:
        rst = payload["rst"]
    except KeyError as exc:
        raise ParseFailedError(
            f"Parse result is missing the 'rst' key (keys={sorted(map(str, payload.keys()))!r})."
        ) from exc

    if rst is None:
        raise ParseFailedError("Parse result['rst'] is None.")
    if not isinstance(rst, Sequence) or isinstance(rst, str | bytes | bytearray):
        raise ParseFailedError(f"Parse result['rst'] is not a sequence; got {type(rst).__name__}.")
    sequence = cast(Sequence[object], rst)
    if not sequence:
        raise ParseFailedError("Parse result['rst'] is empty.")
    root = sequence[0]

    if root is None:
        raise ParseFailedError("Parse result['rst'][0] is None.")
    return root


__all__ = ["ParseFailedError", "extract_root_tree"]

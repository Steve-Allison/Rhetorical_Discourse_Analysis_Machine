"""Strict RFC 6901 lookup shared by evidence and reading guides."""

from collections.abc import Mapping, Sequence
import re
from typing import cast


def escape_pointer_token(token: str) -> str:
    return token.replace("~", "~0").replace("/", "~1")


def resolve_pointer(value: object, pointer: str) -> object:
    if pointer == "":
        return value
    if not pointer.startswith("/"):
        raise ValueError("JSON pointer must start with /")
    current = value
    for encoded in pointer[1:].split("/"):
        if re.search(r"~(?![01])", encoded):
            raise ValueError("invalid JSON pointer escape")
        key = encoded.replace("~1", "/").replace("~0", "~")
        if isinstance(current, Mapping):
            mapping = cast(Mapping[str, object], current)
            if key not in mapping:
                raise ValueError("JSON pointer does not resolve")
            current = mapping[key]
        elif isinstance(current, Sequence) and not isinstance(current, (str, bytes)):
            sequence = cast(Sequence[object], current)
            if re.fullmatch(r"0|[1-9][0-9]*", key) is None or int(key) >= len(sequence):
                raise ValueError("JSON pointer array index does not resolve")
            current = sequence[int(key)]
        else:
            raise ValueError("JSON pointer traverses a scalar")
    return current

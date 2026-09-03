"""Recursively immutable JSON containers with native wire-type semantics."""

from collections.abc import Mapping, Sequence
from typing import Any, Never

from rdam._strict import JsonValue


def _immutable(*_args: object, **_kwargs: object) -> Never:
    raise TypeError("frozen JSON containers are immutable")


class FrozenJsonObject(dict[str, JsonValue]):
    """A recursively frozen JSON object that remains a native ``dict``."""

    def __init__(self, values: Mapping[str, JsonValue]) -> None:
        prepared: dict[str, JsonValue] = {key: freeze_json(value) for key, value in values.items()}
        super().__init__(prepared)

    __delitem__ = _immutable
    __ior__ = _immutable
    __setitem__ = _immutable
    clear = _immutable
    pop = _immutable
    popitem = _immutable
    setdefault = _immutable
    update = _immutable


class FrozenJsonArray(list[JsonValue]):
    """A recursively frozen JSON array that remains a native ``list``."""

    def __init__(self, values: Sequence[JsonValue]) -> None:
        prepared: list[JsonValue] = [freeze_json(value) for value in values]
        super().__init__(prepared)

    __delitem__ = _immutable
    __iadd__ = _immutable
    __imul__ = _immutable
    __setitem__ = _immutable
    append = _immutable
    clear = _immutable
    extend = _immutable
    insert = _immutable
    pop = _immutable
    remove = _immutable
    reverse = _immutable
    sort = _immutable


def freeze_json(value: JsonValue) -> JsonValue:
    """Copy a JSON value into recursively immutable native containers."""

    if isinstance(value, Mapping):
        return FrozenJsonObject(value)
    if isinstance(value, Sequence) and not isinstance(value, str | bytes):
        return FrozenJsonArray(value)
    if value is None or isinstance(value, str | int | float | bool):
        return value
    raise TypeError(f"value is outside the JSON data model: {type(value).__name__}")


def freeze_json_object(value: Mapping[str, JsonValue]) -> FrozenJsonObject:
    """Copy and recursively freeze one JSON object."""

    return FrozenJsonObject(value)


def thaw_json(value: JsonValue) -> Any:
    """Project frozen containers back to their ordinary JSON wire representation."""

    if isinstance(value, Mapping):
        return {key: thaw_json(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, str | bytes):
        return [thaw_json(item) for item in value]
    return value


__all__ = ["FrozenJsonArray", "FrozenJsonObject", "freeze_json", "freeze_json_object", "thaw_json"]

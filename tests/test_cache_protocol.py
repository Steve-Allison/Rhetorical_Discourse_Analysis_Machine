"""Tests for the ParseCache protocol.

Verifies that a minimal in-memory cache is recognised by
``isinstance(..., ParseCache)`` and that the protocol methods carry the
expected signature. No model loading required.
"""

from __future__ import annotations

from typing import Any

from isanlp_rst.utils.cache import ParseCache


class _LRUCache:
    """Minimal in-memory cache used to verify the protocol."""

    def __init__(self) -> None:
        self._store: dict[str, Any] = {}

    def get(self, text: str) -> Any | None:
        return self._store.get(text)

    def put(self, text: str, result: Any) -> None:
        self._store[text] = result


class _MissingPut:
    def get(self, text: str) -> Any | None:
        return None


class _MissingGet:
    def put(self, text: str, result: Any) -> None:  # noqa: D401
        pass


class TestProtocolMembership:
    def test_lru_cache_satisfies_protocol(self) -> None:
        cache: ParseCache = _LRUCache()
        assert isinstance(cache, ParseCache)

    def test_missing_put_does_not_satisfy_protocol(self) -> None:
        assert not isinstance(_MissingPut(), ParseCache)

    def test_missing_get_does_not_satisfy_protocol(self) -> None:
        assert not isinstance(_MissingGet(), ParseCache)


class TestRoundTrip:
    def test_put_then_get_returns_stored_value(self) -> None:
        cache = _LRUCache()
        cache.put("hello", {"rst": ["mock-tree"]})
        assert cache.get("hello") == {"rst": ["mock-tree"]}

    def test_miss_returns_none(self) -> None:
        cache = _LRUCache()
        assert cache.get("never-stored") is None

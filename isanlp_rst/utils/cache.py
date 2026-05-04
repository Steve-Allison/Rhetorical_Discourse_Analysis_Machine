"""Parse-result cache protocol.

A small Protocol-based interface so callers can inject any cache backend
they like (LRU, Redis, SQLite, Blake3-keyed disk cache) without the
parser package depending on a specific cache library.

The parser uses a cache transparently: if one is supplied, every call
to :meth:`Parser.__call__` first checks the cache; on miss it runs the
model and stores the result. This makes re-analysis of an unchanged
document essentially free.

Implementations of :class:`ParseCache` must be deterministic in the
sense that ``cache.get(text)`` must return the same parse result that
``parser(text)`` would have returned at storage time. Cache keys are
the raw input text (unmodified) — implementations are free to hash or
otherwise key internally.

Examples:
    Pure in-memory LRU cache:

    >>> from collections import OrderedDict
    >>> class LRUCache:
    ...     def __init__(self, maxsize: int = 128) -> None:
    ...         self._store: OrderedDict[str, ParseResult] = OrderedDict()
    ...         self._maxsize = maxsize
    ...     def get(self, text: str) -> ParseResult | None:
    ...         if text not in self._store:
    ...             return None
    ...         self._store.move_to_end(text)
    ...         return self._store[text]
    ...     def put(self, text: str, result: ParseResult) -> None:
    ...         self._store[text] = result
    ...         self._store.move_to_end(text)
    ...         if len(self._store) > self._maxsize:
    ...             self._store.popitem(last=False)

    Wired into the parser:

    >>> parser = Parser(hf_model_version='rstdt', cache=LRUCache())
    >>> result1 = parser("Some text. More text.")  # cold — runs the model
    >>> result2 = parser("Some text. More text.")  # warm — from cache
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


# `ParseResult` is intentionally `Any` here: the parser's actual return
# type is `dict[str, list[DiscourseUnit]]`, but importing `DiscourseUnit`
# from the optional `isanlp` package at protocol-definition time would
# break the abstraction. Implementations will see the concrete type.
ParseResult = Any


@runtime_checkable
class ParseCache(Protocol):
    """Cache backend protocol for parser results.

    Any object exposing ``get(text)`` and ``put(text, result)`` methods
    with the signatures below satisfies this protocol — no inheritance
    required. The :func:`isinstance` check works at runtime via
    ``@runtime_checkable``.
    """

    def get(self, text: str) -> ParseResult | None:
        """Return the cached parse result for ``text``, or ``None`` on miss.

        Args:
            text: The exact input string that would have been passed to
                ``Parser.__call__``. Implementations may hash the key
                internally but must round-trip a stored value via the
                same input.

        Returns:
            The previously-stored parse result on hit, ``None`` on miss.
            Implementations should never raise on a miss — return None.
        """
        ...

    def put(self, text: str, result: ParseResult) -> None:
        """Store ``result`` under ``text``.

        Args:
            text: Cache key — the input string that produced ``result``.
            result: The parser output (a ``dict`` with key ``'rst'``).

        Implementations should treat write failures (full disk, network
        partition) as non-fatal — log and return. The parser will
        continue without caching the result.
        """
        ...


__all__ = ["ParseCache", "ParseResult"]

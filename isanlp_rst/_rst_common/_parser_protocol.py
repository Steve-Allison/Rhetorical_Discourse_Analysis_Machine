"""Structural contract for injectable RST parsers."""

from typing import Protocol


class RstParser(Protocol):
    """Callable boundary used by format-native parsing entry points."""

    def __call__(self, text: str) -> object:
        """Return a parser result containing an RST tree."""


__all__ = ["RstParser"]

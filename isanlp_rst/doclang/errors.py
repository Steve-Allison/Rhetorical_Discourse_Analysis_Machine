"""Custom exceptions for DocLang-native RST parsing."""

from __future__ import annotations


class DoclangRstError(Exception):
    """Base class for parse_doclang errors."""


class EmptyDoclangError(DoclangRstError):
    """The loaded DocLang document has no harvestable body content."""


class EmptyHarvestError(DoclangRstError):
    """The harvest produced no text (e.g. a tables-only document)."""


class InputTooLargeError(DoclangRstError):
    """Harvested text exceeds the configured length threshold."""


class InvalidDoclangError(DoclangRstError):
    """The XML file is not a valid DocLang document."""


class UnsupportedDoclangError(DoclangRstError):
    """The document uses a DocLang construct this parser does not support yet."""

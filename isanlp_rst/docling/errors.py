"""Custom exceptions for Docling-native RST parsing."""


class DoclingRstError(Exception):
    """Base class for parse_docling errors."""


class EmptyDoclingError(DoclingRstError):
    """The loaded DoclingDocument has no body content."""


class EmptyHarvestError(DoclingRstError):
    """The harvest produced no text (e.g. a tables-only document)."""


class InputTooLargeError(DoclingRstError):
    """Harvested text exceeds the configured length threshold."""

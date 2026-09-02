"""Failures raised by the private DocLang source loader."""


class DoclangIngestError(ValueError):
    """Base class for DocLang validation and archive-loading failures."""


class InvalidDoclangError(DoclangIngestError):
    """The XML file is not a valid DocLang document."""


class UnsafeDoclangArchiveError(InvalidDoclangError):
    """A DocLang archive violates bounded local ZIP safety invariants."""


__all__ = ["DoclangIngestError", "InvalidDoclangError", "UnsafeDoclangArchiveError"]

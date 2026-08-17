"""Docling-native RST parsing for isanlp_rst.

Public API:

- ``parse_docling(path, *, parser=None, ...)`` — entry point.
- ``DoclingRstResult``, ``Boundary``, ``RstRelation``, ``RstEdu``,
  ``TableAnalysis`` — result types.
- ``HarvestResult``, ``HarvestSpan``, ``TableHarvest`` — harvest
  intermediates.
- ``DoclingRstError`` and subclasses — error hierarchy.
"""

from ._entry import parse_docling
from ._mimetypes import ensure_docling_mimetypes
from .errors import (
    DoclingRstError,
    EmptyDoclingError,
    EmptyHarvestError,
    InputTooLargeError,
)
from .schema import (
    Boundary,
    DoclingRstResult,
    HarvestResult,
    HarvestSpan,
    RstEdu,
    RstRelation,
    TableAnalysis,
    TableHarvest,
)

# Register WebP (and related) MIME types as soon as the package is imported so
# direct ``DoclingDocument.load_from_json`` callers in tests / scripts also work.
ensure_docling_mimetypes()

__all__ = [
    "Boundary",
    "DoclingRstError",
    "DoclingRstResult",
    "EmptyDoclingError",
    "EmptyHarvestError",
    "HarvestResult",
    "HarvestSpan",
    "InputTooLargeError",
    "RstEdu",
    "RstRelation",
    "TableAnalysis",
    "TableHarvest",
    "ensure_docling_mimetypes",
    "parse_docling",
]

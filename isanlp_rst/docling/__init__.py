"""Docling-native RST parsing for isanlp_rst.

Public API:

- ``parse_docling(path, *, parser=None, ...)`` — entry point.
- ``DoclingRstResult``, ``Boundary``, ``RstRelation``, ``RstEdu`` — result types.
- ``HarvestResult``, ``HarvestSpan`` — harvest intermediates.
- ``DoclingRstError`` and subclasses — error hierarchy.
"""

from __future__ import annotations

from ._entry import parse_docling
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
)

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
    "parse_docling",
]

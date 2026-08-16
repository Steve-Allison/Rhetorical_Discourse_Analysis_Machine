"""DocLang-native RST parsing for isanlp_rst.

Public API:

- ``parse_doclang(path, *, parser=None, ...)`` — entry point.
- ``DoclangRstResult``, ``Boundary``, ``RstRelation``, ``RstEdu``,
  ``TableAnalysis`` — result types.
- ``HarvestResult``, ``HarvestSpan``, ``TableHarvest`` — harvest
  intermediates.
- ``DoclangRstError`` and subclasses — error hierarchy.
- ``local_path`` — the canonical local-name XPath generator used as the
  addressing scheme (verified Phase 1 against the then-40 valid fixtures;
  remirror 2026-08-16 is 42 files).
"""

from __future__ import annotations

from ._entry import parse_doclang
from .errors import (
    DoclangRstError,
    EmptyDoclangError,
    EmptyHarvestError,
    InputTooLargeError,
    InvalidDoclangError,
    UnsupportedDoclangError,
)
from .loader import local_path
from .schema import (
    Boundary,
    DoclangRstResult,
    HarvestResult,
    HarvestSpan,
    RstEdu,
    RstRelation,
    TableAnalysis,
    TableHarvest,
)

__all__ = [
    "Boundary",
    "DoclangRstError",
    "DoclangRstResult",
    "EmptyDoclangError",
    "EmptyHarvestError",
    "HarvestResult",
    "HarvestSpan",
    "InputTooLargeError",
    "InvalidDoclangError",
    "RstEdu",
    "RstRelation",
    "TableAnalysis",
    "TableHarvest",
    "UnsupportedDoclangError",
    "local_path",
    "parse_doclang",
]

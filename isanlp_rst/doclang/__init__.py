"""DocLang-native RST parsing for isanlp_rst.

Public API:

- ``parse_doclang(path, *, parser=None, ...)`` — entry point.
- ``DoclangRstResult``, ``Boundary``, ``RstRelation``, ``RstEdu`` —
  result types.
- ``HarvestResult``, ``HarvestSpan`` — harvest intermediates.
- ``DoclangRstError`` and subclasses — error hierarchy.
- ``local_path`` — the canonical local-name XPath generator used as the
  addressing scheme (verified Phase 1 against all 40 valid fixtures).
"""

from __future__ import annotations

from ._entry import parse_doclang
from .errors import (
    DoclangRstError,
    EmptyDoclangError,
    EmptyHarvestError,
    InputTooLargeError,
    InvalidDoclangError,
)
from .loader import local_path
from .schema import (
    Boundary,
    DoclangRstResult,
    HarvestResult,
    HarvestSpan,
    RstEdu,
    RstRelation,
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
    "local_path",
    "parse_doclang",
]

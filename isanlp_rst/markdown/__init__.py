"""Markdown-native RST parsing for isanlp_rst.

Public API:

- ``parse_markdown(path, *, parser=None, ...)`` — entry point.
- ``MarkdownRstResult``, ``Boundary``, ``RstRelation``, ``RstEdu``,
  ``TableAnalysis`` — result types.
- ``HarvestResult``, ``HarvestSpan``, ``TableHarvest`` — harvest
  intermediates.
- ``MarkdownRstError`` and subclasses — error hierarchy.

Plan: ``docs/plans/2026-06-12-markdown-native-rst.md``.
"""

from __future__ import annotations

from ._entry import parse_markdown
from .errors import (
    EmptyHarvestError,
    EmptyMarkdownError,
    InputTooLargeError,
    MarkdownRstError,
)
from .schema import (
    Boundary,
    HarvestResult,
    HarvestSpan,
    MarkdownRstResult,
    RstEdu,
    RstRelation,
    TableAnalysis,
    TableHarvest,
)

__all__ = [
    "Boundary",
    "EmptyHarvestError",
    "EmptyMarkdownError",
    "HarvestResult",
    "HarvestSpan",
    "InputTooLargeError",
    "MarkdownRstError",
    "MarkdownRstResult",
    "RstEdu",
    "RstRelation",
    "TableAnalysis",
    "TableHarvest",
    "parse_markdown",
]

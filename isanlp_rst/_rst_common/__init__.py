"""Format-agnostic helpers shared between ``docling`` and ``doclang``.

This package contains pure functions and constants that operate on
character offsets and string identifiers, independent of the source
format. Both ``isanlp_rst.docling`` and ``isanlp_rst.doclang`` import
from here.
"""

from __future__ import annotations

from ._overlap import NOTE_THRESHOLD, compute_overlap_refs
from ._split import split_refs_by_nuclearity

__all__ = [
    "NOTE_THRESHOLD",
    "compute_overlap_refs",
    "split_refs_by_nuclearity",
]

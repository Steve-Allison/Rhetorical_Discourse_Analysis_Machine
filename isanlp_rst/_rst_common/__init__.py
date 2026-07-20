"""Format-agnostic helpers shared by the format-native entry points.

This package contains pure functions and small classes that operate on
character offsets, string identifiers, and runtime configuration —
independent of the source format. ``isanlp_rst.docling``,
``isanlp_rst.doclang``, and ``isanlp_rst.markdown`` all import from here.
"""

from __future__ import annotations

from ._cache import dataclass_from_dict, load_cached, result_cache_key, store_cached
from ._flatten import flatten_tree
from ._identity import model_identity_knobs, resolve_result_model_meta
from ._overlap import NOTE_THRESHOLD, SpanIndex, compute_overlap_refs
from ._runtime import resolve_inventory, resolve_tool_version
from ._split import split_refs_by_nuclearity

__all__ = [
    "NOTE_THRESHOLD",
    "SpanIndex",
    "compute_overlap_refs",
    "dataclass_from_dict",
    "flatten_tree",
    "load_cached",
    "model_identity_knobs",
    "resolve_inventory",
    "resolve_result_model_meta",
    "resolve_tool_version",
    "result_cache_key",
    "split_refs_by_nuclearity",
    "store_cached",
]

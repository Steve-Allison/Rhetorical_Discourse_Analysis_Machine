"""Format-agnostic helpers shared by the format-native entry points.

This package contains pure functions and small classes that operate on
character offsets, string identifiers, and runtime configuration —
independent of the source format. ``isanlp_rst.docling``,
``isanlp_rst.doclang``, and ``isanlp_rst.markdown`` all import from here.
"""

from ._cache import dataclass_from_dict, load_cached, normalize_source_basename, result_cache_key, store_cached
from ._flatten import AuthoritativeProjection, ProjectedTreeNode, flatten_tree, project_tree
from ._identity import model_identity_knobs, resolve_result_model_meta
from ._overlap import NOTE_THRESHOLD, SpanIndex, compute_overlap_refs
from ._parser_protocol import RstParser
from ._projection import ProjectionTree, projection_to_format_analysis, projection_to_rst_analysis
from ._runtime import resolve_inventory, resolve_package_version, resolve_source_revision, resolve_tool_version
from ._split import split_refs_by_nuclearity

__all__ = [
    "NOTE_THRESHOLD",
    "AuthoritativeProjection",
    "ProjectedTreeNode",
    "ProjectionTree",
    "RstParser",
    "SpanIndex",
    "compute_overlap_refs",
    "dataclass_from_dict",
    "flatten_tree",
    "load_cached",
    "model_identity_knobs",
    "normalize_source_basename",
    "project_tree",
    "projection_to_format_analysis",
    "projection_to_rst_analysis",
    "resolve_inventory",
    "resolve_package_version",
    "resolve_source_revision",
    "resolve_result_model_meta",
    "resolve_tool_version",
    "result_cache_key",
    "split_refs_by_nuclearity",
    "store_cached",
]

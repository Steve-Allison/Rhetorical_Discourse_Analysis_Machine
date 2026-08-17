"""JSON-serialisation helpers for the RST trees produced by ``isanlp_rst``.

``Parser`` and the format-native entry points return
``isanlp.annotation_rst.DiscourseUnit`` trees. Consumers often need a
JSON-compatible representation to cache, transmit, or visualise without holding
the live object graph. These helpers are pure and depend only on the
already-core ``isanlp`` runtime — no extra dependencies.

For a typed / validated model with ``.model_dump()`` / ``.model_validate()`` and
JSON-schema export, see :mod:`isanlp_rst.utils.serialization_pydantic` (install
the ``pydantic`` extra: ``pip install isanlp_rst[pydantic]``).
"""

from typing import Any

from isanlp.annotation_rst import DiscourseUnit

# Per-node scalar fields serialised, in stable order (deterministic JSON aids
# caching and round-trip equality). ``orig_text`` is excluded — it holds the
# whole-document string (used only to re-slice ``text``), not per-node data.
# ``left`` / ``right`` are the recursive children, handled separately.
_NODE_FIELDS: tuple[str, ...] = (
    "id",
    "relation",
    "nuclearity",
    "start",
    "end",
    "text",
    "proba",
    "entropy",
)


def tree_to_dict(node: DiscourseUnit | None) -> dict[str, Any]:
    """Serialise a ``DiscourseUnit`` RST tree to a nested, JSON-ready dict.

    Recursively walks ``left`` / ``right``. Per-node fields whose value is
    ``None`` are omitted (compact, round-trip-stable JSON). Returns ``{}`` for
    a ``None`` node. Pass ``parser(text)['rst'][0]`` directly.
    """
    if node is None:
        return {}
    out: dict[str, Any] = {}
    for field in _NODE_FIELDS:
        value = getattr(node, field)
        if value is not None:
            out[field] = value
    if node.left is not None:
        out["left"] = tree_to_dict(node.left)
    if node.right is not None:
        out["right"] = tree_to_dict(node.right)
    return out


def tree_from_dict(data: dict[str, Any]) -> DiscourseUnit | None:
    """Reconstruct a ``DiscourseUnit`` tree from :func:`tree_to_dict` output.

    Inverse of :func:`tree_to_dict`; returns ``None`` for an empty dict.
    """
    if not data:
        return None
    node = DiscourseUnit(**{f: data[f] for f in _NODE_FIELDS if f in data})
    node.left = tree_from_dict(data["left"]) if "left" in data else None
    node.right = tree_from_dict(data["right"]) if "right" in data else None
    return node


__all__ = ["tree_from_dict", "tree_to_dict"]

"""JSON-serialisation helpers for the RST trees produced by ``rdam.rst``.

The low-level ``Parser`` call interface returns
``isanlp.annotation_rst.DiscourseUnit`` trees. Consumers sometimes need a
JSON-compatible representation to cache, transmit, or visualise without holding
the live object graph. These helpers are pure and depend only on the
already-core ``isanlp`` runtime — no extra dependencies.

For a typed / validated model with ``.model_dump()`` / ``.model_validate()`` and
JSON-schema export, see :mod:`rdam.rst.utils.serialization_pydantic`.
"""

from typing import Any, cast

from rdam.rst.annotation_rst import DiscourseUnit

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
    completed: dict[int, dict[str, Any]] = {}
    visiting: set[int] = set()
    pending: list[tuple[DiscourseUnit, bool]] = [(node, False)]
    while pending:
        current, expanded = pending.pop()
        identity = id(current)
        if expanded:
            out = {field: value for field in _NODE_FIELDS if (value := getattr(current, field)) is not None}
            if current.left is not None:
                out["left"] = completed[id(current.left)]
            if current.right is not None:
                out["right"] = completed[id(current.right)]
            completed[identity] = out
            visiting.remove(identity)
            continue
        if identity in visiting or identity in completed:
            raise ValueError("DiscourseUnit input must be an acyclic tree without shared nodes")
        visiting.add(identity)
        pending.append((current, True))
        if current.right is not None:
            pending.append((current.right, False))
        if current.left is not None:
            pending.append((current.left, False))
    return completed[id(node)]


def tree_from_dict(data: dict[str, Any]) -> DiscourseUnit | None:
    """Reconstruct a ``DiscourseUnit`` tree from :func:`tree_to_dict` output.

    Inverse of :func:`tree_to_dict`; returns ``None`` for an empty dict.
    """
    if not data:
        return None
    completed: dict[int, DiscourseUnit] = {}
    visiting: set[int] = set()
    pending: list[tuple[dict[str, Any], bool]] = [(data, False)]
    while pending:
        current, expanded = pending.pop()
        identity = id(current)
        if expanded:
            node = DiscourseUnit(**{field: current[field] for field in _NODE_FIELDS if field in current})
            left = current.get("left")
            right = current.get("right")
            node.left = completed[id(cast(dict[str, Any], left))] if isinstance(left, dict) and left else None
            node.right = completed[id(cast(dict[str, Any], right))] if isinstance(right, dict) and right else None
            completed[identity] = node
            visiting.remove(identity)
            continue
        if identity in visiting or identity in completed:
            raise ValueError("serialized DiscourseUnit must be an acyclic tree without shared mappings")
        visiting.add(identity)
        pending.append((current, True))
        for child_name in ("right", "left"):
            child = current.get(child_name)
            if child is None or child == {}:
                continue
            if not isinstance(child, dict):
                raise TypeError(f"{child_name} must be a JSON object")
            pending.append((cast(dict[str, Any], child), False))
    return completed[id(data)]


__all__ = ["tree_from_dict", "tree_to_dict"]

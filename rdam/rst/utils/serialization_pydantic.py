"""Typed Pydantic model for RST trees.

Mirrors :func:`rdam.rst.utils.serialization.tree_to_dict` (same field set) as a
validated, self-referencing :class:`RstNode` model. Gives ``.model_dump()`` /
``.model_validate()`` and JSON-schema export for consumers that want a typed
result contract. Keeping this separate from the core ``serialization`` module
means the dependency-free dict helpers stay usable without ``pydantic``.
"""

from pydantic import BaseModel, ConfigDict

from rdam.rst.annotation_rst import DiscourseUnit


class PydanticDiscourseUnit(BaseModel):
    """Validated, JSON-serialisable representation of one DiscourseUnit RST tree node.

    Fields mirror the serialised ``DiscourseUnit`` attributes; ``left`` /
    ``right`` recurse. All fields are optional so leaves (no relation /
    nuclearity / proba) validate without ceremony.
    """

    model_config = ConfigDict(
        extra="forbid",
        strict=True,
        frozen=True,
        validate_default=True,
    )

    id: int | None = None
    relation: str | None = None
    nuclearity: str | None = None
    start: int | None = None
    end: int | None = None
    text: str | None = None
    proba: float | None = None
    entropy: float | None = None
    # Quoted: Pydantic resolves field annotations at class creation
    # (https://docs.pydantic.dev/latest/concepts/forward_annotations/).
    left: PydanticDiscourseUnit | None = None
    right: PydanticDiscourseUnit | None = None

    @classmethod
    def from_tree(cls, node: DiscourseUnit | None) -> PydanticDiscourseUnit | None:
        """Build a model from an arbitrarily deep, acyclic ``DiscourseUnit`` tree."""
        if node is None:
            return None
        completed: dict[int, PydanticDiscourseUnit] = {}
        visiting: set[int] = set()
        pending: list[tuple[DiscourseUnit, bool]] = [(node, False)]
        while pending:
            current, expanded = pending.pop()
            identity = id(current)
            if expanded:
                completed[identity] = cls(
                    id=current.id,
                    relation=current.relation,
                    nuclearity=current.nuclearity,
                    start=current.start,
                    end=current.end,
                    text=current.text,
                    proba=current.proba,
                    entropy=current.entropy,
                    left=completed.get(id(current.left)) if current.left is not None else None,
                    right=completed.get(id(current.right)) if current.right is not None else None,
                )
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

    def to_tree(self) -> DiscourseUnit:
        """Reconstruct an arbitrarily deep ``DiscourseUnit`` tree iteratively."""
        completed: dict[int, DiscourseUnit] = {}
        visiting: set[int] = set()
        pending: list[tuple[PydanticDiscourseUnit, bool]] = [(self, False)]
        while pending:
            current, expanded = pending.pop()
            identity = id(current)
            if expanded:
                completed[identity] = DiscourseUnit(
                    id=current.id,
                    relation=current.relation or "",
                    nuclearity=current.nuclearity or "",
                    start=current.start,
                    end=current.end,
                    text=current.text or "",
                    proba=current.proba,
                    entropy=current.entropy,
                    left=completed.get(id(current.left)) if current.left is not None else None,
                    right=completed.get(id(current.right)) if current.right is not None else None,
                )
                visiting.remove(identity)
                continue
            if identity in visiting or identity in completed:
                raise ValueError("PydanticDiscourseUnit input must be an acyclic tree without shared nodes")
            visiting.add(identity)
            pending.append((current, True))
            if current.right is not None:
                pending.append((current.right, False))
            if current.left is not None:
                pending.append((current.left, False))
        return completed[id(self)]


# Backward-compatible alias for existing consumers
RstNode = PydanticDiscourseUnit

__all__ = ["PydanticDiscourseUnit", "RstNode"]

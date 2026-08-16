"""Typed Pydantic model for RST trees — optional, requires the ``pydantic`` extra.

Mirrors :func:`isanlp_rst.utils.serialization.tree_to_dict` (same field set) as a
validated, self-referencing :class:`RstNode` model. Gives ``.model_dump()`` /
``.model_validate()`` and JSON-schema export for consumers that want a typed
result contract. Keeping this separate from the core ``serialization`` module
means the dependency-free dict helpers stay usable without ``pydantic``.

Install with ``pip install isanlp_rst[pydantic]``.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from isanlp.annotation_rst import DiscourseUnit


class RstNode(BaseModel):
    """Validated, JSON-serialisable representation of one RST tree node.

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
    left: RstNode | None = None
    right: RstNode | None = None

    @classmethod
    def from_tree(cls, node: DiscourseUnit | None) -> RstNode | None:
        """Build an ``RstNode`` from a ``DiscourseUnit`` tree (recursive)."""
        if node is None:
            return None
        return cls(
            id=node.id,
            relation=node.relation,
            nuclearity=node.nuclearity,
            start=node.start,
            end=node.end,
            text=node.text,
            proba=node.proba,
            entropy=node.entropy,
            left=cls.from_tree(node.left),
            right=cls.from_tree(node.right),
        )

    def to_tree(self) -> DiscourseUnit:
        """Reconstruct a ``DiscourseUnit`` tree from this model (recursive)."""
        return DiscourseUnit(
            id=self.id,
            relation=self.relation or "",
            nuclearity=self.nuclearity or "",
            start=self.start,
            end=self.end,
            text=self.text or "",
            proba=self.proba,
            entropy=self.entropy,
            left=self.left.to_tree() if self.left is not None else None,
            right=self.right.to_tree() if self.right is not None else None,
        )


__all__ = ["RstNode"]

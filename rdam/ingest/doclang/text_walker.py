"""Exactly-once DocLang body-text traversal."""

from collections.abc import Iterable
from typing import Literal

from .loader import XmlElement, local_name

_METADATA_HEAD_ELEMENTS = frozenset(
    {
        "caption",
        "custom",
        "description",
        "href",
        "label",
        "layer",
        "location",
        "summary",
        "thread",
        "xref",
    }
)


def iter_body_slots(
    element: XmlElement,
    *,
    excluded_subtrees: frozenset[str] = frozenset(),
) -> Iterable[tuple[XmlElement, Literal["text", "tail"]]]:
    """Yield exact slot owners, excluding metadata bodies but retaining tails."""
    if element.text:
        yield element, "text"
    for child in element:
        if isinstance(child.tag, str):
            name = local_name(child)
            if name not in _METADATA_HEAD_ELEMENTS and name not in excluded_subtrees:
                yield from iter_body_slots(child, excluded_subtrees=excluded_subtrees)
        if child.tail:
            yield child, "tail"


def iter_sibling_slots(
    element: XmlElement,
    *,
    excluded_subtrees: frozenset[str] = frozenset(),
) -> Iterable[tuple[XmlElement, Literal["text", "tail"]]]:
    """Select a sibling body and its tail exactly once."""
    if isinstance(element.tag, str) and local_name(element) not in _METADATA_HEAD_ELEMENTS | excluded_subtrees:
        yield from iter_body_slots(element, excluded_subtrees=excluded_subtrees)
    if element.tail:
        yield element, "tail"


def iter_body_text(element: XmlElement, *, excluded_subtrees: frozenset[str] = frozenset()) -> Iterable[str]:
    for node, slot in iter_body_slots(element, excluded_subtrees=excluded_subtrees):
        yield (node.text if slot == "text" else node.tail) or ""


def iter_sibling_body_text(element: XmlElement, *, excluded_subtrees: frozenset[str] = frozenset()) -> Iterable[str]:
    for node, slot in iter_sibling_slots(element, excluded_subtrees=excluded_subtrees):
        yield (node.text if slot == "text" else node.tail) or ""


def body_text(element: XmlElement, *, excluded_subtrees: frozenset[str] = frozenset()) -> str:
    return "".join(iter_body_text(element, excluded_subtrees=excluded_subtrees)).strip()


__all__ = ["body_text", "iter_body_text", "iter_sibling_body_text"]

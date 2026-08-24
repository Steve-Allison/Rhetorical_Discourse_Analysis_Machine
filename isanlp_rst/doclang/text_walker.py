"""Exactly-once DocLang body-text traversal."""

from collections.abc import Iterable

from lxml import etree

from .eligibility import METADATA_HEAD_ELEMENTS
from .loader import local_name


def iter_body_text(
    element: etree._Element,
    *,
    excluded_subtrees: frozenset[str] = frozenset(),
) -> Iterable[str]:
    """Yield eligible text beneath ``element`` without its outer tail.

    The root is an explicitly selected content element. Metadata-head
    descendants are omitted at every depth, while each omitted element's tail
    remains body text and is emitted once. Selected structural subtrees can be
    excluded without dropping their tails.
    """

    if element.text:
        yield element.text
    for child in element:
        if not isinstance(child.tag, str):
            if child.tail:
                yield child.tail
            continue
        child_name = local_name(child)
        if child_name not in METADATA_HEAD_ELEMENTS and child_name not in excluded_subtrees:
            yield from iter_body_text(child, excluded_subtrees=excluded_subtrees)
        if child.tail:
            yield child.tail


def iter_sibling_body_text(
    element: etree._Element,
    *,
    excluded_subtrees: frozenset[str] = frozenset(),
) -> Iterable[str]:
    """Yield a sibling's eligible body plus its tail exactly once."""

    if (
        isinstance(element.tag, str)
        and local_name(element) not in METADATA_HEAD_ELEMENTS
        and local_name(element) not in excluded_subtrees
    ):
        yield from iter_body_text(element, excluded_subtrees=excluded_subtrees)
    if element.tail:
        yield element.tail


def body_text(
    element: etree._Element,
    *,
    excluded_subtrees: frozenset[str] = frozenset(),
) -> str:
    """Return normalized eligible body text for an explicitly selected root."""

    return "".join(iter_body_text(element, excluded_subtrees=excluded_subtrees)).strip()


__all__ = ["body_text", "iter_body_text", "iter_sibling_body_text"]

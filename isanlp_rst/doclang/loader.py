"""Parse a DocLang 0.5 ``.dclg.xml`` file into a usable element tree.

The ``doclang`` PyPI package (``doclang-project/doclang``) is
validator-only — it exposes ``validate(path)`` and ``ValidationError``
and has no DOM. We parse the XML ourselves with ``lxml`` and provide
the canonical addressing helper ``local_path`` (verified Phase 1 to
round-trip 100% across the 40-fixture corpus).

``lxml.etree.ElementTree.getpath()`` is NOT used: on default-namespaced
documents it emits ``/*/*[N]`` wildcards (`spec.md:219-241` recommends a
default namespace, so this is the common case). The local-name path
``/doclang[1]/heading[2]`` is namespace-agnostic and human-readable.
"""

from __future__ import annotations

from pathlib import Path

from lxml import etree


def local_name(element: etree._Element) -> str:
    """Return the element's tag with any XML namespace stripped."""
    tag = element.tag
    if isinstance(tag, str) and tag.startswith("{"):
        return tag.split("}", 1)[1]
    return tag if isinstance(tag, str) else ""


def local_path(element: etree._Element) -> str:
    """Return a local-name canonical XPath for ``element``.

    Each step is ``local_name[i]`` where ``i`` is the 1-based position
    among siblings sharing the same local name (case-sensitive). The
    output is identical regardless of whether the source declares an
    XML namespace; verified Phase 1 against all 40 valid fixtures.

    Example output: ``"/doclang[1]/heading[2]/text[1]"``.
    """
    parts: list[str] = []
    cur: etree._Element | None = element
    while cur is not None and isinstance(cur.tag, str):
        parent = cur.getparent()
        my_local = local_name(cur)
        if parent is None:
            parts.append(f"/{my_local}[1]")
            break
        same = [c for c in parent if isinstance(c.tag, str) and local_name(c) == my_local]
        pos = same.index(cur) + 1
        parts.append(f"/{my_local}[{pos}]")
        cur = parent
    return "".join(reversed(parts))


def parse_doclang_xml(path: Path) -> etree._ElementTree:
    """Parse the ``.dclg.xml`` file at ``path`` and return the ElementTree.

    Validation is delegated to ``isanlp_rst.doclang._entry`` (which uses
    the ``doclang`` package's ``validate`` when ``validate_xml=True``).
    """
    return etree.parse(path)

"""Utilities for parsing ``.rs3`` and text files into in-memory objects."""

import re
from pathlib import Path
from xml.dom import minidom
from typing import cast
from xml.dom.minidom import Document, Text
from xml.parsers.expat import ExpatError

from lxml import etree

from .rstweb_classes import NODE, NodeMap, get_left_right

__all__ = ["read_rst", "read_text", "read_relfile"]

# Same XXE posture as DocLang loader — RS3 is untrusted input.
_SECURE_PARSER = etree.XMLParser(
    resolve_entities=False,
    no_network=True,
    dtd_validation=False,
    load_dtd=False,
    huge_tree=False,
)

_REL_UNSAFE = re.compile(r"[:;,]")


def _parse_rs3_dom(xml_content: str) -> Document:
    """Parse RS3 XML with a hardened lxml parser, then expose a minidom tree.

    Entity expansion / network DTD fetches are disabled before any DOM is
    built. The minidom step is only for the existing attribute/node walkers.
    """
    try:
        root = etree.fromstring(xml_content.encode("utf-8"), parser=_SECURE_PARSER)
    except etree.XMLSyntaxError as exc:
        raise ExpatError(str(exc)) from exc
    safe_xml = etree.tostring(root, encoding="unicode")
    return minidom.parseString(safe_xml)


def _sanitize_relname(relname: str) -> str:
    return _REL_UNSAFE.sub("", relname)


type NodeRow = tuple[str, int, int, str, int, str, str, str]


def read_rst(filename: str | Path, rel_hash: dict[str, str]) -> NodeMap | str:
    """Parse an RS3 file into a representation that can be stored in SQLite.

    ``rel_hash`` is a mutable out-parameter: the caller passes an empty dict
    and reads relation name → type after return.
    """
    try:
        xml_content = Path(filename).read_text(encoding="utf-8")
    except OSError as err:
        return f"Unable to read '{filename}': {err.strerror}."

    try:
        xmldoc = _parse_rs3_dom(xml_content)
    except ExpatError:
        return "Invalid .rs3 file"

    nodes: list[NodeRow] = []
    ordered_id: dict[str, int] = {}
    schemas: list[str] = []
    default_rst = ""

    for rel in xmldoc.getElementsByTagName("rel"):
        relname = _sanitize_relname(rel.attributes["name"].value)
        if rel.hasAttribute("type"):
            rel_type = rel.attributes["type"].value
            keyed = f"{relname}_{rel_type[0:1]}"
            rel_hash[keyed] = rel_type
            if rel_type == "rst" and default_rst == "":
                default_rst = keyed
        else:
            schemas.append(relname)

    item_list = xmldoc.getElementsByTagName("segment")
    if len(item_list) < 1:
        return '<div class="warn">No segment elements found in .rs3 file</div>'

    id_counter = 0
    for segment in item_list:
        id_counter += 1
        ordered_id[segment.attributes["id"].value] = id_counter
    for group in xmldoc.getElementsByTagName("group"):
        id_counter += 1
        ordered_id[group.attributes["id"].value] = id_counter
    ordered_id["0"] = 0

    element_types: dict[str, str] = {}
    for element in xmldoc.getElementsByTagName("segment"):
        element_types[element.attributes["id"].value] = "edu"
    for element in xmldoc.getElementsByTagName("group"):
        element_types[element.attributes["id"].value] = element.attributes["type"].value

    id_counter = 0
    for segment in xmldoc.getElementsByTagName("segment"):
        id_counter += 1
        parent = segment.attributes["parent"].value if segment.hasAttribute("parent") else "0"
        relname = segment.attributes["relname"].value if segment.hasAttribute("relname") else default_rst

        if relname in schemas:
            relname = "span"
            relname = _sanitize_relname(relname)
        if parent in element_types:
            if element_types[parent] == "multinuc" and f"{relname}_m" in rel_hash:
                relname = f"{relname}_m"
            elif relname != "span":
                relname = f"{relname}_r"
        elif not relname.endswith("_r") and len(relname) > 0:
            relname = f"{relname}_r"
        edu_id = segment.attributes["id"].value
        contents = cast(Text, segment.childNodes[0]).data.strip()
        nodes.append(
            (
                str(ordered_id[edu_id]),
                id_counter,
                id_counter,
                str(ordered_id[parent]),
                0,
                "edu",
                contents,
                relname,
            )
        )

    for group in xmldoc.getElementsByTagName("group"):
        if group.attributes.length == 4:
            parent = group.attributes["parent"].value
        else:
            parent = "0"
        if group.attributes.length == 4:
            relname = group.attributes["relname"].value
            if relname in schemas:
                relname = "span"
            relname = _sanitize_relname(relname)
            if parent in element_types:
                if element_types[parent] == "multinuc" and f"{relname}_m" in rel_hash:
                    relname = f"{relname}_m"
                elif relname != "span":
                    relname = f"{relname}_r"
            else:
                relname = ""
        else:
            relname = ""
        group_id = group.attributes["id"].value
        group_type = group.attributes["type"].value
        nodes.append(
            (
                str(ordered_id[group_id]),
                0,
                0,
                str(ordered_id[parent]),
                0,
                group_type,
                "",
                relname,
            )
        )

    elements: NodeMap = {}
    for row in nodes:
        elements[row[0]] = NODE(row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7], "")

    for element in elements:
        if elements[element].kind == "edu":
            get_left_right(element, elements, 0, 0, rel_hash)

    return elements


def read_text(filename: str | Path, rel_hash: dict[str, str]) -> NodeMap:
    id_counter = 0
    nodes: NodeMap = {}
    lines = Path(filename).read_text(encoding="utf-8").splitlines(keepends=True)
    if len(rel_hash) < 2:
        rel_hash["elaboration_r"] = "rst"
        rel_hash["joint_m"] = "multinuc"

    rels = dict(sorted(rel_hash.items()))
    try:
        first_relname, first_reltype = next(iter(rels.items()))
    except StopIteration as exc:
        raise ValueError("Relation map is empty; expected at least one relation.") from exc

    for line in lines:
        id_counter += 1
        nodes[str(id_counter)] = NODE(
            str(id_counter),
            id_counter,
            id_counter,
            "0",
            0,
            "edu",
            line.strip(),
            first_relname,
            first_reltype,
        )

    return nodes


def read_relfile(filename: str | Path) -> dict[str, str]:
    rel_lines = Path(filename).read_text(encoding="utf-8").splitlines(keepends=True)
    rels: dict[str, str] = {}
    for line in rel_lines:
        if line.find("\t") > 0:
            rel_data = line.split("\t")
            match rel_data[1].strip():
                case "rst":
                    rels[f"{rel_data[0].strip()}_r"] = "rst"
                case "multinuc":
                    rels[f"{rel_data[0].strip()}_m"] = "multinuc"
    return rels

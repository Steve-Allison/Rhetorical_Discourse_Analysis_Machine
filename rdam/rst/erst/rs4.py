"""Faithful RS4 XML reader and writer for GUM eRST and classical RST."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from lxml import etree

_SECURE_PARSER = etree.XMLParser(
    resolve_entities=False,
    no_network=True,
    dtd_validation=False,
    load_dtd=False,
    huge_tree=False,
)


@dataclass(frozen=True, slots=True)
class RS4Segment:
    """An individual text segment (<segment>) in RS4 XML."""

    id: int
    text: str
    parent: int | None = None
    relname: str = "span"


@dataclass(frozen=True, slots=True)
class RS4Group:
    """A span or multinuclear group (<group>) in RS4 XML."""

    id: int
    type: str  # "span" or "multinuc"
    parent: int | None = None
    relname: str = "span"


@dataclass(frozen=True, slots=True)
class RS4SecEdge:
    """A secondary edge (<secedge>) in RS4 XML."""

    id: str
    source: int
    target: int
    relname: str


@dataclass(frozen=True, slots=True)
class RS4Signal:
    """A discourse signal (<signal>) in RS4 XML."""

    source: str  # Can be a node id (e.g. "1") or secedge id (e.g. "30-101")
    type: str
    subtype: str
    tokens: tuple[int, ...] = ()  # 1-based token integers as serialized in RS4
    status: str = "predicted"


@dataclass(frozen=True, slots=True)
class RS4Document:
    """Complete RS4 XML document representation."""

    relations: dict[str, str] = field(default_factory=dict)  # relname -> "rst" | "multinuc"
    sigtypes: dict[str, tuple[str, ...]] = field(default_factory=dict)  # sigtype -> tuple of subtypes
    segments: tuple[RS4Segment, ...] = ()
    groups: tuple[RS4Group, ...] = ()
    secedges: tuple[RS4SecEdge, ...] = ()
    signals: tuple[RS4Signal, ...] = ()


class RS4Reader:
    """Reads and validates RS4 XML files."""

    @staticmethod
    def _parse_tokens(tokens_str: str | None) -> tuple[int, ...]:
        if not tokens_str or not tokens_str.strip():
            return ()
        out: list[int] = []
        for part in tokens_str.strip().split(","):
            part_clean = part.strip()
            if not part_clean:
                continue
            if "-" in part_clean:
                # Support range "1-3"
                subparts = part_clean.split("-", 1)
                if len(subparts) == 2 and subparts[0].isdigit() and subparts[1].isdigit():
                    start_tok, end_tok = int(subparts[0]), int(subparts[1])
                    out.extend(range(start_tok, end_tok + 1))
                    continue
            if part_clean.isdigit():
                out.append(int(part_clean))
        return tuple(out)

    @classmethod
    def read_string(cls, xml_text: str) -> RS4Document:
        """Parse RS4 XML text into an RS4Document."""
        root = etree.fromstring(xml_text.encode("utf-8"), parser=_SECURE_PARSER)
        return cls._from_tree(root)

    @classmethod
    def read_file(cls, path: Path | str) -> RS4Document:
        """Parse an RS4 XML file into an RS4Document."""
        tree = etree.parse(str(path), parser=_SECURE_PARSER)
        return cls._from_tree(tree.getroot())

    @classmethod
    def _from_tree(cls, root: Any) -> RS4Document:
        if root.tag != "rst":
            raise ValueError(f"Expected root element <rst>, found <{root.tag}>")
        if root.find("header") is None:
            raise ValueError("Missing <header> element in RS4 document")
        if root.find("body") is None:
            raise ValueError("Missing <body> element in RS4 document")

        relations: dict[str, str] = {}
        for rel_elem in root.findall(".//header/relations/rel"):
            name = rel_elem.get("name")
            rel_type = rel_elem.get("type", "rst")
            if name:
                relations[name] = rel_type

        sigtypes: dict[str, tuple[str, ...]] = {}
        for sig_elem in root.findall(".//header/sigtypes/sig"):
            sig_type = sig_elem.get("type")
            subtypes_str = sig_elem.get("subtypes", "")
            if sig_type:
                subtypes = tuple(s.strip() for s in subtypes_str.split(";") if s.strip())
                sigtypes[sig_type] = subtypes

        segments: list[RS4Segment] = []
        for seg in root.findall(".//body/segment"):
            seg_id = int(seg.get("id"))
            parent_attr = seg.get("parent")
            parent_id = int(parent_attr) if parent_attr and parent_attr.isdigit() else None
            relname = seg.get("relname", "span")
            text = "".join(seg.itertext())
            segments.append(RS4Segment(id=seg_id, text=text, parent=parent_id, relname=relname))

        groups: list[RS4Group] = []
        for grp in root.findall(".//body/group"):
            grp_id = int(grp.get("id"))
            grp_type = grp.get("type", "span")
            parent_attr = grp.get("parent")
            parent_id = int(parent_attr) if parent_attr and parent_attr.isdigit() else None
            relname = grp.get("relname", "span")
            groups.append(RS4Group(id=grp_id, type=grp_type, parent=parent_id, relname=relname))

        secedges: list[RS4SecEdge] = []
        for sec in root.findall(".//body/secedges/secedge"):
            sec_id = sec.get("id", f"{sec.get('source')}-{sec.get('target')}")
            source = int(sec.get("source"))
            target = int(sec.get("target"))
            relname = sec.get("relname", "")
            secedges.append(RS4SecEdge(id=sec_id, source=source, target=target, relname=relname))

        signals: list[RS4Signal] = []
        for sig in root.findall(".//body/signals/signal"):
            source = sig.get("source", "")
            sig_type = sig.get("type", "")
            subtype = sig.get("subtype", "")
            tokens = cls._parse_tokens(sig.get("tokens"))
            status = sig.get("status", "predicted")
            signals.append(RS4Signal(source=source, type=sig_type, subtype=subtype, tokens=tokens, status=status))

        return RS4Document(
            relations=relations,
            sigtypes=sigtypes,
            segments=tuple(segments),
            groups=tuple(groups),
            secedges=tuple(secedges),
            signals=tuple(signals),
        )


class RS4Writer:
    """Writes RS4Document objects to well-formed RS4 XML."""

    @classmethod
    def to_string(cls, doc: RS4Document) -> str:
        """Serialize an RS4Document to an XML string."""
        root = etree.Element("rst")
        header = etree.SubElement(root, "header")

        # Relations
        if doc.relations:
            relations_elem = etree.SubElement(header, "relations")
            for name, rel_type in doc.relations.items():
                etree.SubElement(relations_elem, "rel", attrib={"name": name, "type": rel_type})

        # Sigtypes
        if doc.sigtypes:
            sigtypes_elem = etree.SubElement(header, "sigtypes")
            for sig_type, subtypes in doc.sigtypes.items():
                etree.SubElement(sigtypes_elem, "sig", attrib={"type": sig_type, "subtypes": ";".join(subtypes)})

        body = etree.SubElement(root, "body")

        # Segments
        for seg in doc.segments:
            attrs = {"id": str(seg.id), "relname": seg.relname}
            if seg.parent is not None:
                attrs["parent"] = str(seg.parent)
            seg_elem = etree.SubElement(body, "segment", attrib=attrs)
            seg_elem.text = seg.text

        # Groups
        for grp in doc.groups:
            attrs = {"id": str(grp.id), "type": grp.type, "relname": grp.relname}
            if grp.parent is not None:
                attrs["parent"] = str(grp.parent)
            etree.SubElement(body, "group", attrib=attrs)

        # Secedges
        if doc.secedges:
            secedges_elem = etree.SubElement(body, "secedges")
            for sec in doc.secedges:
                etree.SubElement(
                    secedges_elem,
                    "secedge",
                    attrib={
                        "id": str(sec.id),
                        "source": str(sec.source),
                        "target": str(sec.target),
                        "relname": sec.relname,
                    },
                )

        # Signals
        if doc.signals:
            signals_elem = etree.SubElement(body, "signals")
            for sig in doc.signals:
                attrs = {
                    "source": str(sig.source),
                    "type": sig.type,
                    "subtype": sig.subtype,
                    "tokens": ",".join(str(t) for t in sig.tokens),
                }
                if sig.status:
                    attrs["status"] = sig.status
                etree.SubElement(signals_elem, "signal", attrib=attrs)

        xml_bytes = etree.tostring(root, encoding="utf-8", pretty_print=True, xml_declaration=False)
        return xml_bytes.decode("utf-8")

    @classmethod
    def write_file(cls, doc: RS4Document, path: Path | str) -> None:
        """Write an RS4Document to an XML file."""
        target_path = Path(path)
        target_path.write_text(cls.to_string(doc), encoding="utf-8")

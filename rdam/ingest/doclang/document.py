"""Request-local validated DocLang documents and exact private fragment selectors."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from tempfile import NamedTemporaryFile
from types import MappingProxyType
from typing import Literal

from lxml import etree

from .errors import InvalidDoclangError
from .loader import DoclangArchiveMember, XmlElement, parse_control_xml, load_doclang_archive, local_path_index


@dataclass(frozen=True, slots=True)
class ElementTextSlot:
    kind: Literal["element_slot"] = field(default="element_slot", init=False)
    owner_path: str
    slot: Literal["text", "tail"]


@dataclass(frozen=True, slots=True)
class NonElementTailSlot:
    kind: Literal["non_element_tail"] = field(default="non_element_tail", init=False)
    parent_path: str
    child_index: int
    node_kind: Literal["comment", "processing_instruction"]

    def __post_init__(self) -> None:
        if self.child_index < 0:
            raise ValueError("child index must be nonnegative")


type FragmentSelector = ElementTextSlot | NonElementTailSlot


@dataclass(frozen=True, slots=True)
class DoclangTextFragment:
    selector: FragmentSelector
    text: str
    surface_path: str


@dataclass(frozen=True, slots=True)
class DoclangDocument:
    """Private decode context; its tree never enters public immutable results."""

    xml_bytes: bytes
    root: XmlElement
    paths: Mapping[XmlElement, str]
    elements: Mapping[str, XmlElement]
    members: tuple[DoclangArchiveMember, ...] = ()

    @classmethod
    def load(cls, data: bytes, *, archive: bool = False) -> DoclangDocument:
        from doclang import ValidationError, validate

        loaded = load_doclang_archive(data) if archive else None
        xml = loaded.document_bytes if loaded is not None else data
        try:
            with NamedTemporaryFile(suffix=".dclg") as stream:
                stream.write(xml)
                stream.flush()
                validate(stream.name, allow_empty_namespace=True)
            root = loaded.document_root if loaded is not None else parse_control_xml(xml, part_name="document.xml")
        except (ValidationError, InvalidDoclangError) as exc:
            raise InvalidDoclangError(f"DocLang XML failed current validation ({type(exc).__name__})") from exc
        paths = local_path_index(root)
        return cls(
            xml,
            root,
            MappingProxyType(paths),
            MappingProxyType({path: node for node, path in paths.items()}),
            loaded.members if loaded is not None else (),
        )

    def element(self, path: str) -> XmlElement:
        try:
            return self.elements[path]
        except KeyError as exc:
            raise LookupError(f"unknown DocLang element path: {path}") from exc

    def resolve_fragment(self, selector: FragmentSelector) -> str:
        if isinstance(selector, ElementTextSlot):
            node = self.element(selector.owner_path)
            value = node.text if selector.slot == "text" else node.tail
        else:
            children = tuple(self.element(selector.parent_path))
            if selector.child_index >= len(children):
                raise LookupError("DocLang non-element tail index is outside its parent")
            node = children[selector.child_index]
            expected = etree.Comment if selector.node_kind == "comment" else etree.ProcessingInstruction
            if node.tag is not expected:
                raise LookupError("DocLang non-element tail kind does not match")
            value = node.tail
        if value is None:
            raise LookupError("DocLang text slot is absent")
        return value

    def fragment(
        self, node: XmlElement, slot: Literal["text", "tail"], surface_path: str
    ) -> DoclangTextFragment | None:
        value = node.text if slot == "text" else node.tail
        if value is None:
            return None
        if isinstance(node.tag, str):
            selector: FragmentSelector = ElementTextSlot(self.paths[node], slot)
        else:
            parent = node.getparent()
            if parent is None or slot != "tail":
                raise LookupError("non-element content is not an eligible text fragment")
            if node.tag is etree.Comment:
                kind = "comment"
            elif node.tag is etree.ProcessingInstruction:
                kind = "processing_instruction"
            else:
                raise InvalidDoclangError("unsupported non-element DocLang text node")
            selector = NonElementTailSlot(self.paths[parent], tuple(parent).index(node), kind)
        return DoclangTextFragment(selector, value, surface_path)

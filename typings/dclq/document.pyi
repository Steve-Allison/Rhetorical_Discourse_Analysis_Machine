from pathlib import Path
from typing import Any

from lxml import etree

class Unit:
    logical_type: str
    text: str
    all_text: str
    xpaths: tuple[str, ...]
    doc_items: tuple[str, ...]
    item_ref: str | None
    page: int | None
    pages: tuple[int, ...]
    layer: str
    item: Any
    row: int | None
    col: int | None
    container: bool
    metadata: str
    @property
    def xpath(self) -> str: ...

class LoadedDocument:
    name: str
    input_type: str
    raw: bytes
    raw_root: etree._Element
    query_root: etree._Element
    document: Any
    source_map: Any
    members: tuple[str, ...]
    units: list[Unit]
    context_units: list[Unit]
    raw_elements: dict[str, etree._Element]
    source_pages: dict[str, int]
    @classmethod
    def load(
        cls,
        source: str | Path,
        *,
        stdin_bytes: bytes | None = ...,
        validate: bool = ...,
    ) -> LoadedDocument: ...
    def nearest_heading_ref(self, unit: Unit) -> str | None: ...

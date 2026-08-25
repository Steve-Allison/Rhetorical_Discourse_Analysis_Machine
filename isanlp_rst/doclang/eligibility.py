"""Single immutable eligibility policy for DocLang harvest and boundaries."""

from dataclasses import dataclass


METADATA_HEAD_ELEMENTS: frozenset[str] = frozenset(
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


@dataclass(frozen=True, slots=True)
class DoclangEligibility:
    """All switches that determine text harvest and boundary membership."""

    include_prose: bool = True
    include_picture_captions: bool = True
    include_lists: bool = True
    include_table_cells: bool = True
    include_code_blocks: bool = False
    include_formulas: bool = False
    include_field_regions: bool = False
    include_background: bool = False
    include_furniture: bool = False
    include_page_boundaries: bool = True
    include_group_boundaries: bool = True
    include_heading_boundaries: bool = True

    @property
    def allowed_layers(self) -> frozenset[str]:
        """Return the DocLang layers admitted by this policy."""

        layers = {"body"}
        if self.include_background:
            layers.add("background")
        if self.include_furniture:
            layers.add("furniture")
        return frozenset(layers)

    def allows_layer(self, layer: str) -> bool:
        """Return whether ``layer`` contributes harvestable content."""

        return layer in self.allowed_layers

    def allows_main_kind(self, kind: str) -> bool:
        """Return whether a semantic kind contributes to the main harvest."""

        if kind in {"text", "footnote", "key", "value"}:
            return self.include_prose
        if kind == "heading":
            return self.include_prose
        if kind == "list_item":
            return self.include_lists
        if kind == "caption":
            return self.include_picture_captions
        if kind == "code":
            return self.include_code_blocks
        if kind == "formula":
            return self.include_formulas
        if kind in {"page_header", "page_footer"}:
            return self.include_furniture
        return False


__all__ = ["DoclangEligibility", "METADATA_HEAD_ELEMENTS"]

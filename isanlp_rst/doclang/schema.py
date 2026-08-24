"""Self-contained DocLang-native RST wire schema."""

import json
from dataclasses import asdict, dataclass
from operator import attrgetter
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from isanlp_rst.contracts import FormatRstAnalysis


@dataclass(frozen=True, slots=True)
class HarvestSpan:
    """One eligible DocLang text span with parser-input coordinates."""

    xpath: str
    thread_id: int | None
    layer: str
    text: str
    start: int
    end: int
    kind: str = ""
    row_idx: int | None = None
    col_idx: int | None = None


@dataclass(frozen=True, slots=True)
class HarvestResult:
    """Concatenated document harvest and its source-address spans."""

    full_text: str
    spans: tuple[HarvestSpan, ...]


@dataclass(frozen=True, slots=True)
class TableHarvest:
    """One table-cell harvest with coordinates local to ``full_text``."""

    table_idx: int
    marker_xpath: str
    full_text: str
    spans: tuple[HarvestSpan, ...]


@dataclass(frozen=True, slots=True)
class Boundary:
    """One independently detected DocLang structural boundary."""

    id: str
    kind: str
    label: str | None
    parent_xpath: str | None
    xpaths: tuple[str, ...]
    level: int | None = None
    page_no: int | None = None


@dataclass(frozen=True, slots=True)
class RstRelation:
    """One self-contained internal RST node."""

    id: int
    text: str
    char_span: tuple[int, int]
    edu_span: tuple[int, int]
    relation: str
    nuclearity: str
    nucleus_xpaths: tuple[str, ...]
    satellite_xpaths: tuple[str, ...]
    nucleus_thread_ids: tuple[int, ...]
    satellite_thread_ids: tuple[int, ...]
    depth: int
    left_id: int
    right_id: int
    boundary_memberships: tuple[str, ...]
    note: str | None = None


@dataclass(frozen=True, slots=True)
class RstEdu:
    """One self-contained Elementary Discourse Unit."""

    id: int
    text: str
    char_span: tuple[int, int]
    edu_span: tuple[int, int]
    xpaths: tuple[str, ...]
    thread_ids: tuple[int, ...]
    depth: int


@dataclass(frozen=True, slots=True)
class TableAnalysis:
    """One table-local RST projection."""

    id: str
    relations: tuple[RstRelation, ...]
    edus: tuple[RstEdu, ...]


@dataclass(frozen=True, slots=True)
class DoclangRstResult:
    """Top-level output of ``parse_doclang``."""

    schema_name: str
    schema_version: str
    tool: str
    tool_version: str
    source_revision: str
    model_version: str
    inventory: str
    source: str
    source_origin: dict[str, Any]
    boundaries: tuple[Boundary, ...]
    relations: tuple[RstRelation, ...]
    edus: tuple[RstEdu, ...]
    table_analyses: tuple[TableAnalysis, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        """Return JSON-shaped plain data."""

        return json.loads(self.to_json(indent=None))

    def to_json(self, *, indent: int | None = 2) -> str:
        """Serialize deterministically without non-JSON dataclass values."""

        return json.dumps(asdict(self), ensure_ascii=False, indent=indent)

    def to_format_analysis(self) -> FormatRstAnalysis:
        """Project through the single shared ``RstAnalysis`` conversion."""

        from isanlp_rst._rst_common._projection import ProjectionTree, projection_to_format_analysis

        return projection_to_format_analysis(
            ProjectionTree(document_id=self.source, relations=self.relations, edus=self.edus),
            {
                table.id: ProjectionTree(
                    document_id=f"{self.source}_{table.id}",
                    relations=table.relations,
                    edus=table.edus,
                )
                for table in self.table_analyses
            },
            refs_of_edu=attrgetter("xpaths"),
            producer=self.tool,
            software_version=self.tool_version,
            source_revision=self.source_revision,
            model_id=self.model_version,
        )

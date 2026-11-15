"""Native gIBIS result schema across supplied, explicitly derived, and extracted modes."""

from typing import Literal, Self
from pydantic import Field, model_validator
from rdam._native_output import DerivedFromRecord, ExtractionRecord
from rdam._strict import StrictModel
from rdam.ibis.grammar import (
    DeliberationMap,
    IbisInputLink,
    IbisInputNode,
    IbisStructure,
    deliberation_map,
)
from rdam.ingest.contracts.evidence import SourceEvidenceSpan


class IbisStructurePayload(StrictModel):
    nodes: tuple[IbisInputNode, ...] = ()
    links: tuple[IbisInputLink, ...] = ()


class IbisNodeEvidence(StrictModel):
    node_id: str = Field(min_length=1)
    span: SourceEvidenceSpan


class PositionOutput(StrictModel):
    id: str
    supporting: tuple[str, ...]
    objecting: tuple[str, ...]


class IssueOutput(StrictModel):
    id: str
    positions: tuple[PositionOutput, ...]
    raised_by: tuple[str, ...]
    questions: tuple[str, ...]
    generalizes: tuple[str, ...]
    specializes: tuple[str, ...]
    replaces: tuple[str, ...]


class MapOutput(StrictModel):
    issues: tuple[IssueOutput, ...]
    issues_without_positions: tuple[str, ...]
    positions_without_arguments: tuple[str, ...]
    isolated_nodes: tuple[str, ...]


class IbisOutput(StrictModel):
    structure: IbisStructurePayload
    input_origin: Literal["supplied", "explicitly_derived", "extracted"]
    extraction: ExtractionRecord | None
    grammar: Literal["gibis-v1"]
    map: MapOutput
    node_evidence: tuple[IbisNodeEvidence, ...] = Field(default=(), exclude_if=lambda value: not value)
    derived_from: DerivedFromRecord | None = Field(default=None, exclude_if=lambda value: value is None)

    @model_validator(mode="after")
    def map_reproduces_structure(self) -> Self:
        if self.input_origin == "extracted":
            if self.extraction is None:
                raise ValueError("extracted IBIS output requires an extraction record")
            if self.derived_from is not None:
                raise ValueError("extracted IBIS output cannot claim caller derivation")
        else:
            if self.extraction is not None:
                raise ValueError("supplied/derived IBIS output must have extraction=None")
            if not self.structure.nodes:
                raise ValueError("supplied/derived IBIS structure requires at least one node")
            if (self.input_origin == "explicitly_derived") != (self.derived_from is not None):
                raise ValueError("IBIS input origin must agree with its derivation reference")

        if self.structure.nodes:
            structure = IbisStructure.from_payload(self.structure.model_dump(mode="json", by_alias=True))
            expected_map: DeliberationMap = deliberation_map(structure)
        else:
            if self.structure.links:
                raise ValueError("empty IBIS structure cannot carry links")
            expected_map = {
                "issues": [],
                "issues_without_positions": [],
                "positions_without_arguments": [],
                "isolated_nodes": [],
            }
        if self.map.model_dump(mode="json") != expected_map:
            raise ValueError("IBIS map must reproduce the supplied structure")
        return self

"""Native gIBIS result schema, including unfilled issues and positions."""

from typing import Literal, Self
from pydantic import Field, model_validator
from rdam._native_output import DerivedFromRecord
from rdam._strict import StrictModel
from rdam.ibis.grammar import IbisInput, IbisStructure, deliberation_map


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
    structure: IbisInput
    input_origin: Literal["supplied", "explicitly_derived"]
    extraction: None
    grammar: Literal["gibis-v1"]
    map: MapOutput
    derived_from: DerivedFromRecord | None = Field(default=None, exclude_if=lambda value: value is None)

    @model_validator(mode="after")
    def map_reproduces_structure(self) -> Self:
        structure = IbisStructure.from_payload(self.structure.model_dump(mode="json", by_alias=True))
        if self.map.model_dump(mode="json") != deliberation_map(structure):
            raise ValueError("IBIS map must reproduce the supplied structure")
        if (self.input_origin == "explicitly_derived") != (self.derived_from is not None):
            raise ValueError("IBIS input origin must agree with its derivation reference")
        return self

"""Native production outcome schemas remain owned by the existing ingest contract."""

from typing import Any, Self
from pydantic import Field, RootModel, model_validator
from rdam.ingest.contracts.analysis import ProductionAnalysisOutcome
from rdam.ingest.contracts.inference import OutputFormalism


def _formalism_schema(formalism: OutputFormalism) -> dict[str, Any]:
    constraint: dict[str, Any] = {"const": formalism.value}
    for field in ("output_formalism", "policy", "semantic"):
        constraint = {"properties": {field: constraint}}
    return {"allOf": [constraint]}


class RstOutput(RootModel[ProductionAnalysisOutcome]):
    root: ProductionAnalysisOutcome = Field(json_schema_extra=_formalism_schema(OutputFormalism.RST_TREE))

    @model_validator(mode="after")
    def correct_formalism(self) -> Self:
        if self.root.semantic.policy.output_formalism is not OutputFormalism.RST_TREE:
            raise ValueError("RST output requires rst_tree")
        return self


class ErstOutput(RootModel[ProductionAnalysisOutcome]):
    root: ProductionAnalysisOutcome = Field(json_schema_extra=_formalism_schema(OutputFormalism.ERST_GRAPH))

    @model_validator(mode="after")
    def correct_formalism(self) -> Self:
        if self.root.semantic.policy.output_formalism is not OutputFormalism.ERST_GRAPH:
            raise ValueError("eRST output requires erst_graph")
        return self

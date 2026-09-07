"""Native production outcome schemas remain owned by the existing ingest contract."""

from typing import Any, Self
from pydantic import Field, RootModel, model_validator
from rdam.ingest.contracts.analysis import ProductionAnalysisOutcome
from rdam.ingest.contracts.inference import OutputFormalism
from rdam.ingest.validation import validate_parser_analysis_result, validate_preparation_outcome


def _validate_native_evidence(outcome: ProductionAnalysisOutcome) -> None:
    validate_preparation_outcome(outcome.semantic.preparation)
    if outcome.semantic.parser_result is not None:
        validate_parser_analysis_result(outcome.semantic.parser_result)


def _formalism_schema(formalism: OutputFormalism) -> dict[str, Any]:
    constraint: dict[str, Any] = {"const": formalism.value}
    for field in ("output_formalism", "analysis_policy", "request", "semantic"):
        constraint = {"properties": {field: constraint}}
    return {"allOf": [constraint]}


class RstOutput(RootModel[ProductionAnalysisOutcome]):
    root: ProductionAnalysisOutcome = Field(json_schema_extra=_formalism_schema(OutputFormalism.RST_TREE))

    @model_validator(mode="after")
    def correct_formalism(self) -> Self:
        if self.root.semantic.policy.output_formalism is not OutputFormalism.RST_TREE:
            raise ValueError("RST output requires rst_tree")
        _validate_native_evidence(self.root)
        return self


class ErstOutput(RootModel[ProductionAnalysisOutcome]):
    root: ProductionAnalysisOutcome = Field(json_schema_extra=_formalism_schema(OutputFormalism.ERST_GRAPH))

    @model_validator(mode="after")
    def correct_formalism(self) -> Self:
        if self.root.semantic.policy.output_formalism is not OutputFormalism.ERST_GRAPH:
            raise ValueError("eRST output requires erst_graph")
        _validate_native_evidence(self.root)
        return self

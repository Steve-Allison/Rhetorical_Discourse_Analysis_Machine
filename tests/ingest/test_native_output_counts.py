"""Persisted summaries must remain derivable from native analytical records."""

import json
from typing import Any, Literal

import pytest

from rdam.pdtb.output import PdtbOutput
from rdam.pdtb.relations import PdtbAnalysis, RelationType
from rdam.toulmin.argument import ToulminAnalysis, ToulminLayout
from rdam.toulmin.output import ToulminOutput


def extraction() -> dict[str, Any]:
    return {"model": "fixture", "output_attempts": 1, "transport_attempts": 1,
            "instructions_digest": "a" * 64}


@pytest.mark.parametrize("mutation", ("total", "type_count", "missing_type"))
def test_pdtb_rejects_false_counts_even_for_empty_analysis(mutation: str) -> None:
    payload = {**PdtbAnalysis().to_payload(), "extraction": extraction()}
    PdtbOutput.model_validate_json(json.dumps(payload))
    if mutation == "total":
        payload["relation_count"] = 1
    else:
        counts = dict.fromkeys((kind.value for kind in RelationType), 0)
        if mutation == "type_count":
            counts["Explicit"] = 1
        else:
            del counts["Explicit"]
        payload["relation_type_counts"] = counts
    with pytest.raises(ValueError, match="counts must reproduce"):
        PdtbOutput.model_validate_json(json.dumps(payload))


@pytest.mark.parametrize("mutation", ("total", "qualified_count", "qualified_flag", "elements", "warrant"))
def test_toulmin_rejects_contradictory_saved_layouts(
    mutation: Literal["total", "qualified_count", "qualified_flag", "elements", "warrant"],
) -> None:
    analysis = ToulminAnalysis(layouts=[ToulminLayout(
        claim="The road is wet.", grounds=["It rained."], warrant="Rain wets exposed roads.",
        warrant_origin="undetermined", warrant_evidence=(), warrant_origin_reason="insufficient_context",
    )])
    payload: dict[str, Any] = {**analysis.to_payload(), "extraction": extraction()}
    ToulminOutput.model_validate_json(json.dumps(payload))
    match mutation:
        case "total":
            payload["layout_count"] = 0
        case "qualified_count":
            payload["qualified_layout_count"] = 1
        case "qualified_flag":
            payload["layouts"][0]["is_qualified"] = True
        case "elements":
            payload["layouts"][0]["elements_present"].append("backing")
        case "warrant":
            payload["layouts"][0]["warrant"] = payload["layouts"][0]["claim"]
    with pytest.raises(ValueError, match="must reproduce|warrant restates"):
        ToulminOutput.model_validate_json(json.dumps(payload))

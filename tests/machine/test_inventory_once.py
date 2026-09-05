"""Count real inventory calls; observe provider boundaries without replacing ingest."""

from collections import Counter
import sys
from types import FrameType

import pytest

from rdam import (
    AggregateRequest,
    BOUNDARY_TECHNIQUES,
    Machine,
    Technique,
    ProviderDeclaration,
    technique_curie,
    StructuredInput,
)
from rdam.dung import DungProvider
from rdam.ibis import IbisProvider
from rdam.ingest.contracts.preparation import ContentRequirement
from rdam.rst.provider import RstProvider
from tests.machine.conftest import FakeProvider, echo_result, rst_declaration, formalism, fixture_descriptor


@pytest.mark.parametrize("count", range(1, 8))
def test_inventory_and_disposition_once(count: int) -> None:
    calls: Counter[str] = Counter()

    def profile(frame: FrameType, event: str, _argument: object) -> None:
        if event == "call" and frame.f_globals.get("__name__") in {"rdam.ingest.prepare", "rdam.ingest.policy"}:
            calls[frame.f_code.co_name] += 1

    previous = sys.getprofile()
    try:
        sys.setprofile(profile)
        result = Machine().analyse(AggregateRequest.for_text("Evidence exists.", BOUNDARY_TECHNIQUES[:count]))
    finally:
        sys.setprofile(previous)
    assert calls["inventory_source"] == 1
    assert calls["apply_policy"] == 1
    assert result.preparation is not None
    assert result.preparation.preparation.inventory_coverage.covered_units == len(result.preparation.preparation.inventory)


def test_identical_requirements_receive_one_projection_object() -> None:
    requirement: ContentRequirement = RstProvider().content_requirement
    first = rst_declaration().model_copy(update={"content_requirement": requirement})
    second = ProviderDeclaration.model_validate(
        {
            **first.model_dump(),
            "technique": Technique.TOULMIN,
            "technique_curie": technique_curie(Technique.TOULMIN),
            "formalisms": (formalism("toulmin_argument", Technique.TOULMIN, first.capability),),
            "interpretations": (fixture_descriptor("toulmin_argument", Technique.TOULMIN),),
        }
    )
    providers = [FakeProvider(first, echo_result("rst_tree")), FakeProvider(second, echo_result("toulmin_argument"))]
    result = Machine(providers).analyse(
        AggregateRequest.for_text("Evidence exists.", (Technique.RST, Technique.TOULMIN))
    )
    assert providers[0].calls[0].projection is providers[1].calls[0].projection
    assert result.preparation is not None
    assert len(result.preparation.projections) == 1
    first_projection = providers[0].calls[0].projection
    second_projection = providers[1].calls[0].projection
    assert first_projection is not None and second_projection is not None
    assert (
        first_projection.prepared_document.segments[0].contributing_item_ids
        == second_projection.prepared_document.segments[0].contributing_item_ids
    )


def test_structured_providers_declare_no_requirement_and_receive_no_projection() -> None:
    declarations = (DungProvider().declaration, IbisProvider().declaration)
    providers = [FakeProvider(item, echo_result(item.formalisms[0].formalism_id)) for item in declarations]
    request = AggregateRequest.for_text(
        "Caller source.",
        (Technique.DUNG, Technique.IBIS),
        structured_inputs=(
            StructuredInput(technique=Technique.DUNG, payload={"arguments": [], "attacks": []}),
            StructuredInput(technique=Technique.IBIS, payload={"nodes": [], "links": []}),
        ),
    )
    aggregate = Machine(providers).analyse(request)
    assert aggregate.preparation is not None and aggregate.preparation.projections == ()
    for provider in providers:
        assert provider.declaration.content_requirement is None
        assert provider.calls[0].projection is None
        assert provider.calls[0].preparation is None

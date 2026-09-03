"""The Toulmin layout contract: the warrant is what makes a layout a layout (FR-019)."""

import pytest
from pydantic import ValidationError

from rdam.toulmin import IncompleteLayoutError, Rebuttal, ToulminAnalysis, ToulminLayout

FULL = {
    "claim": "The council should reject the proposal.",
    "grounds": ["It would cost £4m that is not budgeted.", "Two surveys found the site unstable."],
    "warrant": "A council should not approve unbudgeted works on unsafe ground.",
    "backing": ["The council's own capital-spending rules require a funded budget line."],
    "qualifier": "presumably",
    "rebuttals": [{"condition": "Unless central government underwrites the overspend."}],
}


class TestCoreTriad:
    def test_a_complete_layout_carries_all_six_elements(self) -> None:
        layout = ToulminLayout.model_validate(FULL)
        assert layout.elements_present == ("claim", "grounds", "warrant", "backing", "qualifier", "rebuttal")
        assert layout.is_qualified is True

    def test_claim_grounds_and_warrant_alone_is_a_valid_layout(self) -> None:
        layout = ToulminLayout.model_validate({k: FULL[k] for k in ("claim", "grounds", "warrant")})
        assert layout.elements_present == ("claim", "grounds", "warrant")
        assert layout.is_qualified is False

    def test_a_layout_without_a_warrant_is_refused(self) -> None:
        """FR-019: claim-and-premise extraction is not a Toulmin analysis."""

        with pytest.raises(ValidationError):
            ToulminLayout.model_validate({"claim": FULL["claim"], "grounds": FULL["grounds"]})

    def test_a_layout_without_grounds_is_refused(self) -> None:
        with pytest.raises(ValidationError):
            ToulminLayout.model_validate({"claim": FULL["claim"], "grounds": [], "warrant": FULL["warrant"]})

    def test_an_empty_claim_is_refused(self) -> None:
        with pytest.raises(ValidationError):
            ToulminLayout.model_validate({**FULL, "claim": "   "})


class TestWarrantIsNotRestatement:
    """A warrant that merely repeats the claim or a ground identified no inference licence."""

    def test_a_warrant_restating_the_claim_is_refused(self) -> None:
        with pytest.raises(ValidationError) as caught:
            ToulminLayout.model_validate({**FULL, "warrant": FULL["claim"]})
        assert "restates the claim" in str(caught.value)

    def test_a_warrant_restating_a_ground_is_refused(self) -> None:
        with pytest.raises(ValidationError) as caught:
            ToulminLayout.model_validate({**FULL, "warrant": FULL["grounds"][0]})
        assert "restates a ground" in str(caught.value)

    def test_the_check_ignores_case_and_surrounding_space(self) -> None:
        with pytest.raises(ValidationError):
            ToulminLayout.model_validate({**FULL, "warrant": f"  {FULL['claim'].upper()}  "})

    def test_incomplete_layout_error_is_a_layout_error(self) -> None:
        assert issubclass(IncompleteLayoutError, ValueError)


class TestPayload:
    def test_unknown_nested_rebuttal_fields_are_refused_not_discarded(self) -> None:
        with pytest.raises(ValidationError, match="extra_forbidden"):
            ToulminLayout.model_validate(
                {
                    **FULL,
                    "rebuttals": [
                        {
                            "condition": "Unless funding is found.",
                            "invented_status": "accepted",
                        }
                    ],
                }
            )

    def test_payload_round_trips_every_element(self) -> None:
        payload = ToulminLayout.model_validate(FULL).to_payload()
        assert payload["claim"] == FULL["claim"]
        assert payload["grounds"] == FULL["grounds"]
        assert payload["warrant"] == FULL["warrant"]
        assert payload["qualifier"] == "presumably"
        assert payload["rebuttals"] == [{"condition": "Unless central government underwrites the overspend.", "source_text": None}]
        assert payload["is_qualified"] is True

    def test_a_passage_that_argues_nothing_yields_an_empty_analysis(self) -> None:
        analysis = ToulminAnalysis()
        assert analysis.to_payload() == {"layouts": [], "layout_count": 0, "fully_qualified_count": 0}

    def test_analysis_counts_only_qualified_layouts(self) -> None:
        bare = {k: FULL[k] for k in ("claim", "grounds", "warrant")}
        analysis = ToulminAnalysis(
            layouts=[ToulminLayout.model_validate(FULL), ToulminLayout.model_validate(bare)]
        )
        payload = analysis.to_payload()
        assert payload["layout_count"] == 2
        assert payload["fully_qualified_count"] == 1

    def test_a_rebuttal_may_cite_its_source_span(self) -> None:
        rebuttal = Rebuttal(condition="Unless funding is found.", source_text="unless the DfT pays")
        assert rebuttal.source_text == "unless the DfT pays"

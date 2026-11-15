"""Dual-mode ASPIC+ structured argumentation provider & rationality postulate tests."""

from collections.abc import Mapping

from pydantic import ValidationError
from pydantic_ai import models
from pydantic_ai.messages import ModelMessage, ModelResponse, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
import pytest

from rdam import (
    AggregateRequest,
    FailedOutcome,
    Machine,
    ResultOutcome,
    SourceIdentity,
    StructuredInput,
    Technique,
    UnavailableOutcome,
    UnavailableReason,
    canonical_json_bytes,
)
from rdam._strict import JsonValue
from rdam.aspic import FORMALISM_ID, AspicProvider, source_identity
from rdam.aspic.output import AspicOutput
from rdam.aspic.theory import (
    AspicError,
    AspicTheoryInput,
    ContraryPairInput,
    DefeasibleRuleInput,
    StrictRuleInput,
    evaluate_aspic,
)

MODEL = "openai:gpt-5.6-sol"


@pytest.fixture(autouse=True)
def never_a_real_request():
    previous = models.ALLOW_MODEL_REQUESTS
    models.ALLOW_MODEL_REQUESTS = False
    yield
    models.ALLOW_MODEL_REQUESTS = previous


def _noop_dotenv(*_args: object, **_kwargs: object) -> None:
    return None


@pytest.fixture
def no_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr("rdam._llm.load_dotenv", _noop_dotenv)
    monkeypatch.setattr("rdam._llm._nearest_dotenv", _noop_dotenv)


@pytest.fixture
def with_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-not-used")


class TestFormalAspicEngine:
    def test_disjoint_kn_kp_and_acyclic_preferences_enforced(self) -> None:
        with pytest.raises(ValidationError, match="disjoint"):
            AspicTheoryInput(axioms=("p",), ordinary_premises=("p",))

        with pytest.raises(ValidationError, match="irreflexive and acyclic"):
            AspicTheoryInput(
                ordinary_premises=("p", "q"),
                premise_preferences=(("p", "q"), ("q", "p")),
            )

        with pytest.raises(ValidationError, match="globally unique"):
            AspicTheoryInput(
                axioms=("p",),
                strict_rules=(StrictRuleInput(id="r1", antecedents=("p",), consequent="q"),),
                defeasible_rules=(DefeasibleRuleInput(id="r1", antecedents=("p",), consequent="z"),),
            )

    def test_undercutting_always_defeats_even_preferred_defeasible_rule(self) -> None:
        theory = AspicTheoryInput(
            axioms=("bird", "penguin"),
            strict_rules=(StrictRuleInput(id="s1", antecedents=("penguin",), consequent="~d1"),),
            defeasible_rules=(DefeasibleRuleInput(id="d1", antecedents=("bird",), consequent="flies"),),
        )
        ev = evaluate_aspic(theory)
        undercuts = [att for att in ev.attacks if att.kind == "undercutting"]
        assert len(undercuts) == 1
        assert undercuts[0].succeeded_as_defeat is True
        raw_grounded = ev.extensions["grounded"]
        assert isinstance(raw_grounded, list)
        grounded_ids = {str(item) for item in raw_grounded}
        grounded_concs = {arg.conclusion for arg in ev.arguments if arg.id in grounded_ids}
        assert {"bird", "penguin", "~d1"}.issubset(grounded_concs)
        assert "flies" not in grounded_concs
        assert ev.rationality.all_satisfied is True

    def test_rebutting_and_undermining_respect_preferences_under_last_and_weakest_link(self) -> None:
        theory = AspicTheoryInput(
            ordinary_premises=("sensor_a", "sensor_b"),
            defeasible_rules=(
                DefeasibleRuleInput(id="d_a", antecedents=("sensor_a",), consequent="safe"),
                DefeasibleRuleInput(id="d_b", antecedents=("sensor_b",), consequent="~safe"),
            ),
            contraries=(ContraryPairInput(symbol="sensor_a", contrary="sensor_b", symmetric=True),),
            premise_preferences=(("sensor_a", "sensor_b"),),
            rule_preferences=(("d_a", "d_b"),),
            ordering_principle="weakest_link",
            set_comparison="elitist",
        )
        ev = evaluate_aspic(theory)
        raw_grounded = ev.extensions["grounded"]
        assert isinstance(raw_grounded, list)
        grounded_ids = {str(item) for item in raw_grounded}
        grounded_concs = {arg.conclusion for arg in ev.arguments if arg.id in grounded_ids}
        assert "sensor_b" in grounded_concs
        assert "~safe" in grounded_concs
        assert "safe" not in grounded_concs
        assert ev.rationality.all_satisfied is True

        with pytest.raises(AspicError, match="exceeds argument capacity"):
            evaluate_aspic(theory, capacity=2)


class TestDualModeProvider:
    def test_structured_input_evaluates_deterministically_without_credentials(
        self,
        no_credentials: None,
    ) -> None:
        structured: Mapping[str, JsonValue] = {
            "axioms": ["audit_passed"],
            "ordinary_premises": ["legacy_exception"],
            "strict_rules": [],
            "defeasible_rules": [
                {"id": "d1", "antecedents": ["audit_passed"], "consequent": "approve"},
                {"id": "d2", "antecedents": ["legacy_exception"], "consequent": "~approve"},
            ],
            "contraries": [],
            "premise_preferences": [],
            "rule_preferences": [["d2", "d1"]],
            "ordering_principle": "last_link",
            "set_comparison": "elitist",
        }
        request = AggregateRequest(
            source=SourceIdentity.from_bytes(b"aspic", media_type="application/json"),
            text=None,
            techniques=(Technique.ASPIC,),
            structured_inputs=(StructuredInput(technique=Technique.ASPIC, payload=structured),),
        )
        outcome = Machine([AspicProvider(model=MODEL)]).analyse(request).outcome_for(Technique.ASPIC)
        assert isinstance(outcome, ResultOutcome)
        assert outcome.result.formalism_id == FORMALISM_ID
        validated = AspicOutput.model_validate_json(canonical_json_bytes(outcome.result.payload))
        assert validated.input_origin == "supplied"
        assert validated.extraction is None
        assert validated.rationality_postulates.all_satisfied is True

    def test_invalid_structured_input_returns_typed_failed_outcome(self) -> None:
        bad: Mapping[str, JsonValue] = {"axioms": ["p"], "ordinary_premises": ["p"]}
        request = AggregateRequest(
            source=SourceIdentity.from_bytes(b"bad", media_type="application/json"),
            text=None,
            techniques=(Technique.ASPIC,),
            structured_inputs=(StructuredInput(technique=Technique.ASPIC, payload=bad),),
        )
        outcome = Machine([AspicProvider(model=MODEL)]).analyse(request).outcome_for(Technique.ASPIC)
        assert isinstance(outcome, FailedOutcome)
        assert outcome.failure.code == "invalid_aspic_theory"

    def test_text_extraction_mode_checks_credentials_and_grounds_premises_and_rules(
        self,
        no_credentials: None,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        provider = AspicProvider(model=MODEL)
        assert source_identity().hex_digest != "0" * 64
        unavail = Machine([provider]).analyse(
            AggregateRequest.for_text("Rain halts play.", (Technique.ASPIC,))
        ).outcome_for(Technique.ASPIC)
        assert isinstance(unavail, UnavailableOutcome)
        assert unavail.reason is UnavailableReason.MODEL_UNAVAILABLE

        monkeypatch.setenv("OPENAI_API_KEY", "test-key-not-used")
        source_text = (
            "The pitch is flooded. Normally a flooded pitch halts play. "
            "However, the stadium roof was closed, invalidating that presumption."
        )
        proposal = {
            "premises": [
                {
                    "symbol": "flooded_pitch",
                    "kind": "ordinary",
                    "evidence": {"quote": "The pitch is flooded.", "occurrence": 1},
                },
                {
                    "symbol": "roof_closed",
                    "kind": "axiom",
                    "evidence": {"quote": "the stadium roof was closed", "occurrence": 1},
                },
            ],
            "rules": [
                {
                    "id": "d_halt",
                    "kind": "defeasible",
                    "antecedents": ["flooded_pitch"],
                    "consequent": "halt_play",
                    "evidence": {"quote": "Normally a flooded pitch halts play.", "occurrence": 1},
                },
                {
                    "id": "s_undercut",
                    "kind": "strict",
                    "antecedents": ["roof_closed"],
                    "consequent": "~d_halt",
                    "evidence": {"quote": "invalidating that presumption.", "occurrence": 1},
                },
            ],
            "contraries": [],
            "premise_preferences": [],
            "rule_preferences": [],
            "ordering_principle": "last_link",
            "set_comparison": "elitist",
        }

        def respond(_messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
            return ModelResponse(parts=[ToolCallPart(tool_name=info.output_tools[0].name, args=proposal)])

        with provider.analyst.agent.override(model=FunctionModel(respond)):
            aggregate = Machine([provider]).analyse(
                AggregateRequest.for_text(source_text, (Technique.ASPIC,))
            )
        outcome = aggregate.outcome_for(Technique.ASPIC)
        assert isinstance(outcome, ResultOutcome)
        validated = AspicOutput.model_validate_json(canonical_json_bytes(outcome.result.payload))
        assert validated.input_origin == "extracted"
        assert validated.evidence is not None and len(validated.evidence) == 4
        assert validated.rationality_postulates.all_satisfied is True
        assert len(outcome.result.source_alignment) == 4

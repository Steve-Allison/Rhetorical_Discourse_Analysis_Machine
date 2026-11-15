"""Inference Anchoring Theory (IAT) Argument Mining provider tests."""

from pydantic import ValidationError
from pydantic_ai import models
from pydantic_ai.messages import ModelMessage, ModelResponse, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
import pytest

from rdam import (
    AggregateRequest,
    Machine,
    ResultOutcome,
    Technique,
    UnavailableOutcome,
    UnavailableReason,
    canonical_json_bytes,
)
from rdam._grounding import QuoteRef
from rdam.argument_mining import FORMALISM_ID, ArgumentMiningProvider, source_identity
from rdam.argument_mining.iat import (
    AduNodeProposal,
    ArgumentMiningError,
    EnthymemeProposal,
    IatGraphProposal,
    IatRelationProposal,
)
from rdam.argument_mining.output import ArgumentMiningOutput

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


class TestIatGraphValidation:
    def test_self_links_cycles_and_invalid_enthymeme_targets_rejected(self) -> None:
        with pytest.raises(ValidationError, match="cannot link 'adu_1' to itself"):
            IatRelationProposal(id="r_1", relation_type="inference", source_id="adu_1", target_id="adu_1")

        n1 = AduNodeProposal(
            id="adu_1", role="claim", proposition="P1", evidence=QuoteRef(quote="A", occurrence=1)
        )
        n2 = AduNodeProposal(
            id="adu_2", role="premise", proposition="P2", evidence=QuoteRef(quote="B", occurrence=1)
        )
        with pytest.raises(ValidationError, match="acyclic graph"):
            IatGraphProposal(
                adu_nodes=[n1, n2],
                relations=[
                    IatRelationProposal(id="r_1", relation_type="inference", source_id="adu_1", target_id="adu_2"),
                    IatRelationProposal(id="r_2", relation_type="inference", source_id="adu_2", target_id="adu_1"),
                ],
            )

        with pytest.raises(ValidationError, match="existing 'inference' relation"):
            IatGraphProposal(
                adu_nodes=[n1, n2],
                relations=[
                    IatRelationProposal(id="ca_1", relation_type="conflict", source_id="adu_2", target_id="adu_1"),
                ],
                enthymemes=[
                    EnthymemeProposal(
                        id="enth_1",
                        inference_relation_id="ca_1",
                        reconstructed_premise="Implicit bridge",
                    ),
                ],
            )

    def test_ungrounded_adu_quote_raises_argument_mining_error(self) -> None:
        graph = IatGraphProposal(
            adu_nodes=[
                AduNodeProposal(
                    id="adu_1",
                    role="major_claim",
                    proposition="Adopt Rust",
                    evidence=QuoteRef(quote="We should adopt Rust.", occurrence=1),
                ),
            ]
        )
        with pytest.raises(ArgumentMiningError, match="does not appear in source text"):
            graph.validate_source("We kept C++.")


class TestThroughTheMachine:
    def test_unavailable_without_credentials(self, no_credentials: None) -> None:
        provider = ArgumentMiningProvider(model=MODEL)
        assert source_identity().hex_digest != "0" * 64
        outcome = Machine([provider]).analyse(
            AggregateRequest.for_text("Adopt Rust because memory bugs drop.", (Technique.ARGUMENT_MINING,))
        ).outcome_for(Technique.ARGUMENT_MINING)
        assert isinstance(outcome, UnavailableOutcome)
        assert outcome.reason is UnavailableReason.MODEL_UNAVAILABLE

    def test_extracts_iat_nodes_ra_ca_ma_and_explicitly_ungrounded_enthymemes(
        self,
        with_credentials: None,
    ) -> None:
        source_text = (
            "We must enable strict TLS. Packet inspection compromises customer tokens. "
            "Legacy debug proxies break under strict TLS. In short, TLS protects credentials."
        )
        proposal = {
            "adu_nodes": [
                {
                    "id": "adu_1",
                    "role": "major_claim",
                    "proposition": "We must enable strict TLS",
                    "speaker": "author",
                    "evidence": {"quote": "We must enable strict TLS.", "occurrence": 1},
                },
                {
                    "id": "adu_2",
                    "role": "premise",
                    "proposition": "Packet inspection compromises customer tokens",
                    "speaker": "author",
                    "evidence": {"quote": "Packet inspection compromises customer tokens.", "occurrence": 1},
                },
                {
                    "id": "adu_3",
                    "role": "premise",
                    "proposition": "Legacy debug proxies break under strict TLS",
                    "speaker": "author",
                    "evidence": {"quote": "Legacy debug proxies break under strict TLS.", "occurrence": 1},
                },
                {
                    "id": "adu_4",
                    "role": "claim",
                    "proposition": "TLS prevents credential compromise",
                    "speaker": "author",
                    "evidence": {"quote": "In short, TLS protects credentials.", "occurrence": 1},
                },
            ],
            "relations": [
                {"id": "ra_1", "relation_type": "inference", "source_id": "adu_2", "target_id": "adu_1"},
                {"id": "ca_1", "relation_type": "conflict", "source_id": "adu_3", "target_id": "adu_1"},
                {"id": "ma_1", "relation_type": "rephrase", "source_id": "adu_4", "target_id": "adu_2"},
            ],
            "enthymemes": [
                {
                    "id": "enth_1",
                    "inference_relation_id": "ra_1",
                    "reconstructed_premise": "Strict TLS prevents cleartext packet inspection of tokens.",
                }
            ],
        }

        def respond(_messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
            return ModelResponse(parts=[ToolCallPart(tool_name=info.output_tools[0].name, args=proposal)])

        provider = ArgumentMiningProvider(model=MODEL)
        with provider.analyst.agent.override(model=FunctionModel(respond)):
            aggregate = Machine([provider]).analyse(
                AggregateRequest.for_text(source_text, (Technique.ARGUMENT_MINING,))
            )
        outcome = aggregate.outcome_for(Technique.ARGUMENT_MINING)
        assert isinstance(outcome, ResultOutcome)
        assert outcome.result.formalism_id == FORMALISM_ID
        validated = ArgumentMiningOutput.model_validate_json(canonical_json_bytes(outcome.result.payload))
        assert validated.major_claim_ids == ("adu_1",)
        assert validated.node_count == 4
        assert validated.relation_count == 3
        assert len(validated.enthymemes) == 1
        assert validated.enthymemes[0].grounded is False
        assert len(outcome.result.source_alignment) == 4

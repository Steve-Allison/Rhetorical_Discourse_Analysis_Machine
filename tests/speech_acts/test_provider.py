"""Speech Act & Hamblin Commitment Store provider tests."""

from pathlib import Path

from pydantic import ValidationError
from pydantic_ai import models
from pydantic_ai.messages import ModelMessage, ModelResponse, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
import pytest

from rdam import (
    AggregateRequest,
    Machine,
    ProviderError,
    ProviderRequest,
    ResultOutcome,
    SourceIdentity,
    Technique,
    UnavailableOutcome,
    UnavailableReason,
    canonical_json_bytes,
)
from rdam._grounding import QuoteRef
from rdam.speech_acts import FORMALISM_ID, SpeechActsProvider, source_identity
from rdam.speech_acts.acts import SpeechActError, SpeechActItemProposal, SpeechActProposal
from rdam.speech_acts.commitments import replay_commitments
from rdam.speech_acts.output import SpeechActsOutput

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


class TestTaxonomyAndCommitments:
    def test_incompatible_searle_and_iso_function_rejected(self) -> None:
        with pytest.raises(ValidationError, match="incompatible with searle_class"):
            SpeechActItemProposal(
                act_id="sa_1",
                speaker="Alice",
                searle_class="directive",
                iso_communicative_function="inform",
                propositional_content="Deploy today",
                commitment_operation="none",
                evidence=QuoteRef(quote="Deploy today.", occurrence=1),
            )

    def test_target_proposition_invariants_enforced(self) -> None:
        with pytest.raises(ValidationError, match="requires target_proposition"):
            SpeechActItemProposal(
                act_id="sa_1",
                speaker="Alice",
                searle_class="assertive",
                iso_communicative_function="correction",
                propositional_content="Retract earlier claim",
                commitment_operation="retract",
                target_proposition=None,
                evidence=QuoteRef(quote="I withdraw that.", occurrence=1),
            )
        with pytest.raises(ValidationError, match="target_proposition must be null"):
            SpeechActItemProposal(
                act_id="sa_2",
                speaker="Alice",
                searle_class="assertive",
                iso_communicative_function="inform",
                propositional_content="The release is ready",
                commitment_operation="assert",
                target_proposition="The release is ready",
                evidence=QuoteRef(quote="The release is ready.", occurrence=1),
            )

    def test_duplicate_ids_and_ungrounded_quotes_rejected(self) -> None:
        item = SpeechActItemProposal(
            act_id="sa_1",
            speaker="Alice",
            searle_class="assertive",
            iso_communicative_function="inform",
            propositional_content="Tests pass",
            commitment_operation="assert",
            evidence=QuoteRef(quote="Tests pass.", occurrence=1),
        )
        with pytest.raises(ValidationError, match="Duplicate speech-act act_id"):
            SpeechActProposal(acts=[item, item])

        proposal = SpeechActProposal(acts=[item])
        with pytest.raises(SpeechActError, match="does not appear in source text"):
            proposal.validate_source("Build failed.")

    def test_hamblin_commitment_replay_tracks_assertions_retractions_challenges_and_conflicts(self) -> None:
        acts = (
            SpeechActItemProposal(
                act_id="sa_1",
                speaker="Alice",
                searle_class="assertive",
                iso_communicative_function="inform",
                propositional_content="The cache is warm",
                commitment_operation="assert",
                evidence=QuoteRef(quote="a", occurrence=1),
            ),
            SpeechActItemProposal(
                act_id="sa_2",
                speaker="Bob",
                searle_class="directive",
                iso_communicative_function="question",
                propositional_content="Why is the cache warm",
                commitment_operation="challenge",
                target_proposition="The cache is warm",
                evidence=QuoteRef(quote="b", occurrence=1),
            ),
            SpeechActItemProposal(
                act_id="sa_3",
                speaker="Alice",
                searle_class="assertive",
                iso_communicative_function="disconfirm",
                propositional_content="The cache is not warm",
                commitment_operation="assert",
                evidence=QuoteRef(quote="c", occurrence=1),
            ),
            SpeechActItemProposal(
                act_id="sa_4",
                speaker="Alice",
                searle_class="assertive",
                iso_communicative_function="correction",
                propositional_content="Withdrawing initial claim",
                commitment_operation="retract",
                target_proposition="The cache is warm",
                evidence=QuoteRef(quote="d", occurrence=1),
            ),
        )
        summary = replay_commitments(acts)
        by_speaker = {s.speaker: s for s in summary.speakers}
        assert by_speaker["Alice"].active_commitments == ("The cache is not warm",)
        assert by_speaker["Alice"].retracted_commitments == ("The cache is warm",)
        assert by_speaker["Bob"].challenges_raised == ("The cache is warm",)
        assert len(summary.conflicts) == 1
        assert summary.conflicts[0].speaker == "Alice"
        assert summary.conflicts[0].earlier_act_id == "sa_1"
        assert summary.conflicts[0].later_act_id == "sa_3"


class TestThroughTheMachine:
    def test_unavailable_without_credentials_and_source_identity_stable(self, no_credentials: None) -> None:
        provider = SpeechActsProvider(model=MODEL)
        assert source_identity().hex_digest != "0" * 64
        outcome = Machine([provider]).analyse(
            AggregateRequest.for_text("We promise to ship on Friday.", (Technique.SPEECH_ACTS,))
        ).outcome_for(Technique.SPEECH_ACTS)
        assert isinstance(outcome, UnavailableOutcome)
        assert outcome.reason is UnavailableReason.MODEL_UNAVAILABLE

    def test_undeclared_formalism_is_rejected(self, with_credentials: None) -> None:
        provider = SpeechActsProvider(model=MODEL)
        with pytest.raises(ProviderError) as caught:
            provider.analyse(
                ProviderRequest(
                    source=SourceIdentity.from_text("Ship today."),
                    text="Ship today.",
                    structured_input=None,
                    formalism_id="wrong_formalism",
                )
            )
        assert caught.value.failure.code == "formalism_not_declared"

    def test_doclang_dialogue_extracts_speech_acts_and_commitment_store(
        self,
        tmp_path: Path,
        with_credentials: None,
    ) -> None:
        doc = tmp_path / "dialogue.dclg"
        doc.write_text(
            '<doclang version="0.9">'
            "<track>"
            '<bdiv/><minutes value="0"/><seconds value="1"/><voice>Protagonist</voice>'
            "The migration is safe."
            '<bdiv/><minutes value="0"/><seconds value="4"/><voice>Reviewer</voice>'
            "Can you prove the rollback works?"
            '<bdiv/><minutes value="0"/><seconds value="7"/><voice>Protagonist</voice>'
            "The migration is not safe yet."
            "</track></doclang>",
            encoding="utf-8",
        )
        raw = {
            "acts": [
                {
                    "act_id": "act_1",
                    "speaker": "Protagonist",
                    "searle_class": "assertive",
                    "iso_communicative_function": "inform",
                    "propositional_content": "The migration is safe",
                    "commitment_operation": "assert",
                    "target_proposition": None,
                    "evidence": {"quote": "The migration is safe.", "occurrence": 1},
                },
                {
                    "act_id": "act_2",
                    "speaker": "Reviewer",
                    "searle_class": "directive",
                    "iso_communicative_function": "question",
                    "propositional_content": "Proof that rollback works",
                    "commitment_operation": "challenge",
                    "target_proposition": "The migration is safe",
                    "evidence": {"quote": "Can you prove the rollback works?", "occurrence": 1},
                },
                {
                    "act_id": "act_3",
                    "speaker": "Protagonist",
                    "searle_class": "assertive",
                    "iso_communicative_function": "disconfirm",
                    "propositional_content": "The migration is not safe",
                    "commitment_operation": "assert",
                    "target_proposition": None,
                    "evidence": {"quote": "The migration is not safe yet.", "occurrence": 1},
                },
            ]
        }

        def respond(_messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
            return ModelResponse(parts=[ToolCallPart(tool_name=info.output_tools[0].name, args=raw)])

        provider = SpeechActsProvider(model=MODEL)
        with provider.analyst.agent.override(model=FunctionModel(respond)):
            aggregate = Machine([provider]).analyse(
                AggregateRequest.for_source(doc, (Technique.SPEECH_ACTS,))
            )
        outcome = aggregate.outcome_for(Technique.SPEECH_ACTS)
        assert isinstance(outcome, ResultOutcome)
        assert outcome.result.formalism_id == FORMALISM_ID
        validated = SpeechActsOutput.model_validate_json(canonical_json_bytes(outcome.result.payload))
        assert validated.act_count == 3
        assert len(validated.conflicts) == 1
        assert len(outcome.result.source_alignment) == 3
        assert len(aggregate.xpath_alignment) == 3

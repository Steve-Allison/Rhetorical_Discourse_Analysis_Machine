"""Deterministic Centering Theory & Entity Grid provider tests."""

from pathlib import Path

import pytest

from rdam import (
    AggregateRequest,
    AvailableCapability,
    Machine,
    ProviderError,
    ProviderRequest,
    ResultOutcome,
    SourceIdentity,
    Technique,
    canonical_json_bytes,
)
from rdam.centering import CONTRACT_VERSION, FORMALISM_ID, PROVIDER_ID, CenteringProvider, source_identity
from rdam.centering.grid import analyse_centering
from rdam.centering.output import CenteringOutput


class TestDeclaration:
    def test_declaration_is_available_and_cache_eligible(self) -> None:
        provider = CenteringProvider()
        declaration = provider.declaration
        assert declaration.technique is Technique.CENTERING
        assert declaration.capability == AvailableCapability(
            provider_id=PROVIDER_ID,
            contract_version=CONTRACT_VERSION,
        )
        assert declaration.requires_structured_input is False
        assert declaration.configuration.cache_eligible is True
        first = source_identity()
        assert source_identity() is first
        assert first.hex_digest != "0" * 64


class TestEntityGridAndTransitions:
    def test_coherent_narrative_exhibits_continue_and_pronoun_resolution(self) -> None:
        coherent = (
            "Elena designed the compiler. "
            "She tested the compiler in production. "
            "She documented the results for Marcus."
        )
        analysis = analyse_centering(coherent)
        assert len(analysis.utterances) == 3
        assert analysis.utterances[0].transition == "establishment"
        assert analysis.utterances[1].cb is not None
        assert analysis.utterances[1].transition in {"continue", "smooth_shift", "retain"}
        assert any(
            mention.is_pronoun
            for entity in analysis.entities
            for mention in entity.mentions
        )

        disjoint = (
            "Elena designed the compiler. "
            "Thunderstorms delayed regional flights. "
            "Pottery glazes require kiln calibration."
        )
        disjoint_analysis = analyse_centering(disjoint)
        assert disjoint_analysis.transition_counts["zero_cb"] >= 1
        assert analysis.local_coherence_score > disjoint_analysis.local_coherence_score

    def test_retain_and_shift_transitions_and_role_precedence(self) -> None:
        text = (
            "Alice praised Bob at the summit. "
            "Charlie congratulated Alice after the keynote. "
            "Charlie led the workshop."
        )
        analysis = analyse_centering(text)
        assert len(analysis.utterances) == 3
        transitions = [u.transition for u in analysis.utterances]
        assert transitions[0] == "establishment"
        # Utterance 2 realizes Alice in object position while Charlie is subject (Cp != Cb -> retain)
        assert transitions[1] == "retain"
        # Utterance 3 shifts backward-looking center to Charlie in subject position (smooth_shift)
        assert transitions[2] == "smooth_shift"
        for roles in analysis.entity_grid.values():
            assert len(roles) == 3
            assert set(roles).issubset({"S", "O", "X", "-"})


class TestThroughTheMachine:
    def test_undeclared_formalism_and_missing_text_raise_typed_errors(self) -> None:
        provider = CenteringProvider()
        with pytest.raises(ProviderError) as bad_formalism:
            provider.analyse(
                ProviderRequest(
                    source=SourceIdentity.from_text("The cat sat."),
                    text="The cat sat.",
                    structured_input=None,
                    formalism_id="not_centering",
                )
            )
        assert bad_formalism.value.failure.code == "formalism_not_declared"

        with pytest.raises(ProviderError) as missing_text:
            provider.analyse(
                ProviderRequest(
                    source=SourceIdentity.from_bytes(b"x"),
                    text=None,
                    structured_input=None,
                )
            )
        assert missing_text.value.failure.code == "text_required"

    def test_doclang_stream_aligns_prose_tables_and_speaker_turns(self, tmp_path: Path) -> None:
        doc = tmp_path / "centering.dclg"
        doc.write_text(
            '<doclang version="0.9">'
            "<text>Postgres enforces transactional DDL.</text>"
            "<table><ched/>System<ched/>Feature<nl/><fcel/>Postgres<fcel/>Transactional DDL<nl/></table>"
            '<track><bdiv/><minutes value="0"/><seconds value="2"/>'
            "<voice>Dana</voice>It prevents partial schema drift.</track>"
            "</doclang>",
            encoding="utf-8",
        )
        aggregate = Machine([CenteringProvider()]).analyse(
            AggregateRequest.for_source(doc, (Technique.CENTERING,))
        )
        outcome = aggregate.outcome_for(Technique.CENTERING)
        assert isinstance(outcome, ResultOutcome)
        assert outcome.result.formalism_id == FORMALISM_ID
        validated = CenteringOutput.model_validate_json(canonical_json_bytes(outcome.result.payload))
        assert validated.utterance_count >= 3
        assert validated.entity_count >= 1
        assert outcome.result.source_alignment
        xpaths = {entry.xpath for entry in aggregate.xpath_alignment}
        assert "/d:doclang/d:text[1]" in xpaths
        assert any("/d:table[1]/" in xp for xp in xpaths)
        assert any("/d:track[1]/" in xp for xp in xpaths)

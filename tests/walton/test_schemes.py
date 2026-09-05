"""The Walton scheme table and its validator, checked exhaustively over every scheme."""

import pytest
from pydantic import ValidationError

from rdam.walton import (
    SCHEMES,
    SCHEME_SET_ID,
    CriticalQuestion,
    CriticalQuestionStatus,
    Scheme,
    SchemeError,
    SchemeId,
    SchemeInstance,
    WaltonAnalysis,
)

EXPERT = {
    "scheme_id": "expert_opinion",
    "conclusion": "The bridge is unsafe.",
    "premises": {
        "source": "Dr Okonkwo",
        "domain": "structural engineering",
        "assertion": "the bridge cannot carry its rated load",
    },
    "critical_questions": [
        {"index": index, "status": "open"}
        for index in range(len(SCHEMES[SchemeId.EXPERT_OPINION].critical_questions))
    ],
}


def _premises(scheme_id: SchemeId) -> dict[str, str]:
    """Every premise role the scheme names, filled once."""

    return {role: f"content for {role}" for role in SCHEMES[scheme_id].premise_roles}


def _filled(scheme_id: SchemeId) -> dict[str, object]:
    """A minimally well-formed instance of any scheme: every role filled once."""

    return {
        "scheme_id": scheme_id.value,
        "conclusion": "some conclusion",
        "premises": _premises(scheme_id),
        "critical_questions": _questions(scheme_id),
    }


def _question_source(scheme_id: SchemeId, addressed: tuple[int, ...]) -> str:
    """An authored passage taking up exactly the selected catalogue questions."""

    return "\n".join(f"The speaker asks: {SCHEMES[scheme_id].critical_questions[index]}" for index in addressed)


def _questions(scheme_id: SchemeId, addressed: tuple[int, ...] = ()) -> list[dict[str, object]]:
    source = _question_source(scheme_id, addressed)
    questions: list[dict[str, object]] = []
    for index, question in enumerate(SCHEMES[scheme_id].critical_questions):
        if index in addressed:
            quote = f"The speaker asks: {question}"
            start = source.index(quote)
            questions.append({
                "index": index,
                "status": "addressed",
                "note": "The passage explicitly takes up this catalogue question.",
                "evidence": [{"start": start, "end": start + len(quote), "text": quote}],
            })
        else:
            questions.append({"index": index, "status": "open"})
    return questions


class TestTheSchemeTable:
    @pytest.mark.parametrize(
        ("name", "roles", "questions"),
        (
            ("", ("finding",), ("A question?",)),
            ("Sign", (), ("A question?",)),
            ("Sign", ("finding", "finding"), ("A question?",)),
            ("Sign", ("finding",), ()),
        ),
    )
    def test_direct_scheme_construction_enforces_catalogue_invariants(
        self,
        name: str,
        roles: tuple[str, ...],
        questions: tuple[str, ...],
    ) -> None:
        with pytest.raises(SchemeError):
            Scheme(
                scheme_id=SchemeId.SIGN,
                name=name,
                premise_roles=roles,
                critical_questions=questions,
            )

    def test_every_declared_scheme_is_in_the_table(self) -> None:
        assert set(SCHEMES) == set(SchemeId), "every SchemeId must have a Scheme"

    @pytest.mark.parametrize("scheme_id", list(SchemeId))
    def test_every_scheme_has_roles_a_name_and_critical_questions(self, scheme_id: SchemeId) -> None:
        scheme = SCHEMES[scheme_id]
        assert scheme.scheme_id is scheme_id
        assert scheme.name.strip()
        assert scheme.premise_roles, "a scheme without premise roles cannot be instanced"
        assert len(set(scheme.premise_roles)) == len(scheme.premise_roles), "roles must be unique"
        assert scheme.critical_questions, "a Walton scheme without critical questions is not a Walton scheme"
        assert all(question.strip().endswith("?") for question in scheme.critical_questions)

    @pytest.mark.parametrize("scheme_id", list(SchemeId))
    def test_every_scheme_accepts_a_fully_filled_instance(self, scheme_id: SchemeId) -> None:
        instance = SchemeInstance.model_validate(_filled(scheme_id))
        assert instance.scheme.scheme_id is scheme_id


class TestPremiseRoles:
    @pytest.mark.parametrize("scheme_id", list(SchemeId))
    def test_a_missing_role_is_refused_for_every_scheme(self, scheme_id: SchemeId) -> None:
        premises = _premises(scheme_id)
        dropped = SCHEMES[scheme_id].premise_roles[0]
        del premises[dropped]
        with pytest.raises(ValidationError) as caught:
            SchemeInstance.model_validate({**_filled(scheme_id), "premises": premises})
        assert dropped in str(caught.value)

    @pytest.mark.parametrize("scheme_id", list(SchemeId))
    def test_an_unknown_role_is_refused_for_every_scheme(self, scheme_id: SchemeId) -> None:
        premises = {**_premises(scheme_id), "not_a_role": "x"}
        with pytest.raises(ValidationError) as caught:
            SchemeInstance.model_validate({**_filled(scheme_id), "premises": premises})
        assert "not_a_role" in str(caught.value)

    @pytest.mark.parametrize("scheme_id", list(SchemeId))
    def test_an_empty_premise_is_refused_for_every_scheme(self, scheme_id: SchemeId) -> None:
        first_role = SCHEMES[scheme_id].premise_roles[0]
        with pytest.raises(ValidationError):
            SchemeInstance.model_validate(
                {**_filled(scheme_id), "premises": {**_premises(scheme_id), first_role: "  "}}
            )

    def test_an_unknown_scheme_id_is_refused(self) -> None:
        with pytest.raises(ValidationError):
            SchemeInstance.model_validate({**EXPERT, "scheme_id": "argument_from_vibes"})


class TestCriticalQuestions:
    def test_unreported_questions_are_rejected_not_defaulted_open(self) -> None:
        with pytest.raises(ValidationError) as caught:
            SchemeInstance.model_validate({key: value for key, value in EXPERT.items() if key != "critical_questions"})
        assert caught.value.errors()[0]["loc"] == ("critical_questions",)
        assert caught.value.errors()[0]["type"] == "missing"

    def test_an_addressed_question_preserves_explicitly_open_remainder(self) -> None:
        instance = SchemeInstance.model_validate(
            {**EXPERT, "critical_questions": _questions(SchemeId.EXPERT_OPINION, (0,))}
        )
        WaltonAnalysis(instances=[instance]).validate_source(_question_source(SchemeId.EXPERT_OPINION, (0,)))
        total = len(SCHEMES[SchemeId.EXPERT_OPINION].critical_questions)
        assert len(instance.open_questions) == total - 1

    @pytest.mark.parametrize("scheme_id", list(SchemeId))
    def test_one_addressed_question_leaves_the_exact_complement_open(self, scheme_id: SchemeId) -> None:
        instance = SchemeInstance.model_validate(
            {
                **_filled(scheme_id),
                "critical_questions": _questions(scheme_id, (0,)),
            }
        )
        scheme = SCHEMES[scheme_id]
        assert instance.open_questions == scheme.critical_questions[1:]
        WaltonAnalysis(instances=[instance]).validate_source(_question_source(scheme_id, (0,)))

    def test_an_addressed_question_must_say_how(self) -> None:
        with pytest.raises(ValidationError, match="must say how"):
            CriticalQuestion.model_validate({**_questions(SchemeId.EXPERT_OPINION, (0,))[0], "note": None})

    def test_an_open_question_needs_no_note(self) -> None:
        assert CriticalQuestion(index=0, status=CriticalQuestionStatus.OPEN).note is None

    def test_an_open_question_refuses_a_provider_authored_note(self) -> None:
        with pytest.raises(ValidationError) as caught:
            CriticalQuestion(
                index=0,
                status=CriticalQuestionStatus.OPEN,
                note="The source should have answered yes.",
            )
        assert "open question cannot carry note or evidence" in str(caught.value)

    def test_an_out_of_range_question_index_is_refused(self) -> None:
        count = len(SCHEMES[SchemeId.EXPERT_OPINION].critical_questions)
        with pytest.raises(ValidationError) as caught:
            SchemeInstance.model_validate({**EXPERT, "critical_questions": [{"index": count, "status": "open"}]})
        assert "does not exist" in str(caught.value)

    def test_a_negative_question_index_is_refused(self) -> None:
        with pytest.raises(ValidationError):
            SchemeInstance.model_validate({**EXPERT, "critical_questions": [{"index": -1, "status": "open"}]})

    def test_a_repeated_question_is_refused(self) -> None:
        with pytest.raises(ValidationError) as caught:
            SchemeInstance.model_validate(
                {
                    **EXPERT,
                    "critical_questions": [
                        {"index": 1, "status": "open"},
                        {"index": 1, "status": "open"},
                    ],
                }
            )
        assert "twice" in str(caught.value)

    @pytest.mark.parametrize("scheme_id", list(SchemeId))
    def test_marking_every_question_addressed_leaves_none_open(self, scheme_id: SchemeId) -> None:
        scheme = SCHEMES[scheme_id]
        addressed = tuple(range(len(scheme.critical_questions)))
        instance = SchemeInstance.model_validate(
            {
                **_filled(scheme_id),
                "critical_questions": _questions(scheme_id, addressed),
            }
        )
        assert instance.open_questions == ()
        WaltonAnalysis(instances=[instance]).validate_source(_question_source(scheme_id, addressed))


class TestPayload:
    def test_the_payload_pairs_each_reported_question_with_its_text(self) -> None:
        instance = SchemeInstance.model_validate(
            {**EXPERT, "critical_questions": _questions(SchemeId.EXPERT_OPINION, (1,))}
        )
        payload = instance.to_payload()
        reported = payload["critical_questions"]
        assert isinstance(reported, list)
        entry = reported[1]
        assert isinstance(entry, dict)
        assert entry["question"] == SCHEMES[SchemeId.EXPERT_OPINION].critical_questions[1]
        assert entry["status"] == "addressed"
        assert payload["scheme_name"] == "Argument from Expert Opinion"

    def test_open_questions_are_reported_never_answered(self) -> None:
        payload = SchemeInstance.model_validate(EXPERT).to_payload()
        assert payload["open_question_count"] == len(SCHEMES[SchemeId.EXPERT_OPINION].critical_questions)
        assert isinstance(payload["open_questions"], list)

    def test_an_empty_analysis_forces_no_scheme_onto_the_passage(self) -> None:
        payload = WaltonAnalysis().to_payload()
        assert payload["instances"] == []
        assert payload["instance_count"] == 0
        assert payload["total_open_questions"] == 0

    def test_the_analysis_names_the_scheme_set_it_used(self) -> None:
        assert WaltonAnalysis().to_payload()["scheme_set"] == SCHEME_SET_ID

    def test_open_questions_total_across_instances(self) -> None:
        analysis = WaltonAnalysis(
            instances=[
                SchemeInstance.model_validate(EXPERT),
                SchemeInstance.model_validate(_filled(SchemeId.SIGN)),
            ]
        )
        expected = len(SCHEMES[SchemeId.EXPERT_OPINION].critical_questions) + len(SCHEMES[SchemeId.SIGN].critical_questions)
        assert analysis.to_payload()["total_open_questions"] == expected

"""Observed terms retain their scope, source spelling and mapping failures."""

import pytest

from rdam.ontology import ObservedVocabularyAlignment, observed_vocabulary_alignment, walton_profile_alignment
from rdam.rst.ontology import OntologyAdapter, load_ontology_lock
from rdam.rst.contracts.enums import RelationSchemeEnum
from rdam.walton.schemes import SCHEMES
from rdam.pdtb.relations import RelationType


def test_pdtb_relation_types_cover_the_native_inventory() -> None:
    native = tuple(item.value for item in RelationType)
    alignment = observed_vocabulary_alignment("coe:artifact/narrative/pdtb3_relation_types", native)
    assert not alignment.unmapped
    assert tuple(item.native_value for item in alignment.mappings) == native


def test_sdrt_preserves_unknown_labels_without_guessing_synonyms() -> None:
    alignment = observed_vocabulary_alignment(
        "coe:artifact/narrative/sdrt_vocabulary",
        ("Narration", "narration", "Result", "Consequence", "cause", " Narration", "Narration"),
    )
    assert tuple(item.native_value for item in alignment.mappings) == (
        "Narration", "narration", "Result", "Consequence",
    )
    assert alignment.mappings[0].concept_id == alignment.mappings[1].concept_id
    assert alignment.mappings[2].concept_id != alignment.mappings[3].concept_id
    assert tuple(item.native_value for item in alignment.unmapped) == ("cause", " Narration")
    assert ObservedVocabularyAlignment.model_validate_json(alignment.model_dump_json()) == alignment


def test_gum_fine_inventory_has_scoped_central_identity() -> None:
    native = tuple(load_ontology_lock().gum_fine_to_coarse)
    alignment = observed_vocabulary_alignment("coe:artifact/narrative/gum_erst_relations", native)
    assert not alignment.unmapped
    assert tuple(item.native_value for item in alignment.mappings) == native
    mapped = {item.native_value: item.concept_id for item in alignment.mappings}
    assert mapped["causal-cause"] != mapped["causal-result"]
    assert mapped["adversative-concession"] != mapped["adversative-contrast"]


def test_rst_directional_labels_and_negative_attribution_remain_distinct() -> None:
    raw = ("cause", "result", "consequence-n-e", "consequence-s", "attribution-n", "attribution")
    alignment = OntologyAdapter.central_alignment(raw, RelationSchemeEnum.RST_DT_FINE)
    assert not alignment.unmapped
    assert len({item.concept_id for item in alignment.mappings}) == len(raw)
    assert tuple(item.native_value for item in alignment.mappings) == raw


def test_coarse_crosswalks_cover_each_trained_corpus_inventory() -> None:
    lock = load_ontology_lock()
    for raw, scheme in (
        (tuple(lock.coarse_concepts), RelationSchemeEnum.RST_DT_COARSE_18),
        (tuple(item.label for item in lock.dmrst_gum_model_27.values()), RelationSchemeEnum.GUM_ERST_COARSE),
    ):
        alignment = OntologyAdapter.central_alignment(raw, scheme)
        assert not alignment.unmapped
        assert {item.native_value for item in alignment.mappings} == set(raw)


def test_walton_accounts_for_every_native_slot_without_inventing_equivalence() -> None:
    alignment = walton_profile_alignment(tuple(SCHEMES))
    expected = {
        key
        for scheme_id, scheme in SCHEMES.items()
        for key in (
            *(f"{scheme_id}/premise/{role}" for role in scheme.premise_roles),
            *(f"{scheme_id}/question/{index}" for index in range(len(scheme.critical_questions))),
        )
    }
    mapped = {item.native_value: item for item in alignment.mappings}
    unmapped = {item.native_value for item in alignment.unmapped}
    assert set(mapped).isdisjoint(unmapped)
    assert set(mapped) | unmapped == expected
    assert "/scheme_variable/" in mapped["expert_opinion/premise/source"].concept_id
    assert "/scheme_variable/" in mapped["sign/premise/indicated"].concept_id
    assert mapped["expert_opinion/question/3"].concept_id.endswith("/trustworthiness")
    assert mapped["analogy/question/1"].relationship == "broader"
    assert mapped["cause_to_effect/question/0"].concept_id.endswith("/cause_to_effect/strength")
    assert "cause_to_effect/question/3" in unmapped
    assert "example/question/4" in unmapped
    assert all(item.reason == "equivalence_not_established" and item.explanation for item in alignment.unmapped)
    assert alignment.consumer_profile_identity is not None
    assert ObservedVocabularyAlignment.model_validate_json(alignment.model_dump_json()) == alignment


def test_walton_observed_profile_excludes_unused_schemes() -> None:
    alignment = walton_profile_alignment(("expert_opinion",))
    assert all(value.startswith("expert_opinion/") for value in alignment.native_values)
    assert not walton_profile_alignment(()).native_values


def test_walton_non_equivalence_explanation_cannot_be_replaced_or_removed() -> None:
    alignment = walton_profile_alignment(("cause_to_effect",))
    assert len(alignment.unmapped) == 1
    for explanation in (None, "This question has an exact canonical equivalent."):
        payload = alignment.model_dump()
        payload["unmapped"][0]["explanation"] = explanation
        with pytest.raises(ValueError):
            ObservedVocabularyAlignment.model_validate(payload)


@pytest.mark.parametrize("mutation", ("missing", "invented", "source", "duplicate"))
def test_observed_resolution_rejects_forgery(mutation: str) -> None:
    alignment = observed_vocabulary_alignment("coe:artifact/narrative/sdrt_vocabulary", ("Narration", "unknown"))
    payload = alignment.model_dump()
    match mutation:
        case "missing":
            payload["unmapped"] = ()
        case "invented":
            payload["mappings"][0]["concept_id"] = "coe:concept/invented"
        case "source":
            payload["source"] = "invented"
        case "duplicate":
            payload["native_values"] = ("Narration", "Narration", "unknown")
        case _:
            raise ValueError(f"Unknown mutation: {mutation}")
    with pytest.raises(ValueError):
        ObservedVocabularyAlignment.model_validate(payload)

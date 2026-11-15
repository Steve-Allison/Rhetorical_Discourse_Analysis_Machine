"""Observed terms resolve via explicit v5.0.0 lookup tables and preserve unmapped labels."""

import pytest

from rdam.ontology import (
    ObservedVocabularyAlignment,
    lookup_curie_for_native,
    lookup_native_for_curie,
    observed_vocabulary_alignment,
    walton_profile_alignment,
)
from rdam.pdtb.relations import PdtbSense
from rdam.rst.contracts.enums import RelationSchemeEnum
from rdam.rst.ontology import OntologyAdapter, load_ontology_lock
from rdam.walton.schemes import SCHEMES


def test_pdtb_senses_resolve_via_explicit_lookup_table() -> None:
    native = tuple(item.value for item in PdtbSense)
    alignment = observed_vocabulary_alignment("pdtb3_senses", native)
    mapped = {item.native_value: item for item in alignment.mappings}
    unmapped = {item.native_value for item in alignment.unmapped}
    assert set(mapped).isdisjoint(unmapped)
    assert set(mapped) | unmapped == set(native)
    assert mapped["Contingency.Cause.Result"].concept_id == "coe:C06123"
    assert mapped["Comparison.Contrast"].concept_id == "coe:C06126"
    direct = lookup_curie_for_native("pdtb3_senses", "Comparison.Contrast")
    assert direct is not None and direct.concept_id == "coe:C06126"
    assert "Comparison.Contrast" in lookup_native_for_curie("pdtb3_senses", "coe:C06126")


def test_sdrt_preserves_unknown_labels_without_guessing_synonyms() -> None:
    alignment = observed_vocabulary_alignment(
        "sdrt_relations",
        ("Narration", "narration", "Result", "Consequence", "cause", " Narration", "Narration"),
    )
    assert tuple(item.native_value for item in alignment.mappings) == (
        "Narration",
        "narration",
        "Result",
        "Consequence",
    )
    assert alignment.mappings[0].concept_id == alignment.mappings[1].concept_id == "coe:C06121"
    assert alignment.mappings[2].concept_id == "coe:C06123"
    assert alignment.mappings[3].concept_id == "coe:C06125"
    assert tuple(item.native_value for item in alignment.unmapped) == ("cause", " Narration")
    assert ObservedVocabularyAlignment.model_validate_json(alignment.model_dump_json()) == alignment


def test_gum_fine_inventory_accounts_for_mapped_and_corpus_specific_labels() -> None:
    native = tuple(load_ontology_lock().gum_fine_to_coarse)
    alignment = observed_vocabulary_alignment("gum_erst_relations", native)
    mapped = {item.native_value: item.concept_id for item in alignment.mappings}
    unmapped = {item.native_value for item in alignment.unmapped}
    assert set(mapped).isdisjoint(unmapped)
    assert set(mapped) | unmapped == set(native)
    assert mapped["causal-cause"] == "coe:C06123"
    assert mapped["adversative-concession"] == "coe:C06127"
    assert mapped["adversative-contrast"] == "coe:C06126"
    assert "attribution-positive" in unmapped


def test_rst_dt_labels_and_negative_attribution_resolve_via_lookup_table() -> None:
    raw = ("cause", "result", "consequence-n-e", "consequence-s", "attribution-n", "attribution")
    alignment = OntologyAdapter.central_alignment(raw, RelationSchemeEnum.RST_DT_FINE)
    mapped = {item.native_value: item.concept_id for item in alignment.mappings}
    unmapped = {item.native_value for item in alignment.unmapped}
    assert mapped == {
        "cause": "coe:C06123",
        "result": "coe:C06123",
        "consequence-n-e": "coe:C06123",
        "consequence-s": "coe:C06123",
    }
    assert unmapped == {"attribution-n", "attribution"}


def test_coarse_crosswalks_account_for_each_trained_corpus_inventory() -> None:
    lock = load_ontology_lock()
    for raw, scheme in (
        (tuple(lock.coarse_concepts), RelationSchemeEnum.RST_DT_COARSE_18),
        (tuple(item.label for item in lock.dmrst_gum_model_27.values()), RelationSchemeEnum.GUM_ERST_COARSE),
    ):
        alignment = OntologyAdapter.central_alignment(raw, scheme)
        accounted = {item.native_value for item in alignment.mappings} | {
            item.native_value for item in alignment.unmapped
        }
        assert accounted == set(raw)
        assert alignment.mappings


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
    assert "expert_opinion/premise/source" in unmapped
    assert "sign/premise/indicated" in unmapped
    assert mapped["expert_opinion/question/3"].concept_id == "coe:C06112"
    assert mapped["analogy/question/0"].concept_id == "coe:C06109"
    assert mapped["analogy/question/0"].relationship == "broader"
    assert mapped["cause_to_effect/question/0"].concept_id == "coe:C06108"
    assert mapped["cause_to_effect/question/3"].concept_id == "coe:C06116"
    assert "cause_to_effect/question/1" in unmapped
    assert "analogy/question/1" in unmapped
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
    assert any(item.native_value == "cause_to_effect/question/1" for item in alignment.unmapped)
    for explanation in (None, "This question has an exact canonical equivalent."):
        payload = alignment.model_dump()
        payload["unmapped"][0]["explanation"] = explanation
        with pytest.raises(ValueError):
            ObservedVocabularyAlignment.model_validate(payload)


@pytest.mark.parametrize("mutation", ("missing", "invented", "source", "duplicate"))
def test_observed_resolution_rejects_forgery(mutation: str) -> None:
    alignment = observed_vocabulary_alignment("sdrt_relations", ("Narration", "unknown"))
    payload = alignment.model_dump()
    match mutation:
        case "missing":
            payload["unmapped"] = ()
        case "invented":
            payload["mappings"][0]["concept_id"] = "coe:C99999"
        case "source":
            payload["source"] = "invented"
        case "duplicate":
            payload["native_values"] = ("Narration", "Narration", "unknown")
        case _:
            raise ValueError(f"Unknown mutation: {mutation}")
    with pytest.raises(ValueError):
        ObservedVocabularyAlignment.model_validate(payload)

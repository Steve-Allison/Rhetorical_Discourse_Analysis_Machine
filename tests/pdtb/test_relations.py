"""Causal tests for PDTB-3 native relation invariants."""

from pydantic import ValidationError
import pytest

from rdam.pdtb.relations import (
    PDTB3_SENSES,
    PdtbAnalysis,
    PdtbArgument,
    PdtbRelation,
    PdtbSense,
    RelationError,
    RelationType,
    TextSpan,
)


def span(start: int, end: int, text: str) -> TextSpan:
    return TextSpan(start=start, end=end, text=text)


def argument(start: int, end: int, text: str) -> PdtbArgument:
    return PdtbArgument(spans=[span(start, end, text)])


def base_relation(relation_type: RelationType, **overrides: object) -> PdtbRelation:
    values: dict[str, object] = {
        "relation_id": f"r_{relation_type.value.casefold()}",
        "relation_type": relation_type,
        "arg1": argument(0, 4, "Rain"),
        "arg2": argument(10, 17, "traffic"),
    }
    if relation_type is RelationType.EXPLICIT:
        values |= {"senses": [PdtbSense.CONTINGENCY_CAUSE_RESULT], "connective_spans": [span(5, 7, "so")]}
    elif relation_type is RelationType.IMPLICIT:
        values |= {"senses": [PdtbSense.CONTINGENCY_CAUSE_RESULT], "inferred_connectives": ["so"]}
    elif relation_type in {RelationType.ALTLEX, RelationType.ALTLEXC}:
        values |= {
            "senses": [PdtbSense.CONTINGENCY_CAUSE_RESULT],
            "alternative_lexicalization_spans": [span(5, 9, "made")],
        }
    values.update(overrides)
    return PdtbRelation.model_validate(values)


@pytest.mark.parametrize("relation_type", list(RelationType))
def test_all_seven_pdtb3_relation_types_round_trip(relation_type: RelationType) -> None:
    relation = base_relation(relation_type)
    assert relation.to_payload()["relation_type"] == relation_type.value


def test_multiple_senses_are_preserved_without_flattening() -> None:
    relation = base_relation(
        RelationType.EXPLICIT,
        senses=[PdtbSense.TEMPORAL_SYNCHRONOUS, PdtbSense.COMPARISON_CONTRAST],
    )
    assert relation.to_payload()["senses"] == ["Temporal.Synchronous", "Comparison.Contrast"]


def test_shipped_sense_constant_is_exactly_the_enum() -> None:
    assert PDTB3_SENSES == tuple(item.value for item in PdtbSense)
    assert len(PDTB3_SENSES) == len(set(PDTB3_SENSES))
    assert "Expansion.List" not in PDTB3_SENSES


def test_discontinuous_spans_are_ordered_and_preserved() -> None:
    arg = PdtbArgument(spans=[span(0, 4, "Rain"), span(18, 25, "stopped")])
    spans = arg.to_payload()["spans"]
    assert isinstance(spans, list) and isinstance(spans[1], dict)
    assert spans[1]["start"] == 18


def test_arg1_need_not_precede_arg2() -> None:
    relation = base_relation(
        RelationType.EXPLICIT,
        arg1=argument(10, 17, "traffic"),
        arg2=argument(0, 4, "Rain"),
    )
    assert relation.arg1.spans[0].start == 10


def test_argument_spans_must_not_overlap() -> None:
    with pytest.raises(ValidationError, match="argument spans overlap"):
        base_relation(RelationType.IMPLICIT, arg2=argument(3, 8, "nfall"))


@pytest.mark.parametrize("relation_type", [RelationType.ENTREL, RelationType.HYPOPHORA, RelationType.NOREL])
def test_non_sense_types_forbid_senses(relation_type: RelationType) -> None:
    with pytest.raises(ValidationError, match="must not carry senses"):
        base_relation(relation_type, senses=[PdtbSense.EXPANSION_CONJUNCTION])


def test_explicit_requires_source_connective_evidence() -> None:
    with pytest.raises(ValidationError, match="explicit connective"):
        base_relation(RelationType.EXPLICIT, connective_spans=[])


def test_implicit_requires_inferred_connective_only() -> None:
    with pytest.raises(ValidationError, match="inferred connective"):
        base_relation(RelationType.IMPLICIT, inferred_connectives=[])


def test_altlex_requires_exact_alternative_evidence() -> None:
    with pytest.raises(ValidationError, match="alternative lexicalization"):
        base_relation(RelationType.ALTLEX, alternative_lexicalization_spans=[])


def test_exact_source_slices_are_mandatory() -> None:
    analysis = PdtbAnalysis(relations=[base_relation(RelationType.EXPLICIT)])
    with pytest.raises(RelationError, match="does not equal source slice"):
        analysis.validate_source("Hail so traffic")


def test_relation_ids_are_unique() -> None:
    relation = base_relation(RelationType.ENTREL)
    with pytest.raises(ValidationError, match="relation ids must be unique"):
        PdtbAnalysis(relations=[relation, relation])

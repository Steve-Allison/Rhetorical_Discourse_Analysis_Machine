"""Causal tests for native SDRS graph invariants."""

from pydantic import ValidationError
import pytest

from rdam.sdrt.graph import (
    ComplexDiscourseUnit,
    ElementaryDiscourseUnit,
    GraphError,
    RelationStructure,
    SdrtAnalysis,
    SdrtRelation,
)


def edu(unit_id: str, text: str, start: int, end: int) -> ElementaryDiscourseUnit:
    return ElementaryDiscourseUnit(unit_id=unit_id, text=text, start=start, end=end)


def relation(
    relation_id: str,
    source_id: str,
    target_id: str,
    *,
    structural_type: RelationStructure = RelationStructure.SUBORDINATING,
    label: str = "Elaboration",
) -> SdrtRelation:
    return SdrtRelation(
        relation_id=relation_id,
        source_id=source_id,
        target_id=target_id,
        label=label,
        structural_type=structural_type,
    )


def valid_graph() -> SdrtAnalysis:
    return SdrtAnalysis(
        edus=[edu("e1", "One.", 0, 4), edu("e2", "Two.", 5, 9), edu("e3", "Three.", 10, 16)],
        cdus=[ComplexDiscourseUnit(unit_id="c1", members=["e1", "e2"])],
        relations=[
            relation("r1", "e1", "e2"),
            relation(
                "r2",
                "c1",
                "e3",
                structural_type=RelationStructure.COORDINATING,
                label="Narration",
            ),
        ],
    )


def test_valid_graph_preserves_cdu_scope_and_structural_class() -> None:
    graph = valid_graph()
    graph.validate_source("One. Two. Three.")
    payload = graph.to_payload()
    assert payload["cdus"] == [{"unit_id": "c1", "members": ["e1", "e2"]}]
    relations = payload["relations"]
    assert isinstance(relations, list) and isinstance(relations[1], dict)
    assert relations[1]["source_id"] == "c1"
    assert relations[1]["structural_type"] == "coordinating"
    assert payload["right_frontier_validated"] is True


@pytest.mark.parametrize(
    ("field", "value"),
    [("start", -1), ("end", 0)],
)
def test_edu_offsets_must_form_a_positive_span(field: str, value: int) -> None:
    values = {"unit_id": "e1", "text": "x", "start": 0, "end": 1, field: value}
    with pytest.raises(ValidationError):
        ElementaryDiscourseUnit.model_validate(values)


@pytest.mark.parametrize(
    ("field", "value"),
    (("start", "0"), ("end", True)),
)
def test_edu_offsets_refuse_non_integer_coercion(field: str, value: object) -> None:
    values = {"unit_id": "e1", "text": "x", "start": 0, "end": 1, field: value}
    with pytest.raises(ValidationError):
        ElementaryDiscourseUnit.model_validate(values)


def test_exact_source_slice_is_mandatory() -> None:
    with pytest.raises(GraphError, match="does not equal source slice"):
        valid_graph().validate_source("One! Two. Three.")


def test_edu_spans_are_ordered_and_non_overlapping() -> None:
    with pytest.raises(ValidationError, match="ordered and non-overlapping"):
        SdrtAnalysis(edus=[edu("e1", "later", 5, 10), edu("e2", "first", 0, 5)])


def test_every_reference_must_resolve() -> None:
    with pytest.raises(ValidationError, match="unknown discourse unit"):
        SdrtAnalysis(edus=[edu("e1", "One.", 0, 4)], relations=[relation("r1", "e1", "missing")])


def test_cdu_membership_must_be_acyclic() -> None:
    with pytest.raises(ValidationError, match="CDU membership is cyclic"):
        SdrtAnalysis(
            edus=[edu("e1", "One.", 0, 4)],
            cdus=[
                ComplexDiscourseUnit(unit_id="c1", members=["e1", "c2"]),
                ComplexDiscourseUnit(unit_id="c2", members=["e1", "c1"]),
            ],
        )


def test_cdu_cycle_detection_does_not_depend_on_an_id_prefix() -> None:
    with pytest.raises(ValidationError, match="CDU membership is cyclic"):
        SdrtAnalysis(
            edus=[edu("e1", "One.", 0, 4)],
            cdus=[
                ComplexDiscourseUnit(unit_id="group_alpha", members=["e1", "group_beta"]),
                ComplexDiscourseUnit(unit_id="group_beta", members=["e1", "group_alpha"]),
            ],
        )


def test_relation_graph_must_be_acyclic() -> None:
    with pytest.raises(ValidationError, match="relation graph is cyclic"):
        SdrtAnalysis(
            edus=[edu("e1", "One.", 0, 4), edu("e2", "Two.", 5, 9)],
            relations=[relation("r1", "e1", "e2"), relation("r2", "e2", "e1")],
        )


def test_graph_must_be_connected() -> None:
    with pytest.raises(ValidationError, match="graph is disconnected"):
        SdrtAnalysis(edus=[edu("e1", "One.", 0, 4), edu("e2", "Two.", 5, 9)])


def test_one_pair_cannot_mix_structural_classes() -> None:
    with pytest.raises(ValidationError, match="both structural classes"):
        SdrtAnalysis(
            edus=[edu("e1", "One.", 0, 4), edu("e2", "Two.", 5, 9)],
            relations=[
                relation("r1", "e1", "e2"),
                relation("r2", "e1", "e2", structural_type=RelationStructure.COORDINATING),
            ],
        )


def test_right_frontier_accepts_reverse_subordinating_ancestry() -> None:
    graph = SdrtAnalysis(
        edus=[edu("e1", "One.", 0, 4), edu("e2", "Two.", 5, 9), edu("e3", "Three.", 10, 16)],
        relations=[relation("r1", "e1", "e2"), relation("r2", "e1", "e3")],
    )
    assert graph.to_payload()["right_frontier_validated"] is True


def test_attachment_outside_the_right_frontier_is_refused() -> None:
    with pytest.raises(ValidationError, match="right frontier"):
        SdrtAnalysis(
            edus=[
                edu("e1", "One.", 0, 4),
                edu("e2", "Two.", 5, 9),
                edu("e3", "Three.", 10, 16),
            ],
            relations=[
                relation("r1", "e1", "e2", structural_type=RelationStructure.COORDINATING),
                relation("r2", "e1", "e3"),
            ],
        )

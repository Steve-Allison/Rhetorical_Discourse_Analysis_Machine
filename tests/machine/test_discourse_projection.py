"""Discourse and technique projections match Central_Configs v5.0.0 and reject broken IDs."""

from copy import deepcopy
from pathlib import Path
from typing import Any, cast

import pytest

from rdam._interpretation_types import NativeSectionDescription
from rdam.ontology import (
    AlignedFramework,
    NativeOntologyAlignment,
    native_framework_values,
    native_vocabulary_alignment,
    pdtb_sense_alignment,
    toulmin_role_alignment,
)
from rdam.pdtb.relations import PdtbSense
from rdam.toulmin.interpretation import describe
from rdam.toulmin.output import HistoricalLayoutOutput
from tools.ontology.project_discourse_concepts import (
    CENTRAL_ROOT,
    OUTPUT,
    VOCABULARY_OUTPUT,
    project,
    project_vocabularies,
    render,
    validate_discourse_projection,
)

ROOT = Path(__file__).resolve().parents[2]
CENTRAL = (ROOT / CENTRAL_ROOT).resolve()


def test_packaged_discourse_projection_matches_central_sqlite() -> None:
    assert (ROOT / OUTPUT).read_text(encoding="utf-8") == render(project(CENTRAL))


def test_toulmin_guide_resolves_every_native_role_to_v5_curies() -> None:
    alignment = toulmin_role_alignment()
    native_roles = HistoricalLayoutOutput.model_json_schema()["properties"]["elements_present"]["items"]["enum"]
    assert {mapping.native_value for mapping in alignment.mappings} == set(native_roles)
    authority = project(CENTRAL)
    expected_curies = {
        "claim": "coe:C06101",
        "grounds": "coe:C06102",
        "warrant": "coe:C06103",
        "backing": "coe:C06104",
        "qualifier": "coe:C06105",
        "rebuttal": "coe:C06106",
    }
    for mapping in alignment.mappings:
        assert mapping.concept_id == expected_curies[mapping.native_value]
        assert authority["concepts"][mapping.concept_id]["label"] == mapping.label
        assert mapping.relationship == "exact"
    descriptor = describe("toulmin_layouts", "2.0.0")
    assert descriptor.sections[0].ontology_alignment == alignment
    assert type(descriptor).model_validate_json(descriptor.model_dump_json()) == descriptor


def test_existing_unmapped_section_serialization_is_unchanged() -> None:
    section = NativeSectionDescription(pointer="/payload", meaning="Native evidence")
    assert section.model_dump() == {"pointer": "/payload", "meaning": "Native evidence", "availability": "present"}


def test_pdtb_vocabulary_maps_supported_senses_and_tracks_unmapped_explicitly() -> None:
    alignment = pdtb_sense_alignment()
    mapped = {mapping.native_value: mapping for mapping in alignment.mappings}
    assert set(mapped).isdisjoint(alignment.unmapped_native_values)
    assert set(mapped) | set(alignment.unmapped_native_values) == {sense.value for sense in PdtbSense}
    assert mapped[PdtbSense.COMPARISON_CONTRAST].concept_id == "coe:C06126"
    assert mapped[PdtbSense.COMPARISON_CONTRAST].relationship == "exact"
    assert mapped[PdtbSense.CONTINGENCY_CAUSE_RESULT].concept_id == "coe:C06123"
    assert mapped[PdtbSense.CONTINGENCY_CAUSE_RESULT].relationship == "exact"
    assert "Expansion.Conjunction" in alignment.unmapped_native_values
    payload = alignment.model_dump()
    payload["mappings"][0]["relationship"] = (
        "broader" if payload["mappings"][0]["relationship"] == "exact" else "exact"
    )
    with pytest.raises(ValueError, match="native inventory"):
        type(alignment).model_validate(payload)


def test_packaged_technique_vocabularies_match_authority() -> None:
    assert (ROOT / VOCABULARY_OUTPUT).read_text(encoding="utf-8") == render(project_vocabularies(CENTRAL))


@pytest.mark.parametrize(
    "framework",
    ("pdtb", "walton", "ibis", "dung", "sdrt", "classical_rhetoric"),
)
def test_registered_inventory_is_complete_and_cannot_be_forged(framework: AlignedFramework) -> None:
    alignment = native_vocabulary_alignment(framework)
    mapped_values = {item.native_value for item in alignment.mappings}
    unmapped_values = set(alignment.unmapped_native_values)
    assert mapped_values.isdisjoint(unmapped_values)
    assert mapped_values | unmapped_values == set(native_framework_values(framework))
    assert NativeOntologyAlignment.model_validate_json(alignment.model_dump_json()) == alignment

    payload = alignment.model_dump()
    if payload["mappings"]:
        payload["mappings"] = payload["mappings"][1:]
    else:
        payload["unmapped_native_values"] = payload["unmapped_native_values"][1:]
    with pytest.raises(ValueError, match="native inventory"):
        NativeOntologyAlignment.model_validate(payload)


def test_saved_alignment_rejects_unknown_canonical_reference() -> None:
    alignment = toulmin_role_alignment()
    payload = alignment.model_dump()
    payload["mappings"][0]["concept_id"] = "coe:C99999"
    with pytest.raises(ValueError, match="canonical reference"):
        type(alignment).model_validate(payload)


@pytest.mark.parametrize("mutation", ("missing_role", "spurious_unmapped"))
def test_toulmin_alignment_rejects_incomplete_coverage(mutation: str) -> None:
    alignment = toulmin_role_alignment()
    payload = alignment.model_dump()
    if mutation == "missing_role":
        payload["mappings"] = payload["mappings"][1:]
    else:
        payload["unmapped_native_values"] = ("invented_role",)
    with pytest.raises(ValueError, match="every registered role"):
        type(alignment).model_validate(payload)


@pytest.mark.parametrize(
    "mutation",
    ("foreign_scheme", "missing_stage_parent", "self_stage_parent", "cycle", "unresolved_linked"),
)
def test_discourse_projection_rejects_invalid_references(mutation: str) -> None:
    projection = deepcopy(project(CENTRAL))
    concepts = cast(dict[str, dict[str, Any]], projection["concepts"])
    stage_id = next(cid for cid, item in concepts.items() if item["collection_name"] == "framework_stages")
    framework_id = str(concepts[stage_id]["payload"]["stage_of_framework"])
    active_ids = set(concepts)
    match mutation:
        case "foreign_scheme":
            concepts[stage_id]["in_scheme"] = "https://example.invalid/foreign"
        case "missing_stage_parent":
            concepts[stage_id]["payload"]["stage_of_framework"] = "coe:C99999"
        case "self_stage_parent":
            concepts[stage_id]["payload"]["stage_of_framework"] = stage_id
        case "cycle":
            concepts[framework_id]["payload"]["stage_of_framework"] = stage_id
        case "unresolved_linked":
            concepts[stage_id]["payload"]["linked_concepts"] = ["coe:C99999"]
        case _:
            raise ValueError(f"Unknown mutation: {mutation}")
    with pytest.raises(ValueError):
        validate_discourse_projection(projection, all_active_ids=active_ids)

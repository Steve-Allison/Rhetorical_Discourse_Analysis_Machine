"""The discourse projection preserves Central authority and rejects broken IDs."""

from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from tools.ontology.project_discourse_concepts import (
    OUTPUT, SOURCE, VOCABULARY_OUTPUT, project, project_vocabularies, render,
)
from rdam.ontology import AlignedFramework, toulmin_role_alignment, pdtb_sense_alignment, native_vocabulary_alignment
from rdam.pdtb.relations import PdtbSense
from rdam.toulmin.interpretation import describe
from rdam.toulmin.output import HistoricalLayoutOutput
from rdam._interpretation_types import NativeSectionDescription


def test_packaged_discourse_projection_matches_authority() -> None:
    assert OUTPUT.read_text(encoding="utf-8") == render(project(SOURCE))


def test_toulmin_guide_resolves_every_native_role_to_registered_authority() -> None:
    alignment = toulmin_role_alignment()
    native_roles = HistoricalLayoutOutput.model_json_schema()["properties"]["elements_present"]["items"]["enum"]
    assert {mapping.native_value for mapping in alignment.mappings} == set(native_roles)
    authority = project(SOURCE)
    for mapping in alignment.mappings:
        assert authority["concepts"][mapping.concept_id]["label"] == mapping.label
        assert mapping.relationship == "exact"
    descriptor = describe("toulmin_layouts", "2.0.0")
    assert descriptor.sections[0].ontology_alignment == alignment
    assert type(descriptor).model_validate_json(descriptor.model_dump_json()) == descriptor


def test_existing_unmapped_section_serialization_is_unchanged() -> None:
    section = NativeSectionDescription(pointer="/payload", meaning="Native evidence")
    assert section.model_dump() == {"pointer": "/payload", "meaning": "Native evidence", "availability": "present"}


def test_pdtb_vocabulary_preserves_every_fine_distinction() -> None:
    alignment = pdtb_sense_alignment()
    mapped = {mapping.native_value: mapping for mapping in alignment.mappings}
    assert set(mapped).isdisjoint(alignment.unmapped_native_values)
    assert set(mapped) | set(alignment.unmapped_native_values) == {sense.value for sense in PdtbSense}
    assert mapped[PdtbSense.COMPARISON_CONTRAST].relationship == "exact"
    assert all(mapping.relationship == "exact" for mapping in mapped.values())
    assert not alignment.unmapped_native_values
    assert len({mapping.concept_id for mapping in mapped.values()}) == len(PdtbSense)
    payload = alignment.model_dump()
    payload["mappings"][0]["relationship"] = "broader"
    with pytest.raises(ValueError, match="native inventory"):
        type(alignment).model_validate(payload)


def test_packaged_technique_vocabularies_match_authority() -> None:
    assert VOCABULARY_OUTPUT.read_text(encoding="utf-8") == render(project_vocabularies())


@pytest.mark.parametrize("framework", ("pdtb", "walton", "ibis", "dung", "sdrt"))
def test_registered_inventory_is_complete_and_cannot_be_forged(framework: AlignedFramework) -> None:
    from rdam.ontology import NativeOntologyAlignment

    alignment = native_vocabulary_alignment(framework)
    assert alignment.mappings
    assert not alignment.unmapped_native_values
    assert NativeOntologyAlignment.model_validate_json(alignment.model_dump_json()) == alignment
    payload = alignment.model_dump()
    payload["mappings"] = payload["mappings"][1:]
    with pytest.raises(ValueError, match="native inventory"):
        NativeOntologyAlignment.model_validate(payload)


def test_saved_alignment_rejects_unknown_canonical_reference() -> None:
    alignment = toulmin_role_alignment()
    payload = alignment.model_dump()
    payload["mappings"][0]["concept_id"] = "coe:concept/invented"
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


@pytest.mark.parametrize("mutation", ("duplicate", "foreign", "missing", "cycle"))
def test_discourse_projection_rejects_invalid_references(tmp_path: Path, mutation: str) -> None:
    document = yaml.safe_load(SOURCE.read_bytes())
    concepts = document["taxonomies"][0]["concepts"]
    parent, child = concepts[:2]
    match mutation:
        case "duplicate":
            concepts.append(deepcopy(child))
        case "foreign":
            child["in_scheme"] = "coe:artifact/foreign"
        case "missing":
            child["broader"] = ["coe:concept/missing"]
        case "cycle":
            parent["broader"] = [child["id"]]
        case _:
            raise ValueError(f"Unknown mutation: {mutation}")
    source = tmp_path / "taxonomy.yaml"
    source.write_text(yaml.safe_dump(document), encoding="utf-8")
    with pytest.raises(ValueError):
        project(source)

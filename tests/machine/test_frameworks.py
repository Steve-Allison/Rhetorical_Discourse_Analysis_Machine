"""Framework identities resolve to Central and the packaged projection never drifts."""

from pathlib import Path

import yaml

from rdam import BOUNDARY_TECHNIQUES, FRAMEWORK_SCHEME, STRUCTURED_INPUT_TECHNIQUES, Technique, framework_identities, technique_curie
from tools.ontology.project_framework_identities import PROJECTION, VENDORED_TAXONOMY, project, render

ROOT = Path(__file__).resolve().parents[2]


def test_all_eight_identities_resolve_to_the_scheme() -> None:
    identities = framework_identities()
    assert set(identities) == set(Technique)
    for technique, identity in identities.items():
        assert identity.scheme == FRAMEWORK_SCHEME
        assert identity.curie.endswith(f"/{technique.value}")
        assert identity.broader.startswith("coe:concept/analytical_frameworks_taxonomy/")


def test_boundaries_are_the_seven_of_fr_002_and_erst_is_a_formalism() -> None:
    assert BOUNDARY_TECHNIQUES == (
        Technique.RST,
        Technique.PDTB,
        Technique.SDRT,
        Technique.TOULMIN,
        Technique.WALTON,
        Technique.DUNG,
        Technique.IBIS,
    )
    assert Technique.ERST not in BOUNDARY_TECHNIQUES
    assert STRUCTURED_INPUT_TECHNIQUES == {Technique.DUNG, Technique.IBIS}


def test_packaged_projection_equals_a_fresh_projection_of_the_vendored_taxonomy() -> None:
    committed = (ROOT / PROJECTION).read_text(encoding="utf-8")
    assert committed == render(project(ROOT / VENDORED_TAXONOMY))


def test_curies_are_exactly_the_vendored_concept_ids() -> None:
    document = yaml.safe_load((ROOT / VENDORED_TAXONOMY).read_text(encoding="utf-8"))
    taxonomy = next(item for item in document["taxonomies"] if item["id"] == FRAMEWORK_SCHEME)
    vendored_ids = {concept["id"] for concept in taxonomy["concepts"]}
    for technique in Technique:
        assert technique_curie(technique) in vendored_ids

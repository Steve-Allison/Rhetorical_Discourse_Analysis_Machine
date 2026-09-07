"""Framework identities resolve to Central and the packaged projection never drifts."""

from collections.abc import MutableMapping
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from typing import cast

import pytest
import yaml

from rdam import BOUNDARY_TECHNIQUES, FRAMEWORK_SCHEME, STRUCTURED_INPUT_TECHNIQUES, Technique, framework_identities, technique_curie
from tools.ontology.project_framework_identities import PROJECTION, VENDORED_TAXONOMY, project, render
from rdam.frameworks import FrameworkIdentity, FrameworkResolutionError

ROOT = Path(__file__).resolve().parents[2]


def test_callers_cannot_replace_cached_canonical_identities() -> None:
    identities = framework_identities()
    original = identities[Technique.RST]
    # Deliberately bypass the static Mapping interface to exercise runtime protection.
    mutable = cast(MutableMapping[Technique, FrameworkIdentity], identities)
    with pytest.raises(TypeError):
        mutable[Technique.RST] = identities[Technique.PDTB]
    assert technique_curie(Technique.RST) == original.curie


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


def test_projection_identifies_exact_source_bytes() -> None:
    source = ROOT / VENDORED_TAXONOMY
    assert project(source)["source_sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()


@pytest.mark.parametrize("mutation", ("duplicate", "missing_parent", "foreign_parent", "self_parent", "foreign_scheme"))
def test_projection_rejects_inconsistent_authority_references(tmp_path: Path, mutation: str) -> None:
    document = yaml.safe_load((ROOT / VENDORED_TAXONOMY).read_text(encoding="utf-8"))
    concepts = document["taxonomies"][0]["concepts"]
    rst = next(concept for concept in concepts if concept["id"].endswith("/rst"))
    match mutation:
        case "duplicate":
            concepts.append(deepcopy(rst))
        case "missing_parent":
            rst["broader"] = ["coe:concept/missing"]
        case "foreign_parent":
            parent = next(concept for concept in concepts if concept["id"] == rst["broader"][0])
            parent["in_scheme"] = "coe:artifact/foreign"
        case "self_parent":
            rst["broader"] = [rst["id"]]
        case "foreign_scheme":
            rst["in_scheme"] = "coe:artifact/foreign"
        case _:
            raise ValueError(f"Unknown mutation: {mutation}")
    source = tmp_path / "taxonomy.yaml"
    source.write_text(yaml.safe_dump(document), encoding="utf-8")
    with pytest.raises(ValueError):
        project(source)


@pytest.mark.parametrize("mutation", ("null_label", "foreign_parent", "unknown_technique"))
def test_runtime_rejects_malformed_packaged_projection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutation: str,
) -> None:
    payload = json.loads((ROOT / PROJECTION).read_bytes())
    match mutation:
        case "null_label":
            payload["concepts"]["rst"]["label"] = None
        case "foreign_parent":
            payload["concepts"]["rst"]["broader"] = "coe:concept/foreign"
        case "unknown_technique":
            payload["concepts"]["unknown"] = payload["concepts"]["rst"]
        case _:
            raise ValueError(f"Unknown mutation: {mutation}")
    resource = tmp_path / "resources" / "framework-identities.json"
    resource.parent.mkdir()
    resource.write_text(json.dumps(payload), encoding="utf-8")
    def packaged_files(anchor: str) -> Path:
        assert anchor == "rdam"
        return tmp_path

    monkeypatch.setattr("rdam.frameworks.resources.files", packaged_files)
    framework_identities.cache_clear()
    try:
        with pytest.raises(FrameworkResolutionError):
            framework_identities()
    finally:
        framework_identities.cache_clear()

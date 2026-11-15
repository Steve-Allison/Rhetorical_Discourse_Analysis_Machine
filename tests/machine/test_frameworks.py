"""Framework identities resolve against Central_Configs v5.0.0 and never drift."""

from collections.abc import MutableMapping
from copy import deepcopy
import json
from pathlib import Path
import re
import sqlite3
from typing import Any, cast

import pytest
import yaml

from rdam import (
    ACCEPTS_STRUCTURED_INPUT_TECHNIQUES,
    BOUNDARY_TECHNIQUES,
    FRAMEWORK_SCHEME,
    STRUCTURED_INPUT_TECHNIQUES,
    Technique,
    framework_identities,
    technique_curie,
)
from rdam.frameworks import FrameworkIdentity, FrameworkResolutionError
from tools.ontology.project_framework_identities import (
    CENTRAL_ROOT,
    PROJECTION,
    PROVIDERS_PATH,
    project,
    render,
)

ROOT = Path(__file__).resolve().parents[2]
CENTRAL = (ROOT / CENTRAL_ROOT).resolve()
PROVIDERS = ROOT / PROVIDERS_PATH
COE_CURIE_RE = re.compile(r"^coe:C[0-9]{5}$")

EXPECTED_CENTRAL_TECHNIQUES = {
    Technique.RST: "coe:C06123",
    Technique.PDTB: "coe:C00108",
    Technique.SDRT: "coe:C06129",
    Technique.CLASSICAL_RHETORIC: "coe:C06007",
    Technique.TOULMIN: "coe:C06101",
    Technique.WALTON: "coe:C06107",
    Technique.IBIS: "coe:C06111",
    Technique.DUNG: "coe:C06106",
}


def test_callers_cannot_replace_cached_canonical_identities() -> None:
    identities = framework_identities()
    original = identities[Technique.RST]
    mutable = cast(MutableMapping[Technique, FrameworkIdentity], identities)
    with pytest.raises(TypeError):
        mutable[Technique.RST] = identities[Technique.PDTB]
    assert technique_curie(Technique.RST) == original.curie


def test_all_fourteen_identities_resolve_to_the_v5_scheme() -> None:
    identities = framework_identities()
    assert FRAMEWORK_SCHEME == "https://steve-allison.github.io/Central_Configs/v5/schema/coe"
    assert set(identities) == set(Technique)
    for technique, identity in identities.items():
        assert identity.scheme == FRAMEWORK_SCHEME
        assert technique_curie(technique) == identity.curie
        if technique in EXPECTED_CENTRAL_TECHNIQUES:
            assert identity.authority == "central_configs"
            assert identity.curie == EXPECTED_CENTRAL_TECHNIQUES[technique]
            assert COE_CURIE_RE.match(identity.curie)
            assert identity.broader.startswith(f"{FRAMEWORK_SCHEME}#")
            assert identity.curie in identity.central_concepts
            assert all(COE_CURIE_RE.match(cid) for cid in identity.central_concepts)
        else:
            assert identity.authority == "rdam"
            assert identity.curie == f"rdmachine:framework/{technique.value}"
            assert identity.broader == "rdmachine:framework"
            assert identity.central_concepts == ()


def test_boundaries_are_the_thirteen_production_techniques_and_erst_is_a_formalism() -> None:
    assert BOUNDARY_TECHNIQUES == (
        Technique.RST,
        Technique.CENTERING,
        Technique.PDTB,
        Technique.SDRT,
        Technique.SPEECH_ACTS,
        Technique.CLASSICAL_RHETORIC,
        Technique.ARGUMENT_MINING,
        Technique.TOULMIN,
        Technique.WALTON,
        Technique.PRAGMA_DIALECTICS,
        Technique.IBIS,
        Technique.ASPIC,
        Technique.DUNG,
    )
    assert Technique.ERST not in BOUNDARY_TECHNIQUES
    assert STRUCTURED_INPUT_TECHNIQUES == {Technique.DUNG}
    assert ACCEPTS_STRUCTURED_INPUT_TECHNIQUES == {Technique.DUNG, Technique.IBIS, Technique.ASPIC}


def test_packaged_projection_equals_a_fresh_projection_against_central_sqlite() -> None:
    committed = (ROOT / PROJECTION).read_text(encoding="utf-8")
    assert committed == render(project(PROVIDERS, CENTRAL))


def test_central_curies_resolve_to_active_resources_in_central_sqlite() -> None:
    sqlite_path = CENTRAL / "dist" / "build" / "central.sqlite"
    uri = f"file:{sqlite_path.as_posix()}?mode=ro"
    with sqlite3.connect(uri, uri=True) as conn:
        active = {
            str(row[0]): str(row[1])
            for row in conn.execute("SELECT id, pref_label FROM resources WHERE status = 'active'").fetchall()
        }
    for technique, expected_curie in EXPECTED_CENTRAL_TECHNIQUES.items():
        identity = framework_identities()[technique]
        assert identity.curie == expected_curie
        assert identity.curie in active
        assert identity.label == active[identity.curie]
        for concept_curie in identity.central_concepts:
            assert concept_curie in active


@pytest.mark.parametrize(
    "mutation",
    (
        "duplicate_boundary",
        "unresolved_curie",
        "invalid_curie_format",
        "foreign_scheme",
        "rdam_with_central_concepts",
        "primary_missing_from_central_concepts",
    ),
)
def test_projection_rejects_inconsistent_provider_bindings(tmp_path: Path, mutation: str) -> None:
    document = cast(dict[str, Any], yaml.safe_load(PROVIDERS.read_text(encoding="utf-8")))
    bindings = cast(list[dict[str, Any]], document["bindings"])
    toulmin = next(item for item in bindings if item["boundary"] == "toulmin")
    centering = next(item for item in bindings if item["boundary"] == "centering")
    match mutation:
        case "duplicate_boundary":
            bindings.append(deepcopy(toulmin))
        case "unresolved_curie":
            toulmin["framework"] = "coe:C99999"
            toulmin["central_concepts"] = ["coe:C99999"]
        case "invalid_curie_format":
            toulmin["framework"] = "coe:invalid"
        case "foreign_scheme":
            document["scheme"] = "https://example.invalid/foreign"
        case "rdam_with_central_concepts":
            centering["central_concepts"] = ["coe:C06101"]
        case "primary_missing_from_central_concepts":
            toulmin["central_concepts"] = ["coe:C06102"]
        case _:
            raise ValueError(f"Unknown mutation: {mutation}")
    mutated_path = tmp_path / "rdam-providers.yaml"
    mutated_path.write_text(yaml.safe_dump(document), encoding="utf-8")
    with pytest.raises(ValueError):
        project(mutated_path, CENTRAL)


@pytest.mark.parametrize(
    "mutation",
    ("null_label", "invalid_central_curie", "unknown_technique", "mismatched_lookup_table"),
)
def test_runtime_rejects_malformed_packaged_projection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutation: str,
) -> None:
    payload = cast(dict[str, Any], json.loads((ROOT / PROJECTION).read_bytes()))
    match mutation:
        case "null_label":
            payload["concepts"]["rst"]["label"] = None
        case "invalid_central_curie":
            payload["concepts"]["rst"]["id"] = "coe:invalid"
            payload["native_to_curie"]["rst"] = "coe:invalid"
        case "unknown_technique":
            payload["concepts"]["unknown"] = payload["concepts"]["rst"]
        case "mismatched_lookup_table":
            payload["native_to_curie"]["rst"] = "coe:C06101"
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

"""Authoritative v5 SQLite compiler checks and SurfaceMatchRule invariants."""

import json
from pathlib import Path
import shutil
import sqlite3

from jsonschema import ValidationError, validate
import pytest

from rdam.concepts import ConceptIndex, ConceptLinkRequest, MatchingOptions, link_source
from rdam.concepts.index import IndexProjection, LexicalEntry, SemanticResource
from rdam.concepts.serialization import load_request, schema
from rdam.ingest.contracts.source import SourceArtifact
from tools.compile_concept_index import compile_distribution


def test_policies_historical_status_and_domain_restriction() -> None:
    active_one = SemanticResource(
        curie="coe:C90001",
        pref_label="Alpha Suite",
        definition="test suite",
        collection_name="offerings",
        status="active",
    )
    deprecated_one = SemanticResource(
        curie="coe:C90002",
        pref_label="Legacy Alpha",
        definition="deprecated suite",
        collection_name="offerings",
        status="deprecated",
    )
    historical_two = SemanticResource(
        curie="coe:C90003",
        pref_label="Historical Product",
        definition="discontinued",
        collection_name="editions",
        status="historical_only",
    )
    entries = (
        LexicalEntry(
            curie="coe:C90001",
            pref_label="Alpha Suite",
            collection_name="offerings",
            surface="ALS",
            match_policy="case_exact",
            case_sensitive=True,
        ),
        LexicalEntry(
            curie="coe:C90001",
            pref_label="Alpha Suite",
            collection_name="offerings",
            surface="Alpha",
            match_policy="context_anchored",
            context_anchors=("Suite", "Enterprise"),
        ),
        LexicalEntry(
            curie="coe:C90001",
            pref_label="Alpha Suite",
            collection_name="offerings",
            surface="IgnoredAlias",
            match_policy="never_link",
        ),
        LexicalEntry(
            curie="coe:C90002",
            pref_label="Legacy Alpha",
            collection_name="offerings",
            surface="Legacy Alpha",
            match_policy="unambiguous",
        ),
        LexicalEntry(
            curie="coe:C90003",
            pref_label="Historical Product",
            collection_name="editions",
            surface="Historical Product",
            match_policy="unambiguous",
        ),
    )
    projection = IndexProjection(
        distribution_id="https://steve-allison.github.io/Central_Configs/v5/schema/coe",
        version="5.0.0",
        domains=("editions", "offerings"),
        resources=(active_one, deprecated_one, historical_two),
        entries=entries,
    )
    index = ConceptIndex(projection=projection, domains=projection.domains)
    source = SourceArtifact.from_text(
        "als ALS Alpha Enterprise IgnoredAlias Legacy Alpha Historical Product",
        source_name="test",
    )
    result = link_source(source, index)
    assert [(m.quote, m.curie, m.resolution) for m in result.mentions] == [
        ("ALS", "coe:C90001", "unique"),
        ("Alpha", "coe:C90001", "unique"),
        ("Legacy Alpha", "coe:C90002", "unique"),
    ]
    insensitive = link_source(source, index, options=MatchingOptions(acronym_case_sensitive=False))
    assert [m.quote for m in insensitive.mentions] == ["als", "ALS", "Alpha", "Legacy Alpha"]
    assert not link_source(source, ConceptIndex(projection=projection, domains=("editions",))).mentions


def test_surface_rule_validation_rejects_wildcards_and_missing_anchors() -> None:
    with pytest.raises(ValueError, match="regex metacharacters"):
        LexicalEntry(
            curie="coe:C90001",
            pref_label="Alpha",
            collection_name="offerings",
            surface="Alpha.*",
            match_policy="unambiguous",
        )
    with pytest.raises(ValueError, match="context_anchor"):
        LexicalEntry(
            curie="coe:C90001",
            pref_label="Alpha",
            collection_name="offerings",
            surface="Alpha",
            match_policy="context_anchored",
            context_anchors=(),
        )


@pytest.fixture
def distribution(tmp_path: Path) -> Path:
    root = Path(__file__).parents[3] / "Central_Configs"
    shutil.copytree(root / "schema", tmp_path / "schema")
    db_dest = tmp_path / "dist/build/central.sqlite"
    db_dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(root / "dist/build/central.sqlite", db_dest)
    return tmp_path


def test_real_sqlite_projection_is_reproducible(distribution: Path) -> None:
    assert compile_distribution(distribution) == ConceptIndex.load().projection


def test_missing_sqlite_or_schema_fails(distribution: Path) -> None:
    (distribution / "dist/build/central.sqlite").unlink()
    with pytest.raises(FileNotFoundError):
        compile_distribution(distribution)


@pytest.mark.parametrize(
    ("sql", "reason"),
    [
        (
            "UPDATE match_lexicon SET collection_name = 'discourse_relations' WHERE rowid = 1",
            "Rule 6 firewall violation",
        ),
        (
            "UPDATE match_lexicon SET surface = 'Adobe.*' WHERE rowid = 1",
            "regex metacharacters",
        ),
        (
            "UPDATE match_lexicon SET match_policy = 'context_anchored', context_anchors_json = '[]' WHERE rowid = 1",
            "context_anchor",
        ),
    ],
)
def test_invalid_sqlite_surface_rules_fail(distribution: Path, sql: str, reason: str) -> None:
    db_path = distribution / "dist/build/central.sqlite"
    with sqlite3.connect(db_path) as conn:
        conn.execute(sql)
        conn.commit()
    with pytest.raises(ValueError, match=reason):
        compile_distribution(distribution)


def test_concept_schemas_and_duplicate_json_rejection() -> None:
    request = ConceptLinkRequest(source=SourceArtifact.from_text("Adobe Analytics", source_name="test"))
    validate(json.loads(request.model_dump_json()), schema("concept-link-request"))
    validate(json.loads(ConceptIndex.load().projection.model_dump_json()), schema("concept-index"))
    with pytest.raises(ValidationError):
        validate({"source": None, "inventory": None}, schema("concept-link-request"))
    with pytest.raises(ValueError, match="duplicate"):
        load_request('{"source":null,"source":null}')

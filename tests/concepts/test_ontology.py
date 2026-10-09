"""Authoritative compiler failures and scoped lexical reasons."""
import json
from pathlib import Path

import pytest
import yaml

from rdam.concepts import ConceptIndex, MatchingOptions, link_source
from rdam.concepts.index import IndexProjection, LexicalEntry, SemanticResource, TermStatus, TermType
from rdam.ingest.contracts.source import SourceArtifact
from tools.compile_concept_index import compile_distribution


def test_term_types_statuses_retirement_and_domain_restriction() -> None:
    target = SemanticResource(identifier="target", label="Full Name", description="test", domain="one",
                              status="canonical", resource_type="Concept", source_path="test")
    retired = SemanticResource(identifier="retired", label="Retired", description="old", domain="two",
                               status="retired", resource_type="Concept", source_path="test")
    terms: tuple[tuple[str, TermType, TermStatus], ...] = (
        ("FN", "initialism", "admitted"), ("FUNA", "acronym", "admitted"), ("Fn", "product_code", "admitted"),
        ("Fuller", "full_form", "superseded"), ("Fake", "codename", "deprecated"), ("Full", "short_form", "admitted"),
    )
    entries = tuple(LexicalEntry(literal=literal, target="target", method="term", term_type=term_type, term_status=status)
                    for literal, term_type, status in terms)
    projection = IndexProjection(distribution_id="test", version="1.0.0", domains=("one", "two"), source_files=(),
        resources=(target, retired), entries=entries + (LexicalEntry(literal="Retired", target="retired", method="label"),),
        authorable_predicates=())
    index = ConceptIndex(projection=projection, domains=projection.domains)
    source = SourceArtifact.from_text("fn funa FN FUNA Fn fuller fake full Retired", source_name="test")
    result = link_source(source, index)
    assert [m.quote for m in result.mentions] == ["FN", "FUNA", "Fn", "fuller", "fake", "full"]
    assert [[(r.term_type, r.term_status) for r in m.candidates[0].reasons] for m in result.mentions] == [
        [("initialism", "admitted")], [("acronym", "admitted")], [("product_code", "admitted")],
        [("full_form", "superseded")], [("codename", "deprecated")], [("short_form", "admitted")],
    ]
    insensitive = link_source(source, index, options=MatchingOptions(acronym_case_sensitive=False))
    assert [m.quote for m in insensitive.mentions] == ["fn", "funa", "FN", "FUNA", "Fn", "fuller", "fake", "full"]
    assert not link_source(source, ConceptIndex(projection=projection, domains=("two",))).mentions


def test_label_cannot_carry_term_attributes_and_term_requires_them() -> None:
    with pytest.raises(ValueError, match="label evidence"):
        LexicalEntry(literal="x", target="t", method="label", term_type="initialism")
    with pytest.raises(ValueError, match="term evidence"):
        LexicalEntry(literal="x", target="t", method="term", term_type="initialism")
    with pytest.raises(ValueError, match="validity"):
        LexicalEntry(literal="x", target="t", method="term", term_type="full_form", term_status="superseded",
                     valid_from="2020-01", valid_to="2019")


@pytest.fixture
def distribution(tmp_path: Path) -> Path:
    root = Path(__file__).parents[3] / "Central_Configs"
    projection = ConceptIndex.load().projection
    for relative, _digest in projection.source_files:
        destination = tmp_path / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes((root / relative).read_bytes())
    return tmp_path


def test_real_manifest_projection_is_reproducible(distribution: Path) -> None:
    assert compile_distribution(distribution) == ConceptIndex.load().projection


def test_missing_declared_file_fails(distribution: Path) -> None:
    path = distribution / "ontology/data/distribution.yaml"
    data = yaml.safe_load(path.read_bytes())
    missing = distribution / data["domain_module_paths"][0]
    missing.unlink()
    with pytest.raises(FileNotFoundError):
        compile_distribution(distribution)


@pytest.mark.parametrize(("mutation", "reason"), [
    ("duplicate", "duplicate identifier"), ("term_type", "term_type"), ("term_status", "term_status"),
])
def test_invalid_authored_terminology_fails(distribution: Path, mutation: str, reason: str) -> None:
    projection = ConceptIndex.load().projection
    entry = next(entry for entry in projection.entries if entry.method == "term")
    owner = next(resource for resource in projection.resources if resource.identifier == entry.target)
    path = distribution / owner.source_path
    text = path.read_text()
    match mutation:
        case "duplicate":
            other = next(resource for resource in projection.resources
                         if resource.source_path == owner.source_path and resource.identifier != owner.identifier)
            text = text.replace(f"id: {other.identifier}\n", f"id: {owner.identifier}\n", 1)
        case "term_type":
            text = text.replace(f"term_type: {entry.term_type}", "term_type: nickname", 1)
        case _:
            text = text.replace(f"term_status: {entry.term_status}", "term_status: retired", 1)
    assert text != path.read_text(), "mutation must change actual authoritative record"
    path.write_text(text)
    with pytest.raises(ValueError, match=reason):
        compile_distribution(distribution)


def test_request_schema_and_duplicate_json_rejection() -> None:
    from jsonschema import validate, ValidationError
    from rdam.concepts.serialization import load_request, schema
    from rdam.concepts import ConceptLinkRequest
    request = ConceptLinkRequest(source=SourceArtifact.from_text("known", source_name="test"))
    validate(json.loads(request.model_dump_json()), schema("concept-link-request"))
    with pytest.raises(ValidationError):
        validate({"source": None, "inventory": None}, schema("concept-link-request"))
    with pytest.raises(ValueError, match="duplicate"):
        load_request('{"source":null,"source":null}')

"""Authoritative compiler failures and scoped lexical reasons."""
import json
from pathlib import Path

import pytest
import yaml

from rdam.concepts import ConceptIndex, MatchingOptions, link_source
from rdam.concepts.index import IndexProjection, LexicalEntry, SemanticResource, SynonymScope
from rdam.ingest.contracts.source import SourceArtifact
from tools.compile_concept_index import compile_distribution


def test_scopes_acronyms_retirement_and_domain_restriction() -> None:
    target = SemanticResource(identifier="target", label="Full Name", description="test", domain="one",
                              status="canonical", resource_type="Concept", source_path="test")
    sense = SemanticResource(identifier="sense", label="sense", description="meaning", domain="one",
                             status="canonical", resource_type="TermSense", source_path="test")
    retired = SemanticResource(identifier="retired", label="Retired", description="old", domain="two",
                               status="retired", resource_type="Concept", source_path="test")
    synonyms: tuple[tuple[str, SynonymScope], ...] = (("FN", "acronym"), ("broad", "broad"), ("narrow", "narrow"), ("old", "deprecated_form"), ("same", "exact"))
    entries = tuple(LexicalEntry(literal=literal, target="target", method="synonym", scope=scope,
        term_id="term", sense_id="sense", definition="meaning", synonym_id=scope)
        for literal, scope in synonyms)
    projection = IndexProjection(distribution_id="test", version="1.0.0", domains=("one", "two"), source_files=(),
        resources=(target, sense, retired), entries=entries + (LexicalEntry(literal="Retired", target="retired", method="label"),),
        authorable_predicates=())
    index = ConceptIndex(projection=projection, domains=projection.domains)
    source = SourceArtifact.from_text("fn FN broad narrow old same Retired", source_name="test")
    result = link_source(source, index)
    assert [m.quote for m in result.mentions] == ["FN", "broad", "narrow", "old", "same"]
    assert [m.candidates[0].reasons[0].scope for m in result.mentions] == ["acronym", "broad", "narrow", "deprecated_form", "exact"]
    assert len(link_source(source, index, options=MatchingOptions(acronym_case_sensitive=False)).mentions) == 6
    assert not link_source(source, ConceptIndex(projection=projection, domains=("two",))).mentions


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


@pytest.mark.parametrize("mutation", ["duplicate", "dangling"])
def test_invalid_authored_terminology_fails(distribution: Path, mutation: str) -> None:
    projection = ConceptIndex.load().projection
    entry = next(entry for entry in projection.entries if entry.method == "term")
    sense = next(resource for resource in projection.resources if resource.identifier == entry.sense_id)
    path = distribution / sense.source_path
    text = path.read_text()
    if mutation == "dangling":
        text = text.replace(f"denotes: {entry.target}", "denotes: missing:canonical-target", 1)
    else:
        text = text.replace(f"id: {entry.sense_id}", f"id: {entry.target}", 1)
    assert text != path.read_text(), "mutation must change actual authoritative record"
    path.write_text(text)
    with pytest.raises(ValueError, match="dangling|duplicate"):
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

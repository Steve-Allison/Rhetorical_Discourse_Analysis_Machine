"""Public lexical operations and causal evidence failures."""

from pathlib import Path

import pytest

from rdam.concepts import (
    CandidateSpan, ConceptIndex, ConceptLinkResult, link_inventory, link_source,
    resolve_candidates, validate_result,
)
from rdam.concepts.index import IndexProjection, LexicalEntry, SemanticResource
from rdam.ingest.contracts.preparation import ContentInventory
from rdam.ingest.contracts.source import SourceArtifact
from rdam.ingest.prepare import prepare_source
from tools.compile_concept_index import compile_distribution


def make_index(*labels: str) -> ConceptIndex:
    resources = tuple(SemanticResource(identifier=f"test:{i}", label=label, description=label,
                                     domain="test", status="canonical", resource_type="Concept", source_path="test.json")
                      for i, label in enumerate(labels))
    projection = IndexProjection(distribution_id="test:distribution", version="1.0.0", domains=("test",),
                                 source_files=(), resources=resources,
                                 entries=tuple(LexicalEntry(literal=r.label, target=r.identifier, method="label") for r in resources),
                                 authorable_predicates=())
    return ConceptIndex(projection=projection, domains=("test",))


def _inventory(text: str) -> ContentInventory:
    return ContentInventory.from_preparation(prepare_source(SourceArtifact.from_text(text, source_name="test")))


def test_real_packaged_central_and_repeated_evidence() -> None:
    index = ConceptIndex.load()
    assert len(index.domains) == 8
    result = link_source(SourceArtifact.from_text("Adobe Analytics. Adobe Analytics.", source_name="test"), index)
    mentions = [m for m in result.mentions if any(c.resource.identifier == "coe:entity/adobe/analytics" for c in m.candidates)]
    assert [(m.start, m.end) for m in mentions] == [(0, 15), (17, 32)]
    assert len({m.occurrence_id for m in mentions}) == 2
    assert {reason.method for reason in mentions[0].candidates[0].reasons} == {"label", "term"}
    assert ConceptLinkResult.model_validate_json(result.model_dump_json()) == result


def test_unicode_offsets_overlaps_whitespace_boundaries_and_ambiguity() -> None:
    index = make_index("Straße", "café", "new york", "york", "york", "s", "C++")
    result = link_inventory(_inventory("STRASSE cafe\u0301 NEW\n  YORK yorkshire ß C++"), index)
    assert [(m.quote, m.resolution) for m in result.mentions] == [
        ("STRASSE", "unique"), ("cafe\u0301", "unique"), ("NEW\n  YORK", "unique"),
        ("YORK", "ambiguous"), ("C++", "unique"),
    ]
    assert all(s.text[m.start:m.end] == m.quote for m in result.mentions for s in result.surfaces if s.item_id == m.item_id)


def test_unknown_supplied_candidates_and_reuse_fail_closed() -> None:
    inventory = _inventory("Known unknown")
    index = make_index("Known")
    scanned = link_inventory(inventory, index)
    surface = scanned.surfaces[0]
    span = CandidateSpan(item_id=surface.item_id, field_pointer=surface.field_pointer, start=6, end=13, quote="unknown")
    resolved = resolve_candidates(inventory, index, (span,))
    assert resolved.mentions[0].resolution == "unmapped"
    validate_result(resolved, inventory, index)
    with pytest.raises(ValueError, match="stale"):
        validate_result(resolved, _inventory("Known changed"), index)
    with pytest.raises(ValueError, match="stale"):
        validate_result(resolved, inventory, make_index("Known", "unknown"))
    with pytest.raises(ValueError, match="exact source"):
        resolve_candidates(inventory, index, (CandidateSpan(item_id=surface.item_id, field_pointer=surface.field_pointer,
                                                          start=6, end=13, quote="changed"),))
    data = resolved.model_dump()
    data["mentions"][0]["quote"] = "changed"
    with pytest.raises(ValueError, match="exact surface"):
        ConceptLinkResult.model_validate(data)


def test_domains_and_duplicate_identifier_rejected() -> None:
    with pytest.raises(ValueError, match="unknown ontology domains"):
        ConceptIndex.load(domains=("missing",))
    projection = make_index("one").projection
    with pytest.raises(ValueError, match="duplicate ontology"):
        IndexProjection.model_validate({**projection.model_dump(exclude={"content_digest"}), "resources": projection.resources * 2})


def test_manifest_compiler_detects_missing_distribution(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        compile_distribution(tmp_path)

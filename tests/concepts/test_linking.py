"""Public Stage 1 lexical operations and causal evidence failures."""

from pathlib import Path

import pytest

from rdam.concepts import (
    CandidateSpan,
    ConceptIndex,
    ConceptLinkResult,
    link_inventory,
    link_source,
    resolve_candidates,
    validate_result,
)
from rdam.concepts.index import IndexProjection, LexicalEntry, SemanticResource
from rdam.ingest.contracts.preparation import ContentInventory
from rdam.ingest.contracts.source import SourceArtifact
from rdam.ingest.prepare import prepare_source
from tools.compile_concept_index import compile_distribution


def make_index(*labels: str) -> ConceptIndex:
    resources = tuple(
        SemanticResource(
            curie=f"coe:C{90001 + i:05d}",
            pref_label=f"{label} ({i})",
            definition=label,
            collection_name="offerings",
            status="active",
        )
        for i, label in enumerate(labels)
    )
    entries = tuple(
        LexicalEntry(
            curie=resource.curie,
            pref_label=resource.pref_label,
            collection_name="offerings",
            surface=labels[i],
            match_policy="unambiguous",
        )
        for i, resource in enumerate(resources)
    )
    projection = IndexProjection(
        distribution_id="https://steve-allison.github.io/Central_Configs/v5/schema/coe",
        version="5.0.0",
        domains=("offerings",),
        resources=resources,
        entries=entries,
    )
    return ConceptIndex(projection=projection, domains=("offerings",))


def _inventory(text: str) -> ContentInventory:
    return ContentInventory.from_preparation(prepare_source(SourceArtifact.from_text(text, source_name="test")))


def test_real_packaged_central_and_repeated_evidence() -> None:
    index = ConceptIndex.load()
    assert len(index.domains) == 10
    text = "Adobe Analytics. Adobe Analytics. In Adobe architectures, AEM uses RTCDP and Photoshop, not rtcdp."
    result = link_source(SourceArtifact.from_text(text, source_name="test"), index)
    mentions = [m for m in result.mentions if m.quote == "Adobe Analytics"]
    assert [(m.start, m.end) for m in mentions] == [(0, 15), (17, 32)]
    assert len({m.occurrence_id for m in mentions}) == 2
    assert mentions[0].curie == "coe:C01007"
    assert mentions[0].candidate_curies == ("coe:C01007",)
    assert mentions[0].ambiguous is False
    by_quote = {m.quote: m for m in result.mentions}
    assert by_quote["AEM"].curie == "coe:C01014"
    assert by_quote["AEM"].candidates[0].reasons[0].match_policy == "context_anchored"
    assert by_quote["RTCDP"].curie == "coe:C01004"
    assert by_quote["RTCDP"].candidates[0].reasons[0].match_policy == "case_exact"
    assert "rtcdp" not in by_quote, "case_exact acronyms match case-sensitively by default"
    assert by_quote["Photoshop"].curie == "coe:C01111"
    assert ConceptLinkResult.model_validate_json(result.model_dump_json()) == result


def test_boundaries_overlaps_ambiguity_and_llm_disambiguation() -> None:
    resources = (
        SemanticResource(curie="coe:C90001", pref_label="New York", definition="d", collection_name="offerings"),
        SemanticResource(curie="coe:C90002", pref_label="York A", definition="d", collection_name="offerings"),
        SemanticResource(curie="coe:C90003", pref_label="York B", definition="d", collection_name="offerings"),
        SemanticResource(curie="coe:C90004", pref_label="Express", definition="d", collection_name="offerings"),
        SemanticResource(curie="coe:C90005", pref_label="Commerce", definition="d", collection_name="offerings"),
    )
    entries = (
        LexicalEntry(curie="coe:C90001", pref_label="New York", collection_name="offerings", surface="New York"),
        LexicalEntry(curie="coe:C90002", pref_label="York A", collection_name="offerings", surface="York"),
        LexicalEntry(curie="coe:C90003", pref_label="York B", collection_name="offerings", surface="York"),
        LexicalEntry(curie="coe:C90004", pref_label="Express", collection_name="offerings", surface="Express"),
        LexicalEntry(
            curie="coe:C90005",
            pref_label="Commerce",
            collection_name="offerings",
            surface="Commerce",
            requires_llm_disambiguation=True,
        ),
    )
    projection = IndexProjection(
        distribution_id="https://steve-allison.github.io/Central_Configs/v5/schema/coe",
        version="5.0.0",
        domains=("offerings",),
        resources=resources,
        entries=entries,
    )
    index = ConceptIndex(projection=projection, domains=("offerings",))
    result = link_inventory(
        _inventory("NEW YORK YORK yorkshire Express.js e-commerce Commerce"),
        index,
    )
    assert [(m.quote, m.resolution, m.curie, m.candidate_curies, m.ambiguous) for m in result.mentions] == [
        ("NEW YORK", "unique", "coe:C90001", ("coe:C90001",), False),
        ("YORK", "ambiguous", None, ("coe:C90002", "coe:C90003"), True),
        ("Commerce", "ambiguous", None, ("coe:C90005",), True),
    ]
    assert all(
        s.text[m.start:m.end] == m.quote
        for m in result.mentions
        for s in result.surfaces
        if s.item_id == m.item_id
    )


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

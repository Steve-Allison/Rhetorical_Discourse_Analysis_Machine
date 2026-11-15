"""Golden proper-noun entity-linking and NIL-abstention benchmark against Central_Configs v5.0.0."""

from pathlib import Path
from typing import Any, cast

import pytest
import yaml

from rdam.concepts import ConceptIndex, link_source
from rdam.concepts.linker import scan_text_mentions
from rdam.ingest.contracts.source import SourceArtifact

_GOLDEN_PATH = Path(__file__).parents[3] / "Central_Configs/tests/golden_grounding.yaml"


def _load_golden_cases() -> list[dict[str, Any]]:
    raw = yaml.safe_load(_GOLDEN_PATH.read_bytes())
    assert isinstance(raw, dict)
    doc = cast(dict[str, Any], raw)
    assert doc["benchmark_id"] == "coe:benchmark/golden_grounding_v5"
    assert str(doc["version"]) == "5.0.0"
    raw_cases = doc["cases"]
    assert isinstance(raw_cases, list)
    cases = cast(list[dict[str, Any]], raw_cases)
    assert len(cases) == 200
    return cases


def test_golden_grounding_200_benchmark_parity() -> None:
    index = ConceptIndex.load()
    cases = _load_golden_cases()

    llm_rule_curies = {
        entry.curie
        for entry in index.projection.entries
        if entry.requires_llm_disambiguation
    }
    assert llm_rule_curies, "expected Central_Configs v5.0.0 to declare Stage 2 LLM disambiguation rules"

    deterministic_count = 0
    nil_count = 0
    llm_disambiguation_count = 0
    failures: list[str] = []

    for case in cases:
        case_id = str(case["id"])
        category = str(case["category"])
        text = str(case["text"])
        expected_curies = sorted(str(c) for c in case["expected_curies"])

        result = link_source(SourceArtifact.from_text(text, source_name=case_id), index)
        unique_curies = sorted({m.curie for m in result.mentions if m.curie is not None})
        ambiguous_mentions = [m for m in result.mentions if m.ambiguous]
        all_candidate_curies = sorted({c for m in result.mentions for c in m.candidate_curies})

        if category.startswith("nil_"):
            nil_count += 1

        if ambiguous_mentions:
            llm_disambiguation_count += 1
            for mention in ambiguous_mentions:
                assert mention.curie is None
                assert mention.resolution == "ambiguous"
                assert mention.requires_llm_disambiguation or len(mention.candidate_curies) > 1
            if sorted(all_candidate_curies) != expected_curies:
                failures.append(
                    f"{case_id} ({category}): expected candidate_curies={expected_curies}, "
                    f"got {all_candidate_curies} (unique={unique_curies})"
                )
            # Substrate scan_text_mentions emits only deterministic hard links, never ambiguous candidates.
            scanned_curies = sorted({curie for _, _, curie in scan_text_mentions(text, index)})
            if scanned_curies != unique_curies:
                failures.append(
                    f"{case_id} ({category}): scan_text_mentions={scanned_curies} != unique_curies={unique_curies}"
                )
        else:
            deterministic_count += 1
            if unique_curies != expected_curies:
                failures.append(
                    f"{case_id} ({category}): expected deterministic curies={expected_curies}, got {unique_curies}"
                )
            scanned_curies = sorted({curie for _, _, curie in scan_text_mentions(text, index)})
            if scanned_curies != expected_curies:
                failures.append(
                    f"{case_id} ({category}): scan_text_mentions={scanned_curies} != expected={expected_curies}"
                )

    assert not failures, "\n".join(failures)
    assert nil_count == 40
    assert deterministic_count == 190
    assert llm_disambiguation_count == 10


def test_craft_rhetoric_and_discourse_firewall() -> None:
    index = ConceptIndex.load()
    forbidden_collections = {
        "story_frameworks",
        "framework_stages",
        "argument_schemes",
        "discourse_relations",
        "rhetorical_moves",
        "cognitive_principles",
        "instructional_methods",
        "visual_principles",
        "rubrics",
        "diagnostic_detectors",
    }
    assert forbidden_collections.isdisjoint(index.domains)
    for resource in index.projection.resources:
        assert not resource.curie.startswith(("coe:C06", "coe:C09"))
    with pytest.raises(ValueError, match="unknown ontology domains"):
        ConceptIndex.load(domains=("discourse_relations",))

"""Focused system serialization and private candidate-cache contract tests."""

from isanlp_rst.erst.candidates import SecondaryEdgeCandidate
from workbench.research.erst.data import CandidateRecord, HarnessCandidate
from workbench.research.erst.systems.cross_encoder import serialize_candidate


def _candidate() -> SecondaryEdgeCandidate:
    return SecondaryEdgeCandidate(
        document_id="GUM_test_document",
        source_id=1,
        target_id=2,
        source_text="Although it rained",
        target_text="we continued",
        source_char_span=(100, 118),
        target_char_span=(119, 131),
        structural_features=(0.0,) * 9,
        is_gold_edge=True,
        gold_relation="adversative-concession",
        gold_concept="Contrast",
        signal_ids=("sig_1", "sig_2"),
        signal_types=("dm", "morph"),
        signal_subtypes=("concessive", "finite"),
        compatible_relations=("adversative-concession",),
        source_head_id=1,
        target_head_id=2,
        source_head_text="Although it rained",
        target_head_text="we continued",
        source_sentence_ids=(0,),
        target_sentence_ids=(0,),
        direction="forward",
        edu_distance=1,
        primary_path=(">span",),
    )


def test_candidate_cache_round_trips_gold_fields_and_overlapping_signal_spans() -> None:
    candidate = _candidate()
    spans = ((100, 108), (104, 110))
    record = CandidateRecord.from_candidate(candidate, spans)
    restored = CandidateRecord.model_validate_json(record.model_dump_json()).to_harness_candidate()

    assert restored.candidate == candidate
    assert restored.candidate.is_gold_edge
    assert restored.candidate.gold_relation == "adversative-concession"
    assert restored.signal_char_spans == spans


def test_signal_aware_serialization_preserves_each_exact_overlapping_anchor() -> None:
    candidate = HarnessCandidate(
        candidate=_candidate(),
        signal_char_spans=((100, 108), (104, 110)),
    )

    source, target = serialize_candidate(
        candidate,
        signal_aware=True,
        include_structure_tokens=True,
    )

    assert "[source-signals=0:8,4:10]" in source
    assert "[target-signals=none]" in target
    assert "[direction=forward]" in source
    assert "[primary-path=>span]" in source


def test_text_only_serialization_contains_no_signal_or_structure_tokens() -> None:
    candidate = HarnessCandidate(
        candidate=_candidate(),
        signal_char_spans=((100, 108),),
    )

    assert serialize_candidate(
        candidate,
        signal_aware=False,
        include_structure_tokens=False,
    ) == ("Although it rained", "we continued")

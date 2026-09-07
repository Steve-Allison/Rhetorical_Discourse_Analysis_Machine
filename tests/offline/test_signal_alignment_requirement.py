"""GUM signal scores must not assume shared parser-local identifiers."""

from tests.offline.gum_validator import GumGoldValidator


def test_gold_identity_comparison_requires_explicit_signal_alignment() -> None:
    validator = GumGoldValidator()
    _, analysis, rs4 = validator.load_gold_fixture("GUM_bio_dvorak")
    assert analysis.signals
    result = validator.validate_analysis(analysis.document_id, analysis, prediction_rs4=rs4)
    assert result.signal_metrics is None
    assert result.signal_evaluation_unavailable_reason == "edge_and_token_alignment_not_verified"
    aligned = validator.validate_analysis(
        analysis.document_id, analysis, prediction_rs4=rs4, signal_identities_prealigned=True,
    )
    assert aligned.signal_evaluation_unavailable_reason is None
    assert aligned.signal_metrics is not None
    assert aligned.signal_metrics.token_f1 == 1.0

from isanlp_rst.ingest.contracts import FailureStage, ProductionIngestError


def test_failure_is_actionable_and_does_not_embed_source_text() -> None:
    error = ProductionIngestError(
        stage=FailureStage.VALIDATE,
        code="doclang_invalid",
        artifact_id="source:abc",
        item_id="xml:/doc/body/p[2]",
        expectation="current XSD and Schematron validation",
        detail="element p[2] violates the contract",
        diagnostic_counts={"inventory": 4},
    )
    payload = error.as_dict()
    assert payload["stage"] == "validate"
    assert payload["item_id"] == "xml:/doc/body/p[2]"
    assert "private paragraph" not in str(error)
    assert payload["diagnostic_counts"] == {"inventory": 4}

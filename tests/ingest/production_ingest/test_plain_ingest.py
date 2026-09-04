from rdam.ingest import ContentClass, PreparationPolicy, SourceArtifact
from rdam.ingest.policy import DEFAULT_PREPARATION_POLICY
from rdam.ingest.service import ProductionIngestor


def test_plain_text_preparation_preserves_exact_paragraph_text() -> None:
    artifact = SourceArtifact.from_text("First.\r\n\r\nSecond.", source_name="plain.txt")
    outcome = ProductionIngestor().prepare(artifact)
    assert outcome.semantic.prepared_document.text == "First.\r\n\r\nSecond."
    assert outcome.semantic_digest


def test_presegmented_edus_remain_indivisible() -> None:
    artifact = SourceArtifact.from_edus((" First ", "Second"), source_name="input.edus")
    outcome = ProductionIngestor().prepare(artifact)
    source_segments = tuple(
        segment for segment in outcome.semantic.prepared_document.segments if segment.contributing_item_ids
    )
    assert tuple(segment.text for segment in source_segments) == (" First ", "Second")


def test_whitespace_only_text_has_no_fabricated_discourse() -> None:
    artifact = SourceArtifact.from_text(" \n\t", source_name="blank.txt")
    outcome = ProductionIngestor().prepare(artifact)
    assert outcome.semantic.prepared_document.text == ""
    assert outcome.semantic.prepared_document.segments == ()


def test_named_policy_scope_is_reflected_in_plain_preparation() -> None:
    artifact = SourceArtifact.from_text("Authored but deliberately side-channelled.", source_name="plain.txt")
    policy = PreparationPolicy.model_validate(
        {
            **DEFAULT_PREPARATION_POLICY.model_dump(exclude={"semantic_digest"}),
            "primary_classes": tuple(
                content_class
                for content_class in DEFAULT_PREPARATION_POLICY.primary_classes
                if content_class is not ContentClass.PARAGRAPH
            ),
            "retained_classes": (*DEFAULT_PREPARATION_POLICY.retained_classes, ContentClass.PARAGRAPH),
        }
    )

    outcome = ProductionIngestor().prepare(artifact, policy=policy)

    assert outcome.semantic.prepared_document.text == ""
    assert len(outcome.retained_items) == 1
    assert outcome.retained_items[0].item_id == "text:document"

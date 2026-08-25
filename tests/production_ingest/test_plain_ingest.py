from isanlp_rst.ingest import ContentClass, PreparationPolicy, SourceArtifact
from isanlp_rst.ingest.policy import AUTHORED_PROSE_V1
from isanlp_rst.ingest.service import ProductionIngestor


def test_plain_text_preparation_preserves_exact_paragraph_text() -> None:
    artifact = SourceArtifact.from_text("First.\r\n\r\nSecond.", source_name="plain.txt")
    prepared = ProductionIngestor(parser=None).prepare(artifact)
    assert prepared.text == "First.\r\n\r\nSecond."
    assert prepared.semantic_digest


def test_presegmented_edus_remain_indivisible() -> None:
    artifact = SourceArtifact.from_edus((" First ", "Second"), source_name="input.edus")
    prepared = ProductionIngestor(parser=None).prepare(artifact)
    assert prepared.document.edus is not None
    assert tuple(edu.text for edu in prepared.document.edus) == (" First ", "Second")


def test_whitespace_only_text_has_no_fabricated_discourse() -> None:
    artifact = SourceArtifact.from_text(" \n\t", source_name="blank.txt")
    prepared = ProductionIngestor(parser=None).prepare(artifact)
    assert prepared.text == ""
    assert prepared.primary_item_ids == ()


def test_named_policy_scope_is_reflected_in_plain_preparation() -> None:
    artifact = SourceArtifact.from_text("Authored but deliberately side-channelled.", source_name="plain.txt")
    policy = PreparationPolicy(
        name="no_plain_paragraphs",
        version="1",
        primary_classes=tuple(
            content_class
            for content_class in AUTHORED_PROSE_V1.primary_classes
            if content_class is not ContentClass.PARAGRAPH
        ),
        side_channel_classes=(*AUTHORED_PROSE_V1.side_channel_classes, ContentClass.PARAGRAPH),
        excluded_classes=AUTHORED_PROSE_V1.excluded_classes,
    )

    prepared = ProductionIngestor(parser=None).prepare(artifact, policy=policy)

    assert prepared.text == ""
    assert prepared.primary_item_ids == ()
    assert prepared.side_channel_item_ids == ("text:document",)

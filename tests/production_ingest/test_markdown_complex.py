from isanlp_rst.ingest import SourceArtifact, SourceForm
from isanlp_rst.ingest.contracts import ContentClass
from isanlp_rst.ingest.prepare import inventory_source
from isanlp_rst.ingest.service import ProductionIngestor


def test_raw_html_is_structurally_inventoried_without_script_navigation_or_style_contamination() -> None:
    markdown = """<article><p>Authored <em>HTML</em> prose.</p><script>steal()</script><nav>Menu</nav><style>.x{}</style></article>"""
    artifact = SourceArtifact.from_bytes(
        markdown.encode(),
        source_form=SourceForm.MARKDOWN,
        source_name="html.md",
        media_type="text/markdown; charset=utf-8",
    )
    inventory, _ = inventory_source(artifact)
    prepared = ProductionIngestor(parser=None).prepare(artifact)
    assert "Authored HTML prose." in prepared.text
    assert "steal" not in prepared.text
    assert "Menu" not in prepared.text
    assert ".x" not in prepared.text
    assert ContentClass.RAW_MARKUP in {item.content_class for item in inventory}
    assert all(item.native_anchors for item in inventory)


def test_image_only_markdown_and_conversion_analysis_sections_are_not_primary() -> None:
    markdown = """# Slide title

![Image](slide.webp)

## 1. VISUAL DESCRIPTION

Machine visual description.

Authored speaker narrative.
"""
    artifact = SourceArtifact.from_bytes(
        markdown.encode(),
        source_form=SourceForm.MARKDOWN,
        source_name="converted.md",
        media_type="text/markdown; charset=utf-8",
    )
    prepared = ProductionIngestor(parser=None).prepare(artifact)
    assert "Slide title" in prepared.text
    assert "Authored speaker narrative." in prepared.text
    assert "slide.webp" not in prepared.text
    assert "Machine visual description." not in prepared.text

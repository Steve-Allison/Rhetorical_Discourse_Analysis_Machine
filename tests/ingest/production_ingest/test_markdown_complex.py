from rdam.rst.ingest import SourceArtifact, SourceForm
from rdam.rst.ingest.contracts import ContentClass
from rdam.rst.ingest.prepare import inventory_source
from rdam.rst.ingest.service import ProductionIngestor


def test_raw_html_is_structurally_inventoried_without_script_navigation_or_style_contamination() -> None:
    markdown = """<article><p>Authored <em>HTML</em> prose.</p><script>steal()</script><nav>Menu</nav><style>.x{}</style></article>"""
    artifact = SourceArtifact.from_bytes(
        markdown.encode(),
        source_form=SourceForm.MARKDOWN,
        source_name="html.md",
        media_type="text/markdown; charset=utf-8",
    )
    inventory, _ = inventory_source(artifact)
    outcome = ProductionIngestor().prepare(artifact)
    text = outcome.semantic.prepared_document.text
    assert "Authored HTML prose." in text
    assert "steal" not in text
    assert "Menu" not in text
    assert ".x" not in text
    assert ContentClass.RAW_MARKUP in {item.classification for item in inventory}
    assert all(item.anchors for item in inventory)


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
    outcome = ProductionIngestor().prepare(artifact)
    text = outcome.semantic.prepared_document.text
    assert "Slide title" in text
    assert "Authored speaker narrative." in text
    assert "slide.webp" not in text
    assert "Machine visual description." not in text

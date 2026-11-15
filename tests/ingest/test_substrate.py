"""Unit and integration tests for unified dclq/DocLang substrate and single-turn quote grounding."""

import pytest

from rdam._grounding import (
    GroundingCollector,
    QuoteRef,
    find_all_occurrences,
    resolve_quote,
    shard_substrate,
)
from rdam.ingest import ProductionIngestor, SourceArtifact, SourceForm
from rdam.ingest.contracts.preparation import ContentInventory
from rdam.ingest.projection import project
from rdam.ingest.requirements import SUBSTANTIVE_CLASSES, llm_requirement
from rdam.ingest.substrate import (
    build_linguistic_substrate,
    render_cached_source_prefix,
)


_UNIFIED_DOCLANG = b"""<doclang xmlns="https://www.doclang.ai/ns/v0" version="0.9">
  <head>
    <summary>Operational provenance that must never enter substantive discourse.</summary>
  </head>
  <page_header>CONFIDENTIAL HEADER CHROME</page_header>
  <heading level="1">Executive Case for Renewables</heading>
  <text>Because grid storage costs fell by 40%, utility solar is now dispatchable. Therefore, we recommend retiring coal plants.</text>
  <picture>
    <label value="logo"/>
    <description>Decorative corporate wordmark</description>
  </picture>
  <picture>
    <label value="bar_chart"/>
    <description>Bar chart showing battery pack prices dropping from 140 USD/kWh to 84 USD/kWh.</description>
    <custom>
      <docling_machine__vlm_metadata>operational_vlm_provenance</docling_machine__vlm_metadata>
    </custom>
  </picture>
  <table>
    <ched/>Fuel<ched/>LCOE<nl/>
    <fcel/>Solar + Storage<fcel/>42 USD/MWh<nl/>
  </table>
  <footnote>Presenter note: emphasize reliability during evening peak.</footnote>
</doclang>"""


def _valid_unified_doclang() -> bytes:
    return _UNIFIED_DOCLANG


def test_unified_stream_retains_substantive_vlm_tables_and_notes_while_pruning_chrome() -> None:
    artifact = SourceArtifact.from_bytes(
        _valid_unified_doclang(),
        source_form=SourceForm.DOCLANG_XML,
        source_name="unified.dclg",
    )
    prepared_outcome = ProductionIngestor().prepare(artifact)
    inventory = ContentInventory.from_preparation(prepared_outcome)
    requirement = llm_requirement(
        "rdam/substantive-stream-v2",
        SUBSTANTIVE_CLASSES,
        requires_speaker_identity=False,
    )
    projection = project(inventory, requirement)
    substrate = build_linguistic_substrate(projection.prepared_document, inventory)

    assert "CONFIDENTIAL HEADER CHROME" not in substrate.text
    assert "Operational provenance" not in substrate.text
    assert "operational_vlm_provenance" not in substrate.text
    assert "Decorative corporate wordmark" not in substrate.text

    assert "Executive Case for Renewables" in substrate.text
    assert "Because grid storage costs fell by 40%" in substrate.text
    assert "Bar chart showing battery pack prices dropping" in substrate.text
    assert "Solar + Storage" in substrate.text
    assert "Presenter note: emphasize reliability" in substrate.text

    xpaths = [u.dclq_xpath for u in substrate.units if u.dclq_xpath is not None]
    assert "/d:doclang/d:heading[1]" in xpaths
    assert "/d:doclang/d:text[1]" in xpaths
    assert any(u.table_cell == (1, 0) for u in substrate.units)

    signal_kinds = {sig.kind for sig in substrate.signals}
    assert "discourse_connective" in signal_kinds
    assert "speech_act_cue" in signal_kinds

    prefix = render_cached_source_prefix(substrate)
    assert prefix.startswith("<source_document>\n[u_0 | ")
    assert "</source_document>" in prefix
    assert "<linguistic_signals>" in prefix
    # Cached prefix is deterministic and memoized across repeated calls
    assert render_cached_source_prefix(substrate) == prefix


def test_quote_grounding_resolves_occurrences_and_emits_actionable_retry_hints() -> None:
    text = "Alpha claims X. Beta disputes X. Alpha claims X."
    assert find_all_occurrences(text, "Alpha claims X.") == ((0, 15), (33, 48))

    span1 = resolve_quote(QuoteRef(quote="Alpha claims X.", occurrence=1), text)
    span2 = resolve_quote(QuoteRef(quote="Alpha claims X.", occurrence=2), text)
    assert (span1.start, span1.end) == (0, 15)
    assert (span2.start, span2.end) == (33, 48)

    with pytest.raises(ValueError, match="occurrence=3"):
        resolve_quote(QuoteRef(quote="Alpha claims X.", occurrence=3), text)

    with pytest.raises(ValueError, match="Case mismatch"):
        resolve_quote(QuoteRef(quote="alpha claims x.", occurrence=1), text)

    with pytest.raises(ValueError, match="unit metadata headers"):
        resolve_quote(QuoteRef(quote="[u_0 | kind=paragraph] Alpha claims X.", occurrence=1), text)

    collector = GroundingCollector(text)
    assert collector.resolve(QuoteRef(quote="Beta disputes X."), field_name="arg1") is not None
    assert collector.resolve(QuoteRef(quote="Nonexistent quote"), field_name="arg2") is None
    assert collector.has_errors
    with pytest.raises(ValueError, match="Fix all 1 validation issue"):
        collector.raise_if_errors()


def test_section_aligned_substrate_sharding_maps_back_to_global_offsets() -> None:
    xml = (
        '<doclang xmlns="https://www.doclang.ai/ns/v0" version="0.9">'
        "<heading level=\"1\">Section One</heading>"
        + "".join(f"<text>Paragraph {i} in section one carries detailed analytical prose.</text>" for i in range(6))
        + "<heading level=\"1\">Section Two</heading>"
        + "".join(f"<text>Paragraph {i} in section two presents distinct empirical data.</text>" for i in range(6))
        + "</doclang>"
    ).encode("utf-8")
    artifact = SourceArtifact.from_bytes(xml, source_form=SourceForm.DOCLANG_XML, source_name="sharded.dclg")
    outcome = ProductionIngestor().prepare(artifact)
    inventory = ContentInventory.from_preparation(outcome)
    projection = project(
        inventory,
        llm_requirement("rdam/substantive-stream-v2", SUBSTANTIVE_CLASSES, requires_speaker_identity=False),
    )
    substrate = build_linguistic_substrate(projection.prepared_document, inventory)
    shards = shard_substrate(substrate, max_chars=300)
    assert len(shards) >= 2
    for shard in shards:
        target = shard.substrate.units[-1].text
        local = resolve_quote(QuoteRef(quote=target), shard.substrate.text)
        mapped = shard.to_global_span(local)
        assert substrate.text[mapped.start : mapped.end] == target

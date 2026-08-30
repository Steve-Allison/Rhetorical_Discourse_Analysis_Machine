"""Machine-readable public-surface authority reconciliation."""

from isanlp_rst.ingest.public_surface import load_public_surface, reconcile_public_surface
from tools.production_boundary.public_surface import public_surface_parity


def test_public_surface_manifest_is_versioned_unique_and_reconciled() -> None:
    inventory = load_public_surface()
    assert inventory.contract_version == "2.0.0"
    assert len({entry.qualified_name for entry in inventory.entries}) == len(inventory.entries)

    report = reconcile_public_surface(inventory)
    assert report.missing_exports == ()
    assert report.unclassified_exports == ()
    assert report.signature_mismatches == ()
    assert report.enum_mismatches == ()
    assert report.schema_mismatches == ()
    assert report.documentation_mismatches == ()
    assert public_surface_parity()


def test_required_v2_boundary_members_are_supported() -> None:
    inventory = load_public_surface()
    supported = {
        entry.qualified_name
        for entry in inventory.entries
        if entry.status.value == "supported"
    }
    assert {
        "isanlp_rst.Parser.analyse_document",
        "isanlp_rst.ingest.ProductionIngestor.prepare",
        "isanlp_rst.ingest.ProductionIngestor.analyse",
        "isanlp_rst.ingest.describe_capabilities",
        "isanlp_rst.ingest.serialize_contract",
        "isanlp_rst.ingest.load_contract",
    } <= supported


def test_public_surface_excludes_scientific_and_archived_internal_types() -> None:
    names = {
        entry.qualified_name.casefold()
        for entry in load_public_surface().entries
        if entry.status.value == "supported"
    }
    forbidden = (
        "tensor",
        "embedding",
        "activation",
        "traininglabel",
        "workbench",
        "dmrst",
        "unirst",
        "unrestrictedchart",
    )
    assert not any(marker in name for marker in forbidden for name in names)

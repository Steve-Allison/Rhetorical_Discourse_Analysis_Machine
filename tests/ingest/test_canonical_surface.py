"""Source preparation has one machine-owned import surface."""

from importlib.util import find_spec

from rdam.ingest.public_surface import load_public_surface
import rdam.machine as orchestration


def test_historical_ingest_module_is_absent() -> None:
    assert find_spec("rdam.rst.ingest") is None


def test_orchestration_has_no_assembly_forwarder() -> None:
    assert not hasattr(orchestration, "production_machine")


def test_manifest_names_only_canonical_ingest_imports() -> None:
    authority = load_public_surface()
    imports = tuple(entry.public_import for entry in authority.entries if entry.public_import is not None)
    assert "rdam.ingest:ProductionIngestor" in imports
    assert not any(name.startswith("rdam.rst.ingest") for name in imports)

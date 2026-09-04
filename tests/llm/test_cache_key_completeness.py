"""Every analytical identity component affects the exact cache address."""

from rdam import ProviderRequest, SourceIdentity, Sha256Identity, semantic_sha256, Technique
from rdam._provider_provenance import provider_provenance
from rdam.ingest import ProductionIngestor, SourceArtifact
from rdam.ingest.contracts.preparation import ContentInventory, ContentRequirement
from rdam.ingest.projection import project
from rdam.machine import _cache_key
from rdam.toulmin.provider import ToulminProvider


def test_instruction_changes_change_provenance_and_cache_key() -> None:
    first = provider_provenance(package="rdam.toulmin", licence="test", instructions="first")
    second = provider_provenance(package="rdam.toulmin", licence="test", instructions="second")
    assert first.source_revision != second.source_revision
    declaration = ToulminProvider().declaration
    request = ProviderRequest(source=SourceIdentity.from_text("text"), text="text", structured_input=None)
    assert _cache_key(Technique.TOULMIN, declaration.model_copy(update={"provenance": first}), request) != _cache_key(
        Technique.TOULMIN, declaration.model_copy(update={"provenance": second}), request,
    )


def test_all_six_identity_elements_are_independently_covered() -> None:
    provider = ToulminProvider()
    declaration = provider.declaration
    inventory = ContentInventory.from_preparation(ProductionIngestor().prepare(SourceArtifact.from_text("Evidence.", source_name="test")))
    projection = project(inventory, provider.content_requirement)
    request = ProviderRequest(source=SourceIdentity.from_text("Evidence."), text="Evidence.", structured_input=None, projection=projection)
    key = _cache_key(Technique.TOULMIN, declaration, request)
    changed_requirement = ContentRequirement.model_validate({**provider.content_requirement.model_dump(exclude={"semantic_digest"}), "normalization": "unicode_nfc"})
    cases = (
        (declaration, request.model_copy(update={"source": SourceIdentity.from_text("Other.")})),
        (declaration, request.model_copy(update={"projection": project(inventory, changed_requirement)})),
        (declaration.model_copy(update={"provider_id": "different"}), request),
        (declaration.model_copy(update={"contract_version": declaration.contract_version.model_copy(update={"root": "9.0.0"})}), request),
        (declaration.model_copy(update={"provenance": declaration.provenance.model_copy(update={"model_identity": "different"})}), request),
        (declaration.model_copy(update={"instructions_identity": Sha256Identity(hex_digest=semantic_sha256("different"))}), request),
    )
    assert all(_cache_key(Technique.TOULMIN, changed, changed_request) != key for changed, changed_request in cases)

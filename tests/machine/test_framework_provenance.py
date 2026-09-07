"""New provenance identifies its authority; historical absence is never backfilled."""

import hashlib
from importlib import resources
import json

from rdam._contract_types import ProviderProvenance
from rdam._provider_provenance import provider_provenance
from rdam.frameworks import FRAMEWORK_SCHEME, framework_authority


def test_provider_provenance_binds_actual_projection_and_source() -> None:
    raw = resources.files("rdam").joinpath("resources/framework-identities.json").read_bytes()
    payload = json.loads(raw)
    provenance = provider_provenance(package="rdam", licence="MIT")
    authority = provenance.framework_authority
    assert authority is not None
    assert authority.scheme == FRAMEWORK_SCHEME
    assert authority.source_identity.hex_digest == payload["source_sha256"]
    assert authority.projection_identity.hex_digest == hashlib.sha256(raw).hexdigest()
    assert ProviderProvenance.model_validate_json(provenance.model_dump_json()) == provenance


def test_historical_provenance_does_not_acquire_current_authority() -> None:
    payload = {"package": "rdam", "version": "6.0.0", "source_revision": None,
               "model_identity": None, "licence": "MIT"}
    loaded = ProviderProvenance.model_validate(payload)
    assert loaded.framework_authority is None
    assert loaded.model_dump(mode="json") == payload
    assert framework_authority() is not None
    assert loaded.model_dump(mode="json") == payload

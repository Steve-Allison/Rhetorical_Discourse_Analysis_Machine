"""A valid digest must not certify a mathematically false native payload."""

import json
import subprocess
import sys

from pydantic import ValidationError
import pytest

from rdam.contracts import NativeTechniqueResult, SourceIdentity
from rdam.serialization import UnsupportedRecordError, load, load_native_payload, serialize
from rdam.frameworks import Technique
from tests.dung.test_output import mutual_attack


def native_bytes(
    *, corrupt: bool = False, version: str = "1.0.0", formalism: str = "dung_extensions",
    technique: Technique = Technique.DUNG,
) -> bytes:
    payload = mutual_attack().model_dump(mode="json")
    if corrupt:
        payload["extensions"]["preferred"] = []
    record = NativeTechniqueResult.model_validate_json(json.dumps({
        "technique": technique.value, "formalism_id": formalism, "provider_id": "test/native",
        "provider_contract_version": version,
        "source": SourceIdentity.from_text("Supplied framework").model_dump(mode="json"),
        "payload": payload,
        "provenance": {"package": "test", "version": "1.0.0", "licence": "MIT"},
    }))
    return serialize(record)


def test_native_loader_validates_and_preserves_mathematical_result() -> None:
    encoded = native_bytes()
    assert load_native_payload(encoded) == mutual_attack()
    assert serialize(load(encoded)) == encoded


def test_resealed_wrong_extensions_fail_native_validation() -> None:
    encoded = native_bytes(corrupt=True)
    assert isinstance(load(encoded), NativeTechniqueResult)
    with pytest.raises(ValidationError, match="extensions must reproduce"):
        load_native_payload(encoded)


def test_future_provider_version_is_not_read_as_current() -> None:
    with pytest.raises(UnsupportedRecordError, match="unsupported schema"):
        load_native_payload(native_bytes(version="99.0.0"))


def test_erst_formalism_under_rst_boundary_uses_erst_validation() -> None:
    from rdam.ingest.contracts.base import WRITE_CONTRACT_VERSION
    from rdam.ingest.contracts.inference import OutputFormalism

    # A Dung payload is deliberately invalid: it must reach the eRST schema,
    # rather than fail dispatch or be accepted as an opaque native envelope.
    encoded = native_bytes(
        technique=Technique.RST, formalism=OutputFormalism.ERST_GRAPH.value,
        version=WRITE_CONTRACT_VERSION,
    )
    with pytest.raises(ValidationError) as failure:
        load_native_payload(encoded)
    assert failure.value.title == "ErstOutput"


@pytest.mark.parametrize("technique", tuple(Technique))
def test_wrong_formalism_is_rejected_before_native_interpretation(technique: Technique) -> None:
    with pytest.raises(UnsupportedRecordError, match="requires formalism"):
        load_native_payload(native_bytes(formalism="unregistered_formalism", technique=technique))


def test_dung_native_validation_does_not_load_unrelated_techniques() -> None:
    process = subprocess.run(
        [sys.executable, "-c", """
import sys
from tests.machine.test_native_loading import native_bytes
from rdam.serialization import load_native_payload
load_native_payload(native_bytes())
for prefix in ('torch', 'rdam.rst', 'rdam.pdtb', 'rdam.sdrt', 'rdam.toulmin', 'rdam.walton', 'rdam.ibis'):
    assert not any(name == prefix or name.startswith(prefix + '.') for name in sys.modules), prefix
"""], capture_output=True, text=True, check=False,
    )
    assert process.returncode == 0, process.stderr

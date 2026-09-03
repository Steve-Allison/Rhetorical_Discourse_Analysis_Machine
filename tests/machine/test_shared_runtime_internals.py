"""Branch-complete tests for the private Feature 018 runtime kernels."""

from dataclasses import dataclass
from datetime import datetime, UTC
from enum import StrEnum
import json
from pathlib import Path, PurePosixPath
from types import SimpleNamespace
from typing import Any

from pydantic import BaseModel
import pytest

from rdam import Machine, NativeTechniqueResult, ProviderProvenance, SemanticVersion, SourceIdentity, Technique, serialize
from rdam import _provenance
from rdam._canonical import (
    canonical_json_bytes,
    json_projection,
    semantic_sha256,
    sha256_bytes,
    sha256_file,
    validate_ijson_value,
)
from rdam._immutable_json import freeze_json
from rdam._provider_provenance import package_version, provider_failure, require_llm_text, source_identity
from rdam._result_cache import ResultCache, revision_is_cacheable
from rdam.contracts import Retryability


class Choice(StrEnum):
    YES = "yes"


class Model(BaseModel):
    value: int


@dataclass(frozen=True)
class Data:
    value: str


def test_canonical_projection_covers_every_supported_value_and_is_stable(tmp_path: Path) -> None:
    value = {
        "model": Model(value=1),
        "data": Data(value="x"),
        "enum": Choice.YES,
        "time": datetime(2026, 1, 2, tzinfo=UTC),
        "path": PurePosixPath("a/b"),
        "bytes": b"\x00\xff",
        "tuple": (True, None, 2.5),
    }
    projected = json_projection(value)
    assert projected == {
        "model": {"value": 1},
        "data": {"value": "x"},
        "enum": "yes",
        "time": "2026-01-02T00:00:00+00:00",
        "path": "a/b",
        "bytes": "00ff",
        "tuple": [True, None, 2.5],
    }
    assert semantic_sha256(value) == sha256_bytes(canonical_json_bytes(value))
    payload = tmp_path / "payload.bin"
    payload.write_bytes(b"a" * (1024 * 1024 + 1))
    assert sha256_file(payload) == sha256_bytes(payload.read_bytes())


@pytest.mark.parametrize(
    "value",
    (
        {1: "not a string key"},
        object(),
        "\ud800",
        9_007_199_254_740_992,
        float("inf"),
        {"nested": object()},
    ),
)
def test_canonical_kernel_rejects_values_outside_ijson(value: object) -> None:
    with pytest.raises(TypeError, match="canonical mappings|unsupported canonical|outside the JSON data model") if not isinstance(
        value, str | int | float
    ) else pytest.raises(ValueError, match="I-JSON|interoperable|non-finite"):
        canonical_json_bytes(value)


def test_frozen_json_rejects_non_json_values() -> None:
    with pytest.raises(TypeError, match="outside the JSON data model"):
        freeze_json(object())


def test_ijson_validator_independently_rejects_bad_keys_and_unknown_values() -> None:
    with pytest.raises(TypeError, match="keys must be strings"):
        validate_ijson_value({1: "bad"})
    with pytest.raises(TypeError, match="outside the JSON data model"):
        validate_ijson_value(object())


def _build_payload() -> dict[str, object]:
    return {
        "schema_name": "isanlp_rst.build_provenance",
        "schema_version": "1.0.0",
        "package_name": "rdam",
        "package_version": "6.0.0",
        "production_contract": "isanlp_rst.production",
        "production_contract_version": "2.0.0",
        "source_commit": "a" * 40,
        "source_tree": "clean",
        "source_archive_sha256": "b" * 64,
        "source_date_epoch": 1,
        "build_input_sha256": "c" * 64,
        "build_tool": "hatchling",
    }


class FakeResource:
    def __init__(self, payload: dict[str, object] | None) -> None:
        self.payload = payload

    def joinpath(self, _name: str) -> "FakeResource":
        return self

    def is_file(self) -> bool:
        return self.payload is not None

    def read_text(self, *, encoding: str) -> str:
        assert encoding == "utf-8"
        assert self.payload is not None
        return json.dumps(self.payload)


@pytest.fixture(autouse=True)
def clear_provenance_caches() -> None:
    _provenance.installed_package_version.cache_clear()
    _provenance.load_build_provenance.cache_clear()
    _provenance.resolve_source_revision.cache_clear()
    package_version.cache_clear()


def test_installed_version_and_absent_build_provenance_fallbacks(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(_provenance, "version", lambda _name: (_ for _ in ()).throw(_provenance.PackageNotFoundError()))
    assert _provenance.installed_package_version() == "unknown"
    monkeypatch.setattr(_provenance.resources, "files", lambda _name: FakeResource(None))
    assert _provenance.load_build_provenance() is None


def test_build_provenance_must_be_an_object(monkeypatch: pytest.MonkeyPatch) -> None:
    resource = FakeResource({})
    resource.read_text = lambda *, encoding: "[]"
    monkeypatch.setattr(_provenance.resources, "files", lambda _name: resource)
    with pytest.raises(ValueError, match="unexpected schema"):
        _provenance.load_build_provenance()


def test_valid_packaged_provenance_supplies_source_revision(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = _build_payload()
    monkeypatch.setattr(_provenance.resources, "files", lambda _name: FakeResource(payload))
    monkeypatch.setattr(_provenance, "installed_package_version", lambda: "6.0.0")
    assert _provenance.load_build_provenance() == payload
    assert _provenance.resolve_source_revision() == "a" * 40


@pytest.mark.parametrize(
    ("mutation", "message"),
    (
        (lambda value: value.pop("build_tool"), "unexpected schema"),
        (lambda value: value.update(schema_name="wrong"), "wrong contract"),
        (lambda value: value.update(schema_version="9.0.0"), "unsupported version"),
        (lambda value: value.update(package_name="wrong"), "wrong package"),
        (lambda value: value.update(package_version="9.0.0"), "contradicts installed metadata"),
        (lambda value: value.update(build_tool=[]), "strings or integers"),
    ),
)
def test_invalid_packaged_provenance_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
    mutation: Any,
    message: str,
) -> None:
    payload = _build_payload()
    mutation(payload)
    monkeypatch.setattr(_provenance.resources, "files", lambda _name: FakeResource(payload))
    monkeypatch.setattr(_provenance, "installed_package_version", lambda: "6.0.0")
    with pytest.raises(ValueError, match=message) if "strings" not in message else pytest.raises(TypeError, match=message):
        _provenance.load_build_provenance()


def test_packaged_source_commit_must_be_a_string(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(_provenance, "load_build_provenance", lambda: {"source_commit": 7})
    with pytest.raises(TypeError, match="source commit"):
        _provenance.resolve_source_revision()


@pytest.mark.parametrize(("dirty", "suffix"), (("", ""), (" M rdam/machine.py", "-dirty")))
def test_checkout_revision_reports_clean_and_dirty_state(
    monkeypatch: pytest.MonkeyPatch,
    dirty: str,
    suffix: str,
) -> None:
    outputs = iter((SimpleNamespace(stdout=f"{'d' * 40}\n"), SimpleNamespace(stdout=dirty)))
    monkeypatch.setattr(_provenance, "load_build_provenance", lambda: None)
    monkeypatch.setattr(_provenance.subprocess, "run", lambda *_args, **_kwargs: next(outputs))
    assert _provenance.resolve_source_revision() == "d" * 40 + suffix


def test_checkout_revision_returns_unknown_only_for_process_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(_provenance, "load_build_provenance", lambda: None)
    monkeypatch.setattr(_provenance.subprocess, "run", lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError()))
    assert _provenance.resolve_source_revision() == "unknown"


def test_provider_source_identity_and_failure_helpers() -> None:
    package_version.cache_clear()
    identity = source_identity("rdam.dung", ("provider.py", "semantics.py"))
    assert len(identity.hex_digest) == 64
    assert package_version()
    failure = provider_failure(
        technique=Technique.DUNG,
        provider_id="fixture/dung",
        code="failed",
        retryability=Retryability.NOT_RETRYABLE,
        exception_type="ValueError",
    )
    assert failure.message_parameters == ()
    assert require_llm_text("accepted", technique=Technique.DUNG, provider_id="fixture/dung") == "accepted"


@pytest.mark.parametrize(
    ("revision", "expected"),
    ((None, False), ("", False), ("unknown", False), ("abc-dirty", False), ("abc", True)),
)
def test_cache_revision_eligibility(revision: str | None, expected: bool) -> None:
    assert revision_is_cacheable(revision) is expected


def _result(text: str = "cached") -> NativeTechniqueResult:
    return NativeTechniqueResult(
        technique=Technique.RST,
        formalism_id="rst_tree",
        provider_id="fixture/rst",
        provider_contract_version=SemanticVersion(root="1.0.0"),
        source=SourceIdentity.from_text(text),
        payload={},
        provenance=ProviderProvenance(
            package="fixture.rst",
            version="1",
            source_revision="clean",
            licence="test",
        ),
    )


def test_cache_miss_and_valid_hit(tmp_path: Path) -> None:
    cache = ResultCache(tmp_path)
    assert cache.load("missing", validate=lambda _result: None) is None
    cache.store("key", _result())
    assert cache.load("key", validate=lambda _result: None) == _result()


def test_cache_rejects_a_valid_non_result_record(tmp_path: Path) -> None:
    cache = ResultCache(tmp_path)
    (tmp_path / "key.json").write_bytes(serialize(Machine().capabilities()))
    with pytest.warns(RuntimeWarning, match="not a native technique result"):
        assert cache.load("key", validate=lambda _result: None) is None


def test_failed_atomic_replace_removes_temporary_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cache = ResultCache(tmp_path)
    monkeypatch.setattr("rdam._result_cache.os.replace", lambda *_args: (_ for _ in ()).throw(OSError("disk")))
    with pytest.raises(OSError, match="disk"):
        cache.store("key", _result())
    assert not tuple(tmp_path.glob(".*"))


def test_corrupt_entry_unlink_failure_is_warned(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "entry.json"
    path.write_text("bad", encoding="utf-8")
    monkeypatch.setattr(Path, "unlink", lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("locked")))
    with pytest.warns(RuntimeWarning, match="could not remove corrupt"):
        ResultCache._discard(path, ValueError("bad"))

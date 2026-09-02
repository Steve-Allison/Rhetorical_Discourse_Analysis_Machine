"""Composite participating-component and loaded-byte identity."""

from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from pathlib import PurePosixPath
from types import SimpleNamespace
from typing import Any

import pytest
import torch

from rdam.rst.ingest import ProductionIngestor, SourceArtifact
from rdam.rst.ingest.parser_result import validate_parser_analysis_result
from rdam.rst.model_loading.release import (
    ModelFile,
    ModelReleaseError,
    ModelReleaseManifest,
    ValidatedModelRelease,
)
from rdam.rst.transformer_parser.predictor import PredictorModernBERT

from .conftest import ParserBuilder


def test_every_immutable_component_has_an_exact_loaded_member_receipt(
    parser_builder: ParserBuilder,
) -> None:
    outcome = ProductionIngestor(parser=parser_builder()).analyse(
        SourceArtifact.from_text("First. Second.", source_name="components.txt")
    )
    result = outcome.semantic.parser_result
    assert result is not None
    immutable = {
        component.component
        for component in (
            result.semantic.composite_identity.primary_parser,
            result.semantic.composite_identity.segmenter,
            result.semantic.composite_identity.marker_refiner,
            result.semantic.composite_identity.relation_inventory,
        )
        if component.state == "immutable_release"
    }
    assert {receipt.component for receipt in result.semantic.loaded_components} == immutable
    validate_parser_analysis_result(result)

    receipt = result.semantic.loaded_components[0]
    damaged = receipt.model_copy(
        update={"declared_identity": receipt.declared_identity.model_copy(update={"hex_digest": "f" * 64})}
    )
    semantic = result.semantic.model_copy(
        update={"loaded_components": (damaged, *result.semantic.loaded_components[1:])}
    )
    with pytest.raises(ValueError, match="receipt"):
        validate_parser_analysis_result(result.model_copy(update={"semantic": semantic}))


def test_local_release_path_is_the_runtime_tokenizer_config_and_weight_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: dict[str, Any] = {}
    tokenizer = SimpleNamespace(is_fast=True)

    def load_tokenizer(path: str, **kwargs: object) -> object:
        calls["tokenizer_path"] = path
        calls["tokenizer_kwargs"] = kwargs
        return tokenizer

    class CapturingNet:
        dev = torch.device("cpu")
        dtype = torch.float32

        def __init__(self, **kwargs: object) -> None:
            calls["model_kwargs"] = kwargs

        def eval(self) -> None:
            calls["evaluated"] = True

    monkeypatch.setattr(
        "rdam.rst.transformer_parser.predictor.AutoTokenizer.from_pretrained",
        load_tokenizer,
    )
    monkeypatch.setattr(
        "rdam.rst.transformer_parser.predictor.PureTransformerParsingNet",
        CapturingNet,
    )

    PredictorModernBERT(model_dir=tmp_path)
    expected = str(tmp_path.resolve())
    assert calls["tokenizer_path"] == expected
    assert calls["tokenizer_kwargs"] == {
        "revision": None,
        "use_fast": True,
        "local_files_only": True,
    }
    model_kwargs = calls["model_kwargs"]
    assert isinstance(model_kwargs, dict)
    assert model_kwargs["model_name_or_path"] == expected
    assert model_kwargs["model_revision"] is None
    assert model_kwargs["local_files_only"] is True


def test_validated_release_strict_loads_full_parser_state_and_records_exact_runtime_bytes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    release = _validated_modernbert_release(tmp_path)
    calls: dict[str, Any] = {}
    tokenizer = SimpleNamespace(is_fast=True)
    encoder_config = SimpleNamespace(hidden_size=8)

    monkeypatch.setattr(
        "rdam.rst.transformer_parser.predictor.AutoTokenizer.from_pretrained",
        lambda path, **kwargs: tokenizer,
    )
    monkeypatch.setattr(
        "rdam.rst.transformer_parser.predictor.AutoConfig.from_pretrained",
        lambda path, **kwargs: encoder_config,
    )

    class CapturingNet:
        dev = torch.device("cpu")
        dtype = torch.float32

        def __init__(self, **kwargs: object) -> None:
            calls["model_kwargs"] = kwargs

        def eval(self) -> None:
            calls["evaluated"] = True

    def load_state(
        model: object,
        filename: Path,
        *,
        strict: bool,
        device: str,
    ) -> tuple[list[str], list[str]]:
        calls["state"] = (model, Path(filename), strict, device)
        return [], []

    monkeypatch.setattr(
        "rdam.rst.transformer_parser.predictor.PureTransformerParsingNet",
        CapturingNet,
    )
    monkeypatch.setattr(
        "rdam.rst.transformer_parser.predictor.load_safetensors_model",
        load_state,
    )

    predictor = PredictorModernBERT(
        model_dir=release.path,
        validated_release=release,
    )

    assert predictor.loaded_release_files == release.manifest.files
    assert calls["state"][1:] == (
        release.path / "parser.safetensors",
        True,
        "cpu",
    )
    model_kwargs = calls["model_kwargs"]
    assert isinstance(model_kwargs, dict)
    assert model_kwargs["encoder_config"] is encoder_config
    assert model_kwargs["raw_relation_inventory"] == ("same-unit",)


def test_validated_release_rejects_runtime_member_substitution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    release = _validated_modernbert_release(tmp_path)
    (release.path / "parser.safetensors").write_bytes(b"substituted")
    tokenizer = SimpleNamespace(is_fast=True)
    monkeypatch.setattr(
        "rdam.rst.transformer_parser.predictor.AutoTokenizer.from_pretrained",
        lambda path, **kwargs: tokenizer,
    )
    monkeypatch.setattr(
        "rdam.rst.transformer_parser.predictor.AutoConfig.from_pretrained",
        lambda path, **kwargs: SimpleNamespace(hidden_size=8),
    )

    class CapturingNet:
        dev = torch.device("cpu")
        dtype = torch.float32

        def __init__(self, **kwargs: object) -> None:
            del kwargs

        def eval(self) -> None: ...

    monkeypatch.setattr(
        "rdam.rst.transformer_parser.predictor.PureTransformerParsingNet",
        CapturingNet,
    )
    monkeypatch.setattr(
        "rdam.rst.transformer_parser.predictor.load_safetensors_model",
        lambda *args, **kwargs: ([], []),
    )

    with pytest.raises(ModelReleaseError, match="changed after release validation"):
        PredictorModernBERT(
            model_dir=release.path,
            validated_release=release,
        )


def _validated_modernbert_release(tmp_path: Path) -> ValidatedModelRelease:
    root = tmp_path / "modernbert-release"
    root.mkdir()
    payloads = {
        "config.json": b"{}",
        "tokenizer.json": b"{}",
        "parser.safetensors": b"strict parser state",
        "relation_inventory.json": json.dumps(["same-unit"]).encode(),
    }
    roles = {
        "config.json": "encoder_config",
        "tokenizer.json": "tokenizer",
        "parser.safetensors": "parser_state",
        "relation_inventory.json": "relation_inventory",
    }
    files: list[ModelFile] = []
    for name, payload in payloads.items():
        path = root / name
        path.write_bytes(payload)
        files.append(
            ModelFile(
                path=PurePosixPath(name),
                role=roles[name],
                size_bytes=len(payload),
                sha256=hashlib.sha256(payload).hexdigest(),
            )
        )
    manifest = ModelReleaseManifest(
        release_id=root.name,
        model_task="rst-parsing",
        architecture="modernbert-base-discourse-parser",
        runtime_contract="isanlp_rst.parser/modernbert-v1",
        compatibility_range=">=5,<7",
        source_model_identity="fixture/modernbert",
        source_revision="a" * 40,
        licence="Apache-2.0",
        use_restrictions=(),
        evaluation_evidence="fixture:test",
        created_at=datetime(2026, 8, 29, tzinfo=UTC),
        producer_version="5.0.0",
        files=tuple(files),
    )
    return ValidatedModelRelease(path=root, manifest=manifest)

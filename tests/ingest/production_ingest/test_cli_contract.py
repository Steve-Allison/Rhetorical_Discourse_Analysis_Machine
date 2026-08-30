"""CLI parity with the canonical Python production contract."""

from dataclasses import dataclass, field
from pathlib import Path

import pytest

import isanlp_rst.cli as cli
from isanlp_rst.ingest import (
    ProductionAnalysisOutcome,
    SafeProductionFailureRecord,
    SourceArtifact,
    SourceForm,
    load_contract,
    serialize_contract,
)

from .conftest import ParserBuilder


@dataclass(slots=True)
class _RecordingIngestor:
    outcome: ProductionAnalysisOutcome
    sources: list[SourceArtifact] = field(default_factory=list)

    def analyse(self, source: SourceArtifact, **_: object) -> ProductionAnalysisOutcome:
        self.sources.append(source)
        return self.outcome


def test_cli_canonical_json_is_byte_identical_and_runs_one_inference(
    parser_builder: ParserBuilder,
    monkeypatch: pytest.MonkeyPatch,
    capsysbinary: pytest.CaptureFixture[bytes],
) -> None:
    source = SourceArtifact.from_text("First. Second.", source_name="cli-text")
    outcome = cli.ProductionIngestor(parser=parser_builder()).analyse(source)
    recording = _RecordingIngestor(outcome)
    monkeypatch.setattr(cli, "_configured_ingestor", lambda _args: recording)

    assert cli.main(
        [
            "parse",
            "--text",
            source.raw_bytes.decode("utf-8") if source.raw_bytes is not None else "",
            "--model-store",
            "/model-store",
            "--release-id",
            "release",
        ]
    ) == 0
    captured = capsysbinary.readouterr()
    assert captured.out == serialize_contract(outcome) + b"\n"
    assert captured.err == b""
    assert len(recording.sources) == 1


@pytest.mark.parametrize(
    ("filename", "payload", "source_form"),
    (
        ("source.txt", b"Text.", SourceForm.TEXT),
        ("source.md", b"# Heading\n\nText.", SourceForm.MARKDOWN),
        ("source.docling.json", b'{"schema_name":"DoclingDocument","version":"1.10.0"}', SourceForm.DOCLING_JSON),
        ("source.dclg", b'<document xmlns="https://doclang.net/spec/v1.0"><text>Text.</text></document>', SourceForm.DOCLANG_XML),
        ("source.dclx", b"PK\x05\x06" + b"\x00" * 18, SourceForm.DOCLANG_ARCHIVE),
    ),
)
def test_cli_routes_path_source_forms_through_source_artifact(
    filename: str,
    payload: bytes,
    source_form: SourceForm,
    tmp_path: Path,
    parser_builder: ParserBuilder,
    monkeypatch: pytest.MonkeyPatch,
    capsysbinary: pytest.CaptureFixture[bytes],
) -> None:
    outcome = cli.ProductionIngestor(parser=parser_builder()).analyse(
        SourceArtifact.from_text("First. Second.", source_name="fixture")
    )
    recording = _RecordingIngestor(outcome)
    monkeypatch.setattr(cli, "_configured_ingestor", lambda _args: recording)
    path = tmp_path / filename
    path.write_bytes(payload)

    assert cli.main(
        ["parse", str(path), "--model-store", "/store", "--release-id", "release"]
    ) == 0
    capsysbinary.readouterr()
    assert [source.source_form for source in recording.sources] == [source_form]


def test_cli_routes_presegmented_edus_without_flattening(
    parser_builder: ParserBuilder,
    monkeypatch: pytest.MonkeyPatch,
    capsysbinary: pytest.CaptureFixture[bytes],
) -> None:
    outcome = cli.ProductionIngestor(parser=parser_builder()).analyse(
        SourceArtifact.from_text("First. Second.", source_name="fixture")
    )
    recording = _RecordingIngestor(outcome)
    monkeypatch.setattr(cli, "_configured_ingestor", lambda _args: recording)
    assert cli.main(
        [
            "parse",
            "--edus",
            '["First.","Second."]',
            "--model-store",
            "/store",
            "--release-id",
            "release",
        ]
    ) == 0
    capsysbinary.readouterr()
    assert recording.sources[0].source_form is SourceForm.EDUS
    assert recording.sources[0].edus == ("First.", "Second.")


def test_cli_malformed_input_is_a_canonical_safe_failure(
    capsysbinary: pytest.CaptureFixture[bytes],
) -> None:
    assert cli.main(
        [
            "parse",
            "--edus",
            "not-json",
            "--model-store",
            "/store",
            "--release-id",
            "release",
        ]
    ) == 2
    captured = capsysbinary.readouterr()
    assert captured.out == b""
    assert isinstance(load_contract(captured.err), SafeProductionFailureRecord)

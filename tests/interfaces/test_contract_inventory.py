"""Executable inventory; enumeration proves membership, not complete field coverage."""

import ast
from collections.abc import Callable
import json
from pathlib import Path
import re
from typing import Any

from pydantic import BaseModel
import pytest

from rdam import BOUNDARY_TECHNIQUES, AggregateRequest, Machine, OperationError, PreparationRequest, SourceIdentity, StructuredInput, Technique, ViewRequest, canonical_json_bytes
from rdam.cli import create_parser
from rdam.configuration import MachineConfig
from rdam.dung import DungProvider
from rdam.ingest.contracts.source import SourceForm
from rdam.serialization import (
    contract_support, load_config, load_preparation_request, load_request, load_view_request,
    schema, schema_models, serialize_config, serialize_preparation_request, serialize_request, serialize_view_request,
)

ROOT = Path(__file__).resolve().parents[2]
SPEC = ROOT / "specs/019-unified-machine-interfaces"
COMMANDS = ("capabilities", "prepare", "analyse", "summary", "view", "schema", "version", "serve")
CONFIG_COMMANDS = ("capabilities", "prepare", "analyse", "serve")
CONFIG_FLAGS = {
    "--config": "config.json", "--model": "openai:test", "--technique-model": "toulmin=openai:test",
    "--rst-model": "gumrrg", "--model-store": "models", "--release-id": "release",
    "--rst-relinventory": "eng.erst.gum", "--device": "cpu", "--erst-checkpoint": "checkpoint",
    "--rst-evidence-detail": "normalized_distributions", "--rst-marker-refinement": "disabled",
    "--dung-capacity": "2", "--max-workers": "1", "--cache-directory": "cache",
}
SOURCE_FLAGS = {"--text": "Source.", "--edus": '["Source."]', "--request": "request.json",
                "--source-name": "source", "--source-form": "text"}
HTTP_FLAGS = {"--host": "127.0.0.1", "--port": "0", "--max-request-bytes": "1024", "--body-timeout-seconds": "1"}
MAPPING_FLAGS = {"--structured", "--formalism", "--technique-model"}
CURRENT_SCHEMAS = {"request", "preparation-request", "configuration", "preparation", "aggregate", "capabilities",
                   "native-result", "operation-error", "version", "analysis-view", "view-request"}
HISTORICAL_SCHEMAS = {"aggregate-v1", "capabilities-v1", "native-result-v1", "toulmin-result-v1", "walton-result-v1"}
INPUT_SCHEMAS = {"dung-input", "ibis-input"}
OUTPUT_SCHEMAS = {f"{technique.value}-result" for technique in Technique}


def _flags(command: str) -> dict[str, str | None]:
    flags: dict[str, str | None] = {"--diagnostics": "json"}
    if command != "serve":
        flags.update({"--output": "output.json", "--force": None})
    if command in CONFIG_COMMANDS:
        flags.update(CONFIG_FLAGS)
    if command in {"prepare", "analyse"}:
        flags.update(SOURCE_FLAGS)
    if command in {"prepare", "analyse", "view"}:
        flags["--techniques"] = "dung"
    if command == "analyse":
        flags.update({"--structured": "dung=structure.json", "--formalism": "dung=dung_extensions"})
    if command == "schema":
        flags["--mode"] = "validation"
    if command == "serve":
        flags.update(HTTP_FLAGS)
    return flags


FLAG_CASES = tuple((command, flag, value) for command in COMMANDS for flag, value in _flags(command).items())


def _positionals(command: str) -> list[str]:
    return ["saved.json"] if command in {"summary", "view"} else ["request"] if command == "schema" else []


def test_documented_flags_have_explicit_grammar_inventory() -> None:
    docs = "\n".join((SPEC / "contracts" / name).read_text(encoding="utf-8") for name in ("cli.md", "http.md"))
    documented = set(re.findall(r"(?<![\w-])--[a-z][a-z-]*", docs))
    unsupported_examples = {"--set", "--format"}
    assert documented - unsupported_examples == {flag for _, flag, _ in FLAG_CASES} | {"--help", "--version"}


@pytest.mark.parametrize(("command", "flag", "value"), FLAG_CASES)
def test_each_documented_flag_is_accepted_by_its_actual_subcommand(command: str, flag: str, value: str | None) -> None:
    parsed = create_parser().parse_args([command, *_positionals(command), flag, *([] if value is None else [value])])
    actual = getattr(parsed, flag.removeprefix("--").replace("-", "_"))
    expected = [value] if flag in MAPPING_FLAGS else True if value is None else value
    assert str(actual) == str(expected) or isinstance(actual, (int, float)) and actual == float(str(value))


@pytest.mark.parametrize(("command", "flag", "value"), tuple(case for case in FLAG_CASES if case[1] not in MAPPING_FLAGS))
def test_every_singleton_is_rejected_twice_by_the_parser(command: str, flag: str, value: str | None) -> None:
    option = [flag, *([] if value is None else [value])]
    with pytest.raises(OperationError):
        create_parser().parse_args([command, *_positionals(command), *option, *option])


@pytest.mark.parametrize("command", tuple(command for command in COMMANDS if command not in CONFIG_COMMANDS))
@pytest.mark.parametrize("flag", tuple(CONFIG_FLAGS))
def test_config_flags_cannot_leak_into_saved_record_or_discovery_commands(command: str, flag: str) -> None:
    with pytest.raises(OperationError):
        create_parser().parse_args([command, *_positionals(command), flag, CONFIG_FLAGS[flag]])


# These references reuse only the named behavior. Existence does not prove a test passed.
REUSED_BEHAVIOR = (
    ("test_cli.py", "test_short_and_long_aliases_share_singleton_tracking"),
    ("test_cli.py", "test_mapping_options_reject_duplicate_keys"),
    ("test_cli.py", "test_configuration_and_flag_precedence_is_visible_in_actual_provider_records"),
    ("test_cli.py", "test_local_rst_selector_replaces_whole_configured_variant_and_requires_both_flags"),
    ("test_cli.py", "test_stdin_ownership_is_rejected_without_waiting_for_any_bytes"),
    ("test_cli.py", "test_paths_are_literal_including_option_like_and_expansion_characters"),
    ("test_cli.py", "test_existing_output_requires_force_and_never_creates_missing_parents"),
    ("test_cli.py", "test_text_diagnostics_are_safe_and_never_written_to_stdout"),
    ("test_cli.py", "test_explicit_formalism_is_not_replaced_by_provider_default"),
    ("test_http.py", "test_cli_serve_reports_actual_port_and_stops_cleanly_on_interrupt"),
    ("test_http.py", "test_encoded_body_limit_is_inclusive"),
    ("test_http.py", "test_slow_body_has_one_total_deadline_and_releases_admission"),
    ("test_schemas.py", "test_llm_provider_outputs_and_current_records_match_schemas"),
    ("test_schemas.py", "test_saved_historical_records_match_their_advertised_schemas"),
)


@pytest.mark.parametrize(("filename", "test_name"), REUSED_BEHAVIOR)
def test_reused_behavioral_test_references_do_not_go_stale(filename: str, test_name: str) -> None:
    tree = ast.parse((Path(__file__).parent / filename).read_text(encoding="utf-8"))
    assert any(isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == test_name for node in ast.walk(tree))


def test_current_historical_native_and_input_schema_names_are_exact() -> None:
    assert set(schema_models()) == CURRENT_SCHEMAS | HISTORICAL_SCHEMAS | INPUT_SCHEMAS | OUTPUT_SCHEMAS


def test_discovery_lists_every_readable_version_schema_for_its_contract() -> None:
    for support in contract_support():
        matching = {name: model for name, model in schema_models().items()
                    if "contract" in model.model_fields and model.model_fields["contract"].default == support.contract}
        assert set(support.schema_names) == set(matching), support.contract
        assert set(support.read_versions) == {str(model.model_fields["contract_version"].default) for model in matching.values()}
        assert support.write_version in support.read_versions


@pytest.mark.parametrize("name", tuple(sorted(CURRENT_SCHEMAS | HISTORICAL_SCHEMAS | INPUT_SCHEMAS | OUTPUT_SCHEMAS)))
@pytest.mark.parametrize("mode", ("validation", "serialization"))
def test_generated_package_schemas_match_public_registry(name: str, mode: str) -> None:
    document = schema(name, mode="validation" if mode == "validation" else "serialization")
    installed = ROOT / "rdam/ingest/schemas" / f"machine-{name}.{mode}.schema.json"
    assert json.loads(installed.read_bytes()) == document


@pytest.fixture
def request_documents() -> dict[str, dict[str, Any]]:
    request = AggregateRequest.for_structured((StructuredInput(technique=Technique.DUNG, payload={"arguments": ["a"], "attacks": []}),))
    aggregate = Machine((DungProvider(),)).analyse(request)
    return {
        "request": json.loads(serialize_request(AggregateRequest.for_text("Source.", (Technique.TOULMIN,)))),
        "preparation-request": json.loads(serialize_preparation_request(PreparationRequest.for_text("Source."))),
        "view-request": json.loads(serialize_view_request(ViewRequest(analysis=aggregate, techniques=(Technique.DUNG,)))),
        "configuration": json.loads(serialize_config(MachineConfig.model_validate_json(canonical_json_bytes({
            "llm": {"model": "openai:test", "output_retries": 0, "transport_retries": 1, "transport_deadline_seconds": 1.5},
            "technique_models": {technique: f"openai:{technique}" for technique in ("pdtb", "sdrt", "toulmin", "walton")},
            "rst": {"model": {"kind": "local_release", "store": "models", "release_id": "release"},
                    "relinventory": "eng.erst.gum", "device": "cpu", "erst_checkpoint": "checkpoint",
                    "default_formalism": "erst_graph", "evidence_detail": "normalized_distributions", "marker_refinement": "disabled"},
            "dung_capacity": 2, "execution": {"max_workers": 1, "cache_directory": "cache"},
        })))),
    }


def _load_document(kind: str, document: dict[str, Any], directory: Path) -> BaseModel:
    payload = canonical_json_bytes(document)
    if kind == "configuration":
        path = directory / "config.json"
        path.write_bytes(payload)
        return load_config(path)
    loaders: dict[str, Callable[[bytes], BaseModel]] = {
        "request": load_request, "preparation-request": load_preparation_request, "view-request": load_view_request,
    }
    return loaders[kind](payload)


@pytest.mark.parametrize("kind", ("request", "preparation-request", "view-request", "configuration"))
@pytest.mark.parametrize("field", ("contract", "contract_version"))
@pytest.mark.parametrize("damage", ("missing", "null", "unsupported"))
def test_dedicated_codecs_require_supported_explicit_envelopes(
    request_documents: dict[str, dict[str, Any]], tmp_path: Path, kind: str, field: str, damage: str,
) -> None:
    document = request_documents[kind]
    _load_document(kind, document, tmp_path)
    if damage == "missing":
        del document[field]
    else:
        document[field] = None if damage == "null" else "unsupported"
    with pytest.raises(ValueError):
        _load_document(kind, document, tmp_path)


@pytest.mark.parametrize("kind", ("request", "preparation-request", "view-request", "configuration"))
@pytest.mark.parametrize("field", ("unknown", "api_key", "base_url", "http_port"))
def test_dedicated_codecs_reject_unknown_secrets_and_transport_fields(
    request_documents: dict[str, dict[str, Any]], tmp_path: Path, kind: str, field: str,
) -> None:
    document = request_documents[kind]
    _load_document(kind, document, tmp_path)
    document[field] = "PRIVATE_UNUSED_VALUE"
    with pytest.raises(ValueError):
        _load_document(kind, document, tmp_path)


@pytest.mark.parametrize(("path", "invalid"), (
    (("llm", "model"), "unknown:model"), (("llm", "output_retries"), -1),
    (("llm", "output_retries"), True), (("llm", "transport_retries"), "2"),
    (("llm", "transport_deadline_seconds"), 0), (("llm", "api_key"), "PRIVATE_UNUSED_VALUE"),
    *(((("technique_models", technique), "invalid:model")) for technique in ("pdtb", "sdrt", "toulmin", "walton")),
    (("technique_models", "dung"), "openai:test"),
    (("rst", "model"), {"kind": "other", "version": "gumrrg"}),
    (("rst", "model"), {"kind": "published", "version": ""}),
    (("rst", "model"), {"kind": "published", "version": "gumrrg", "store": "models"}),
    (("rst", "model"), {"kind": "local_release", "store": "models"}),
    (("rst", "model"), {"kind": "local_release", "store": "models", "release_id": "../escape"}),
    (("rst", "relinventory"), ""), (("rst", "device"), "cuda:-1"),
    (("rst", "erst_checkpoint"), True), (("rst", "default_formalism"), "sdrs_graph"),
    (("rst", "evidence_detail"), "none"), (("rst", "marker_refinement"), "discard"),
    (("dung_capacity",), 0), (("dung_capacity",), True),
    (("execution", "max_workers"), 0), (("execution", "max_workers"), len(BOUNDARY_TECHNIQUES) + 1),
    (("execution", "max_workers"), True), (("execution", "cache_directory"), False),
))
def test_configuration_field_restrictions_are_exercised(
    request_documents: dict[str, dict[str, Any]], tmp_path: Path, path: tuple[str, ...], invalid: object,
) -> None:
    document = request_documents["configuration"]
    _load_document("configuration", document, tmp_path)
    target = document
    for component in path[:-1]:
        target = target[component]
    target[path[-1]] = invalid
    with pytest.raises(ValueError):
        _load_document("configuration", document, tmp_path)


@pytest.mark.parametrize("kind", ("request", "preparation-request"))
@pytest.mark.parametrize("damage", ("no_source", "both_sources", "wrong_digest", "duplicate_techniques", "formalism_boundary", "wrong_text_type"))
def test_request_source_and_selection_restrictions_are_exercised(
    request_documents: dict[str, dict[str, Any]], tmp_path: Path, kind: str, damage: str,
) -> None:
    document = request_documents[kind]
    _load_document(kind, document, tmp_path)
    if damage == "no_source":
        document["text"] = None
    elif damage == "both_sources":
        artifact_request = AggregateRequest.for_bytes(b"Source.", SourceForm.TEXT, "source", (Technique.TOULMIN,))
        document["source_artifact"] = json.loads(serialize_request(artifact_request))["source_artifact"]
    elif damage == "wrong_digest":
        document["source"] = SourceIdentity.from_text("Different.").model_dump(mode="json")
    elif damage == "duplicate_techniques":
        document["techniques"] = ["dung", "dung"]
    elif damage == "formalism_boundary":
        document["techniques"] = ["erst"]
    else:
        document["text"] = True
    with pytest.raises(ValueError):
        _load_document(kind, document, tmp_path)


REQUEST_RESTRICTIONS: tuple[tuple[str, object], ...] = (
    ("structured_inputs", [{"technique": "walton", "payload": dict[str, object]()}]),
    ("structured_inputs", [{"technique": "dung", "payload": {"arguments": ["a"], "attacks": []}}]),
    ("structured_inputs", "not-an-array"),
    ("formalisms", [{"technique": "dung", "formalism_id": "dung_extensions"}]),
    ("formalisms", [{"technique": "toulmin", "formalism_id": "not a formalism"}]),
    ("formalisms", [{"technique": "toulmin", "formalism_id": "toulmin_layout"}] * 2),
    ("upstream_results", [dict[str, object]()]), ("upstream_results", "not-an-array"),
)


@pytest.mark.parametrize(("field", "invalid"), REQUEST_RESTRICTIONS)
def test_analysis_request_structure_formalism_and_upstream_restrictions(
    request_documents: dict[str, dict[str, Any]], tmp_path: Path, field: str, invalid: object,
) -> None:
    document = request_documents["request"]
    _load_document("request", document, tmp_path)
    document[field] = invalid
    with pytest.raises(ValueError):
        _load_document("request", document, tmp_path)


@pytest.mark.parametrize("field", ("structured_inputs", "upstream_results", "formalisms"))
def test_preparation_forbids_analysis_only_fields(
    request_documents: dict[str, dict[str, Any]], tmp_path: Path, field: str,
) -> None:
    document = request_documents["preparation-request"]
    document[field] = []
    with pytest.raises(ValueError):
        _load_document("preparation-request", document, tmp_path)


@pytest.mark.parametrize("kind", ("request", "preparation-request", "view-request", "configuration"))
def test_dedicated_loaders_reject_duplicate_keys_even_when_equal(
    request_documents: dict[str, dict[str, Any]], tmp_path: Path, kind: str,
) -> None:
    document = request_documents[kind]
    payload = canonical_json_bytes(document)
    duplicated = payload[:-1] + b',"contract":' + json.dumps(document["contract"]).encode("utf-8") + b"}"
    if kind == "configuration":
        path = tmp_path / "duplicate-config.json"
        path.write_bytes(duplicated)
        with pytest.raises(ValueError, match="duplicate"):
            load_config(path)
    else:
        loader = {"request": load_request, "preparation-request": load_preparation_request, "view-request": load_view_request}[kind]
        with pytest.raises(ValueError, match="duplicate"):
            loader(duplicated)


def test_empty_text_is_present_but_empty_analysis_selection_is_not() -> None:
    assert load_request(serialize_request(AggregateRequest.for_text("", (Technique.TOULMIN,)))).text == ""
    assert load_preparation_request(serialize_preparation_request(PreparationRequest.for_text(""))).techniques == ()
    with pytest.raises(ValueError):
        AggregateRequest.for_text("", ())


@pytest.mark.parametrize("kind", ("request", "preparation-request"))
@pytest.mark.parametrize("damage", ("invalid_utf8", "empty_edus", "blank_edu"))
def test_wire_source_validation_matches_convenience_constructor_restrictions(kind: str, damage: str) -> None:
    request = AggregateRequest.for_bytes(b"Source.", SourceForm.TEXT, "source", (Technique.TOULMIN,))
    document = json.loads(serialize_request(request))
    artifact = document["source_artifact"]["artifact"]
    for field in ("source_id", "raw_sha256", "raw_size_bytes"):
        del artifact[field]
    if damage == "invalid_utf8":
        artifact["raw_bytes"] = "/w=="
        source_bytes = b"\xff"
    else:
        edus = [] if damage == "empty_edus" else ["   "]
        artifact.update(source_form="edus", raw_bytes=None, edus=edus)
        source_bytes = json.dumps(edus, separators=(",", ":")).encode("utf-8")
    document["source"] = SourceIdentity.from_bytes(source_bytes).model_dump(mode="json")
    if kind == "preparation-request":
        document["contract"] = "rdam.preparation_request"
        for field in ("structured_inputs", "formalisms", "upstream_results"):
            del document[field]
        loader = load_preparation_request
    else:
        loader = load_request
    with pytest.raises(ValueError):
        loader(canonical_json_bytes(document))

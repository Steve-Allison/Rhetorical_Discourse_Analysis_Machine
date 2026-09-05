"""The installed grammar and standard streams are the public interface."""

import json
import os
from pathlib import Path
import subprocess
import sys
from typing import cast
import pytest

from rdam._strict import canonical_json_bytes
from rdam.configuration import LlmSettings, MachineConfig, TechniqueModels
from rdam.contracts import AggregateRequest, PreparationRequest, StructuredInput
from rdam.composition import production_machine
from rdam.frameworks import Technique
from rdam.serialization import serialize, serialize_config, serialize_preparation_request, serialize_request


def run_cli(*arguments: str, input_bytes: bytes | None = None, cwd: Path | None = None,
            env: dict[str, str] | None = None) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run([sys.executable, "-m", "rdam", *arguments], input=input_bytes, capture_output=True,
                          check=False, cwd=cwd, env=env, timeout=30)


def record(result: subprocess.CompletedProcess[bytes], expected_exit: int = 0) -> dict[str, object]:
    assert result.returncode == expected_exit, result.stderr
    assert result.stderr == b""
    decoded = cast(dict[str, object], json.loads(result.stdout))
    assert result.stdout == canonical_json_bytes(decoded) + b"\n"
    return decoded


def diagnostic(result: subprocess.CompletedProcess[bytes], expected_exit: int = 2) -> dict[str, object]:
    assert result.returncode == expected_exit, (result.stdout, result.stderr)
    assert result.stdout == b""
    decoded = cast(dict[str, object], json.loads(result.stderr))
    assert decoded["contract"] == "rdam.operation_error"
    assert result.stderr == canonical_json_bytes(decoded) + b"\n"
    assert b"Traceback" not in result.stderr
    return decoded


def json_object(value: object) -> dict[str, object]:
    assert isinstance(value, dict)
    return cast(dict[str, object], value)


def json_array(value: object) -> list[object]:
    assert isinstance(value, list)
    return cast(list[object], value)


def test_root_help() -> None:
    result = run_cli("--help")
    assert result.returncode == 0
    assert result.stderr == b""
    for command in (b"capabilities", b"prepare", b"analyse", b"view", b"summary", b"schema", b"version", b"serve"):
        assert command in result.stdout


@pytest.mark.parametrize("args", [(), ("analyze",), ("version", "--output", "-", "-o", "-"),
                                ("analyse", "--text", "x", "--techniques", "dung,dung"),
                                ("prepare", "-", "--request", "-"), ("prepare", "--text", "x", "--force")])
def test_invalid_grammar_has_safe_json_diagnostic(args: tuple[str, ...]) -> None:
    result = run_cli(*args)
    assert result.returncode == 2
    assert result.stdout == b""
    assert json.loads(result.stderr)["contract"] == "rdam.operation_error"


def test_inline_prepare_has_one_json_document() -> None:
    result = run_cli("prepare", "--text", "A short source.")
    assert result.returncode == 0, result.stderr
    record = json.loads(result.stdout)
    assert record["contract"] == "rdam.preparation"
    assert record["source"]["source_name"] == "cli-text"
    assert record["bindings"] == []
    assert result.stderr == b""
    assert result.stdout.endswith(b"\n") and not result.stdout.endswith(b"\n\n")


def test_structured_stdin_success() -> None:
    result = run_cli("analyse", "--techniques", "dung", "--structured", "dung=-",
                     input_bytes=b'{"arguments":["a"],"attacks":[]}')
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["status"] == "complete"


@pytest.mark.parametrize(("command", "flag", "value"), (
    ("prepare", "--text", "x"), ("prepare", "--edus", '["x"]'), ("prepare", "--request", "missing"),
    ("prepare", "--source-name", "name"), ("prepare", "--source-form", "text"),
    ("prepare", "--techniques", "dung"), ("version", "--output", "-"),
    ("version", "--diagnostics", "json"), ("schema", "--mode", "validation"),
    *(("capabilities", flag, value) for flag, value in (
        ("--config", "missing"), ("--model", "openai:test"), ("--rst-model", "gumrrg"),
        ("--model-store", "missing"), ("--release-id", "release"), ("--rst-relinventory", "eng.erst.gum"),
        ("--device", "cpu"), ("--erst-checkpoint", "missing"), ("--cache-directory", "missing"),
        ("--rst-evidence-detail", "decision_complete"), ("--rst-marker-refinement", "disabled"),
        ("--dung-capacity", "2"), ("--max-workers", "1"))),
    ("serve", "--host", "127.0.0.1"), ("serve", "--port", "0"),
    ("serve", "--max-request-bytes", "1024"), ("serve", "--body-timeout-seconds", "1"),
))
def test_every_singleton_rejects_repetition_even_when_values_agree(command: str, flag: str, value: str) -> None:
    positional = ("request",) if command == "schema" else ()
    problem = diagnostic(run_cli(command, *positional, flag, value, flag, value))
    assert problem["code"] == "invalid_arguments"


@pytest.mark.parametrize("options", (("-o", "-", "--output", "-"), ("-c", "missing", "--config", "missing")))
def test_short_and_long_aliases_share_singleton_tracking(options: tuple[str, ...]) -> None:
    diagnostic(run_cli("capabilities", *options))


def test_boolean_singletons_are_not_repeatable(tmp_path: Path) -> None:
    diagnostic(run_cli("--version", "--version"))
    destination = tmp_path / "output.json"
    diagnostic(run_cli("version", "-o", str(destination), "--force", "--force"))
    assert not destination.exists()


@pytest.mark.parametrize("arguments", (
    ("parse",), ("analyze",), ("summarise",), ("--model", "openai:test", "capabilities"),
    ("prepare", "--tex", "private-value"), ("prepare", "--text", "x", "--unknown", "private-value"),
    ("analyse", "--text", "x"), ("analyse", "--text", "x", "--techniques", ""),
    *(("analyse", "--text", "x", "--techniques", value) for value in ("dung,", ",dung", "dung,,ibis", "DUNG", "erst", "dung,dung")),
    ("prepare", "missing", "--text", "x"), ("prepare", "--text", "x", "--edus", '["x"]'),
    ("prepare", "--text", "x", "--source-form", "text"), ("prepare", "--edus", '["x"]', "--source-form", "edus"),
    ("prepare", "--request", "missing", "--techniques", "dung"),
    ("analyse", "--request", "missing", "--source-name", "name"),
    ("analyse", "--request", "missing", "--formalism", "dung=dung_extensions"),
    ("analyse", "--request", "missing", "--structured", "dung=missing"),
    ("capabilities", "--model-store", "missing"), ("capabilities", "--release-id", "release"),
    ("capabilities", "--rst-model", "gumrrg", "--model-store", "missing", "--release-id", "release"),
    ("capabilities", "--max-workers", "0"), ("capabilities", "--max-workers", "8"),
    ("capabilities", "--dung-capacity", "0"), ("capabilities", "--device", "private-value"),
    ("capabilities", "--model", "openai:"), ("capabilities", "--set", "private-value"),
    ("summary", "missing", "--model", "openai:test"), ("view", "missing", "--config", "missing"),
    ("version", "--force"), ("version", "--force", "-o", "-"),
))
def test_closed_grammar_and_exclusive_modes_fail_safely(arguments: tuple[str, ...]) -> None:
    result = run_cli(*arguments)
    diagnostic(result)
    assert b"private-value" not in result.stderr


@pytest.mark.parametrize(("flag", "value"), (("--structured", "dung=-"), ("--formalism", "dung=dung_extensions"),
    ("--technique-model", "toulmin=openai:test")))
def test_mapping_options_reject_duplicate_keys(flag: str, value: str) -> None:
    command = "capabilities" if flag == "--technique-model" else "analyse"
    source = () if command == "capabilities" else ("--text", "x", "--techniques", "dung")
    diagnostic(run_cli(command, *source, flag, value, flag, value))


@pytest.mark.parametrize("arguments", (
    ("prepare",), ("analyse", "--techniques", "dung"),
    ("prepare", "-", "--request", "-"), ("prepare", "--request", "-", "--config", "-"),
    ("analyse", "-", "--techniques", "dung", "--structured", "dung=-"),
    ("analyse", "--techniques", "dung,ibis", "--structured", "dung=-", "--structured", "ibis=-"),
    ("prepare", "-", "--model", "openai:"),
    ("prepare", "-", "--model-store", "missing"),
    ("prepare", "-", "--technique-model", "unknown=openai:test"),
    ("analyse", "-", "--techniques", "dung", "--formalism", "ibis=ibis_structure"),
    ("analyse", "--techniques", "dung", "--structured", "dung=-", "--source-form", "markdown"),
))
def test_stdin_ownership_is_rejected_without_waiting_for_any_bytes(arguments: tuple[str, ...]) -> None:
    with subprocess.Popen([sys.executable, "-m", "rdam", *arguments], stdin=subprocess.PIPE,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE) as process:
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate()
            pytest.fail("invalid input ownership blocked waiting for stdin")
        stdout, stderr = process.communicate()
    diagnostic(subprocess.CompletedProcess(process.args, process.returncode, stdout, stderr))


@pytest.mark.parametrize("arguments", (("--version",), ("version",), ("schema", "request"),
    ("prepare", "--config", "does-not-exist", "--help")))
def test_discovery_short_circuits_invalid_environment_and_unused_config(arguments: tuple[str, ...]) -> None:
    env = {**os.environ, "RDAM_LLM_MODEL": "invalid:model"}
    result = run_cli(*arguments, env=env)
    assert result.returncode == 0, result.stderr
    assert result.stderr == b""


def test_version_alias_has_exactly_the_same_bytes() -> None:
    assert record(run_cli("--version")) == record(run_cli("version"))


def test_configuration_and_flag_precedence_is_visible_in_actual_provider_records(tmp_path: Path) -> None:
    config = MachineConfig(llm=LlmSettings(model="openai:shared-file"),
                           technique_models=TechniqueModels(toulmin="anthropic:specific-file"))
    path = tmp_path / "config.json"
    path.write_bytes(serialize_config(config))
    result = record(run_cli("capabilities", "-c", str(path), "--model", "openai:shared-flag",
        "--technique-model", "walton=google:specific-flag", "--rst-model", "unavailable-version", "--device", "cpu",
        "--rst-relinventory", "eng.erst.gum", "--rst-evidence-detail", "normalized_distributions",
        "--rst-marker-refinement", "disabled", "--dung-capacity", "3", "--max-workers", "1",
        "--cache-directory", str(tmp_path / "cache")))
    settings: dict[str, dict[str, object]] = {}
    for entry in json_array(result["configurations"]):
        item = json_object(entry)
        technique = item["technique"]
        assert isinstance(technique, str)
        settings[technique] = json_object(json_object(item["configuration"])["settings"])
    assert settings["pdtb"]["model"] == "openai:shared-flag"
    assert settings["toulmin"]["model"] == "anthropic:specific-file"
    assert settings["walton"]["model"] == "google:specific-flag"
    assert settings["dung"]["capacity"] == 3
    assert settings["rst"]["model_identity"] == "unavailable-version"
    assert settings["rst"]["device"] == "cpu"
    assert settings["rst"]["relinventory"] == "eng.erst.gum"
    assert settings["rst"]["evidence_detail"] == "normalized_distributions"
    assert settings["rst"]["marker_refinement"] == "disabled"


@pytest.mark.parametrize("name", ("-source.txt", "-", "*.txt", "~"))
def test_paths_are_literal_including_option_like_and_expansion_characters(name: str, tmp_path: Path) -> None:
    path = tmp_path / name
    path.write_text("Literal path source.", encoding="utf-8")
    argument = "./-" if name == "-" else name
    result = run_cli("prepare", "--source-form", "text", "--", argument, cwd=tmp_path)
    payload = record(result)
    assert json_object(payload["source"])["source_name"] == name


def test_source_name_override_preserves_local_origin_and_byte_identity(tmp_path: Path) -> None:
    source = tmp_path / "source.txt"
    source.write_text("Evidence.", encoding="utf-8")
    result = record(run_cli("prepare", str(source), "--source-name", "override"))
    semantic = json_object(result["preparation"])
    assert json_object(semantic["source"])["origin_classification"] == "local_file"
    assert json_object(result["source"])["source_name"] == "override"


def test_stdin_is_text_unless_a_form_is_explicitly_selected() -> None:
    data = b'["First.", "Second."]'
    text = record(run_cli("prepare", "-", input_bytes=data))
    edus = record(run_cli("prepare", "-", "--source-form", "edus", input_bytes=data))
    assert json_object(json_object(text["preparation"])["source"])["source_form"] == "text"
    assert json_object(json_object(edus["preparation"])["source"])["source_form"] == "edus"
    assert json_object(text["source"])["source_id"] == json_object(edus["source"])["source_id"]
    assert json_object(text["source"])["source_name"] == "stdin"


@pytest.mark.parametrize(("techniques", "payload", "expected_exit", "status"), (
    ("dung", b'{"arguments":["a"],"attacks":[["a","a"]]}', 0, "complete"),
    (" ibis , dung ", b'{"arguments":["a"],"attacks":[]}', 3, "partial"),
    ("dung", b'{"arguments":["a"],"attacks":[["a","unknown"]]}', 4, "unsuccessful"),
))
def test_analysis_exits_preserve_full_requested_scope(techniques: str, payload: bytes, expected_exit: int, status: str) -> None:
    result = record(run_cli("analyse", "--techniques", techniques, "--structured", "dung=-", input_bytes=payload), expected_exit)
    assert result["status"] == status
    assert result["requested_techniques"] == [item.strip() for item in techniques.split(",")]


@pytest.mark.parametrize(("arguments", "input_bytes", "expected_exit"), (
    (("prepare", "private-missing-source.txt"), None, 1),
    (("prepare", "-"), b"\xff", 2),
    (("prepare", "--edus", '"private-invalid-value"'), None, 2),
    (("prepare", "-", "--source-form", "doclang_xml"), b"<doclang><bad></doclang>", 1),
    (("analyse", "--request", "-"), b"{}", 2),
))
def test_fatal_failures_use_safe_diagnostics_without_source_values(arguments: tuple[str, ...], input_bytes: bytes | None,
                                                                  expected_exit: int) -> None:
    result = run_cli(*arguments, input_bytes=input_bytes)
    diagnostic(result, expected_exit)
    assert b"private-" not in result.stderr
    assert b"<doclang>" not in result.stderr


def test_text_diagnostics_are_safe_and_never_written_to_stdout() -> None:
    result = run_cli("prepare", "private-missing-path", "--diagnostics", "text")
    assert result.returncode == 1
    assert result.stdout == b""
    assert result.stderr.startswith(b"source_unavailable:")
    assert b"private-missing-path" not in result.stderr


def test_request_routes_have_exact_python_parity() -> None:
    preparation = PreparationRequest.for_text("Evidence.", (Technique.DUNG,), source_name="shared")
    prepared = run_cli("prepare", "--request", "-", input_bytes=serialize_preparation_request(preparation))
    assert prepared.stdout == serialize(production_machine().prepare(preparation)) + b"\n"
    request = AggregateRequest.for_structured((StructuredInput(technique=Technique.DUNG,
        payload={"arguments": ["a"], "attacks": []}),))
    analysed = run_cli("analyse", "--request", "-", input_bytes=serialize_request(request))
    assert analysed.stdout == serialize(production_machine().analyse(request)) + b"\n"
    assert prepared.returncode == analysed.returncode == 0


def test_file_publication_and_summary_view_preserve_saved_input(tmp_path: Path) -> None:
    destination = tmp_path / "analysis.json"
    result = run_cli("analyse", "--techniques", "dung,ibis", "--structured", "dung=-", "-o", str(destination),
                     input_bytes=b'{"arguments":["a"],"attacks":[]}')
    assert result.returncode == 3 and result.stdout == result.stderr == b""
    saved = destination.read_bytes()
    assert json.loads(saved)["status"] == "partial"
    assert destination.stat().st_mode & 0o777 == 0o600
    summary = run_cli("summary", str(destination))
    assert summary.returncode == 0 and summary.stderr == b""
    assert b"partial" in summary.stdout
    view = record(run_cli("view", str(destination), "--techniques", "dung"))
    assert view["analysis_status"] == "partial"
    diagnostic(run_cli("summary", str(destination), "-o", str(destination), "--force"), 1)
    assert destination.read_bytes() == saved
    assert not tuple(tmp_path.glob(".rdam-*.tmp"))


@pytest.mark.parametrize("alias_kind", ("same", "hardlink", "symlink"))
def test_force_never_overwrites_an_input_alias(alias_kind: str, tmp_path: Path) -> None:
    source = tmp_path / "source.txt"
    source.write_bytes(b"Preserve these source bytes.")
    target = source if alias_kind == "same" else tmp_path / "output.json"
    if alias_kind == "hardlink":
        target.hardlink_to(source)
    elif alias_kind == "symlink":
        target.symlink_to(source)
    diagnostic(run_cli("prepare", str(source), "-o", str(target), "--force"), 1)
    assert source.read_bytes() == b"Preserve these source bytes."


def test_closed_stdout_pipe_has_exit_141_without_a_traceback() -> None:
    with subprocess.Popen([sys.executable, "-m", "rdam", "version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE) as process:
        assert process.stdout is not None
        process.stdout.close()
        assert process.wait(timeout=10) == 141
        assert process.stderr is not None
        assert b"Traceback" not in process.stderr.read()


@pytest.mark.parametrize("command", ("capabilities", "prepare", "analyse", "summary", "view", "schema", "version", "serve"))
def test_command_help_includes_a_small_usage_example(command: str) -> None:
    result = run_cli(command, "--help")
    assert result.returncode == 0 and result.stderr == b""
    assert b"example" in result.stdout.lower()


@pytest.mark.parametrize("value", ("dung", "dung=", "unknown=x", "rst=x"))
def test_structured_mapping_rejects_missing_values_and_non_structured_boundaries(value: str) -> None:
    diagnostic(run_cli("analyse", "--text", "x", "--techniques", "dung", "--structured", value))


@pytest.mark.parametrize("value", ("toulmin", "toulmin=", "unknown=x", "dung=openai:test"))
def test_model_mapping_rejects_missing_values_and_non_llm_boundaries(value: str) -> None:
    diagnostic(run_cli("capabilities", "--technique-model", value))


@pytest.mark.parametrize("value", ("dung", "dung=", "ibis=ibis_structure", "erst=erst_graph"))
def test_formalism_mapping_is_only_for_selected_boundaries(value: str) -> None:
    diagnostic(run_cli("analyse", "--text", "x", "--techniques", "dung", "--formalism", value))


def test_unrelated_source_form_cannot_be_silently_ignored_in_structured_only_mode() -> None:
    diagnostic(run_cli("analyse", "--techniques", "dung", "--structured", "dung=-", "--source-form", "markdown",
                       input_bytes=b'{"arguments":["a"],"attacks":[]}'))


def test_local_rst_selector_replaces_whole_configured_variant_and_requires_both_flags(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    config = json.loads(serialize_config(MachineConfig()))
    config["rst"]["model"] = {"kind": "local_release", "store": str(tmp_path), "release_id": "from-file"}
    path.write_text(json.dumps(config), encoding="utf-8")
    diagnostic(run_cli("capabilities", "--config", str(path), "--release-id", "from-flag"))
    diagnostic(run_cli("capabilities", "--config", str(path), "--model-store", str(tmp_path)))
    published = record(run_cli("capabilities", "--config", str(path), "--rst-model", "unknown-published"))
    local = record(run_cli("capabilities", "--config", str(path), "--model-store", str(tmp_path), "--release-id", "from-flag"))
    for result, expected in ((published, "unknown-published"), (local, "from-flag")):
        rst = next(json_object(item) for item in json_array(result["configurations"]) if json_object(item)["technique"] == "rst")
        assert json_object(json_object(rst["configuration"])["settings"])["model_identity"] == expected


def test_existing_output_requires_force_and_never_creates_missing_parents(tmp_path: Path) -> None:
    target = tmp_path / "result.json"
    target.write_bytes(b"Keep until successful replacement.")
    diagnostic(run_cli("version", "-o", str(target)), 1)
    assert target.read_bytes() == b"Keep until successful replacement."
    result = run_cli("version", "-o", str(target), "--force")
    assert result.returncode == 0 and result.stdout == result.stderr == b""
    assert json.loads(target.read_bytes())["contract"] == "rdam.version"
    missing_parent = tmp_path / "not-created"
    diagnostic(run_cli("version", "-o", str(missing_parent / "result.json")), 1)
    assert not missing_parent.exists()


def test_config_and_structure_inputs_are_also_protected_from_publication(tmp_path: Path) -> None:
    config = tmp_path / "config.json"
    config.write_bytes(serialize_config(MachineConfig()))
    structure = tmp_path / "dung.json"
    structure.write_bytes(b'{"arguments":["a"],"attacks":[]}')
    for target in (config, structure):
        before = target.read_bytes()
        diagnostic(run_cli("analyse", "--techniques", "dung", "--structured", f"dung={structure}",
                           "--config", str(config), "-o", str(target), "--force"), 1)
        assert target.read_bytes() == before


@pytest.mark.parametrize("mode", ("validation", "serialization"))
def test_schema_modes_use_the_requested_shape(mode: str) -> None:
    result = record(run_cli("schema", "request", "--mode", mode))
    assert result["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert str(result["$id"]).endswith(f"/{mode}.schema.json")


def test_legacy_view_is_rejected_without_inventing_requested_scope() -> None:
    fixture = Path(__file__).parent / "fixtures/historical/aggregate-v1.json"
    diagnostic(run_cli("view", str(fixture), "--techniques", "dung"))


def test_literal_dash_output_is_a_file_not_stdout(tmp_path: Path) -> None:
    result = run_cli("version", "-o", "./-", cwd=tmp_path)
    assert result.returncode == 0 and result.stdout == result.stderr == b""
    assert (tmp_path / "-").read_bytes() == run_cli("version").stdout


def test_interruption_during_source_read_exits_130_without_publishing(tmp_path: Path) -> None:
    destination = tmp_path / "result.json"
    script = """
import os
import signal
import sys
from rdam.cli import main

def interrupt(signum, frame):
    os.kill(os.getpid(), signal.SIGINT)

signal.signal(signal.SIGALRM, interrupt)
signal.alarm(1)
raise SystemExit(main(['prepare', '-', '-o', sys.argv[1]]))
"""
    with subprocess.Popen([sys.executable, "-c", script, str(destination)], stdin=subprocess.PIPE,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE) as process:
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate()
            pytest.fail("source reading did not stop on SIGINT")
        stdout, stderr = process.communicate()
    problem = diagnostic(subprocess.CompletedProcess(process.args, process.returncode, stdout, stderr), 130)
    assert problem["category"] == "interrupted"
    assert not destination.exists()
    assert not tuple(tmp_path.glob(".rdam-*.tmp"))


def test_distinct_repeatable_mappings_are_preserved() -> None:
    payload = record(run_cli("capabilities", "--technique-model", "toulmin=anthropic:first",
                             "--technique-model", "walton=google:second"))
    models: dict[str, object] = {}
    for entry in json_array(payload["configurations"]):
        item = json_object(entry)
        technique = item["technique"]
        assert isinstance(technique, str)
        models[technique] = json_object(json_object(item["configuration"])["settings"]).get("model")
    assert models["toulmin"] == "anthropic:first"
    assert models["walton"] == "google:second"


def test_explicit_formalism_is_not_replaced_by_provider_default() -> None:
    payload = record(run_cli("analyse", "--techniques", "dung", "--structured", "dung=-",
                             "--formalism", "dung=dung_extensions", input_bytes=b'{"arguments":["a"],"attacks":[]}'))
    outcome = json_object(json_array(payload["outcomes"])[0])
    assert json_object(outcome["result"])["formalism_id"] == "dung_extensions"

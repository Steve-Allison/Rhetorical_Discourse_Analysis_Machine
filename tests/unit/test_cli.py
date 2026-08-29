"""Unit tests for the isanlp-rst CLI entrypoint."""

import json
from pathlib import Path
import pytest

from isanlp_rst.cli import main, _render_tree_ascii
from isanlp_rst.annotation_rst import DiscourseUnit


def test_cli_version(capsys: pytest.CaptureFixture[str]) -> None:
    """Verify version subcommand outputs expected package details."""
    ret = main(["version"])
    assert ret == 0
    captured = capsys.readouterr()
    assert "isanlp_rst:" in captured.out
    assert "ModernBERT" in captured.out


def test_cli_tree_ascii_rendering() -> None:
    """Verify ASCII tree formatting correctly renders hierarchy."""
    leaf1 = DiscourseUnit(id=0, text="First clause.", start=0, end=13, nuclearity="N", relation="span")
    leaf2 = DiscourseUnit(id=1, text="Second clause.", start=14, end=27, nuclearity="S", relation="elaboration")
    root = DiscourseUnit(
        id=2,
        left=leaf1,
        right=leaf2,
        nuclearity="NS",
        relation="elaboration",
        entropy=0.123,
    )

    rendered = _render_tree_ascii(root)
    assert "Node #2 [NS: elaboration]" in rendered
    assert "EDU #0 [N: span]" in rendered
    assert "EDU #1 [S: elaboration]" in rendered
    assert "First clause." in rendered
    assert "Second clause." in rendered


def test_cli_parse_text_flag(capsys: pytest.CaptureFixture[str]) -> None:
    """Verify parse command with --text flag outputs tree representation."""
    ret = main(["parse", "--text", "This is the first segment. This is the second segment.", "-f", "tree"])
    assert ret == 0
    captured = capsys.readouterr()
    assert "Node #" in captured.out or "EDU #" in captured.out


def test_cli_parse_json_format(capsys: pytest.CaptureFixture[str]) -> None:
    """Verify parse command with -f json outputs valid RstAnalysis JSON."""
    ret = main(["parse", "--text", "First sentence. Second sentence.", "-f", "json"])
    assert ret == 0
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["schema_version"] == "1.0"
    assert "nodes" in payload
    assert "primary_edges" in payload


def test_cli_parse_stats_format(capsys: pytest.CaptureFixture[str]) -> None:
    """Verify parse command with -f stats outputs structural diagnostics."""
    ret = main(["parse", "--text", "First sentence. Second sentence.", "-f", "stats"])
    assert ret == 0
    captured = capsys.readouterr()
    stats = json.loads(captured.out)
    assert "depth" in stats
    assert "n_leaves" in stats
    assert "nuclearity_counts" in stats


def test_cli_parse_output_file(tmp_path: Path) -> None:
    """Verify parse command with -o writes to file."""
    out_file = tmp_path / "output.json"
    ret = main(["parse", "--text", "First sentence. Second sentence.", "-f", "json", "-o", str(out_file)])
    assert ret == 0
    assert out_file.is_file()
    payload = json.loads(out_file.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "1.0"

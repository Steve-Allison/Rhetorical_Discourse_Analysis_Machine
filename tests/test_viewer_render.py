"""Characterization of HTML generation, notebook wrappers, render, and CLI."""

import asyncio
import io
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from isanlp_rst.rstviewer.main import (
    RenderedRST,
    _html_to_fragment,
    cli,
    render,
    rs3tohtml,
    rs3topng,
)

VIEWER_FIXTURES = Path(__file__).resolve().parent / "fixtures" / "viewer"
MINIMAL = VIEWER_FIXTURES / "minimal.rs3"
CLASSIC = VIEWER_FIXTURES / "classic_span.rs3"
CLASSIC_TEXT = CLASSIC.read_text(encoding="utf-8")


def test_rs3tohtml_structural_slices() -> None:
    html_out = rs3tohtml(str(MINIMAL))
    assert "jQuery v1.11.3" in html_out
    assert "jsPlumb" in html_out
    assert 'id="edu1"' in html_out
    assert 'id="edu2"' in html_out
    assert 'id="lg3"' in html_out
    assert 'id="g3"' in html_out
    assert html_out.count('class="edu"') == 2
    assert html_out.count('class="group"') == 1
    assert "Hello &amp; welcome" in html_out

    multi_match = html_out.partition("var multi_rel_entries = ")[2].partition(";\n")[0]
    rst_match = html_out.partition("var rst_rel_entries = ")[2].partition(";\n")[0]
    assert json.loads(multi_match) == [
        {"value": "joint_m", "label": "joint"},
        {"value": "elaboration_r", "label": "(satellite...)"},
    ]
    assert json.loads(rst_match) == [
        {"value": "elaboration_r", "label": "elaboration"},
    ]


def test_rendered_rst_repr_html_contract() -> None:
    hidden = RenderedRST("<html/>", already_displayed=True, display_override="<div/>")
    assert hidden._repr_html_() == ""
    override = RenderedRST("<html/>", already_displayed=False, display_override="<div/>")
    assert override._repr_html_() == "<div/>"
    plain = RenderedRST("<html/>", already_displayed=False)
    assert plain._repr_html_() == "<html/>"


def test_html_to_fragment_keeps_assets_and_body_inner() -> None:
    frag = _html_to_fragment(
        "<html><head><style>a{}</style><script>x</script><title>t</title></head>"
        "<body><p>hi</p></body></html>"
    )
    assert frag == "<style>a{}</style><script>x</script><p>hi</p>"


def test_render_from_path_string_and_io() -> None:
    from_path = render(str(CLASSIC), display_inline=False)
    from_string = render(CLASSIC_TEXT, display_inline=False)
    from_io = render(io.StringIO(CLASSIC_TEXT), display_inline=False)
    for html_out in (from_path, from_string, from_io):
        assert isinstance(html_out, RenderedRST)
        assert "nucleus text" in html_out
        assert "satellite text" in html_out
        assert 'id="edu1"' in html_out
    assert "classic_span.rs3" in from_path


def test_render_unlinks_temp_file_for_string_source() -> None:
    created: list[str] = []
    real_named = tempfile.NamedTemporaryFile

    def _recording_named_temporary_file(*args, **kwargs):
        handle = real_named(*args, **kwargs)
        created.append(handle.name)
        return handle

    with patch("isanlp_rst.rstviewer.main.tempfile.NamedTemporaryFile", _recording_named_temporary_file):
        render(CLASSIC_TEXT, display_inline=False)

    assert created
    for path in created:
        assert not Path(path).exists()


def test_cli_writes_html_to_stdout(capsys: pytest.CaptureFixture[str]) -> None:
    cli([str(MINIMAL)])
    captured = capsys.readouterr()
    assert "jQuery v1.11.3" in captured.out
    assert 'id="edu1"' in captured.out
    assert captured.err == ""


def test_rs3topng_refuses_running_event_loop() -> None:
    async def _call() -> None:
        rs3topng(str(MINIMAL))

    with pytest.raises(RuntimeError, match="Detected running asyncio loop"):
        asyncio.run(_call())

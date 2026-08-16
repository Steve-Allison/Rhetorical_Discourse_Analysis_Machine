"""Unit tests for viewer convenience helpers in ``isanlp_rst``."""

from pathlib import Path
from unittest.mock import patch

from isanlp_rst import to_html


def test_to_html_returns_string_and_writes_file(tmp_path: Path) -> None:
    """When ``html_path`` is set, ``to_html`` must write the file AND
    return the HTML string (docstring contract)."""
    rs3 = tmp_path / "tree.rs3"
    rs3.write_text("<rst/>", encoding="utf-8")
    out = tmp_path / "out.html"

    with patch("isanlp_rst._rst_main.rs3tohtml", return_value="<html/>") as mock_rs3:
        result = to_html(rs3, html_path=out)

    mock_rs3.assert_called_once()
    assert result == "<html/>"
    assert out.read_text(encoding="utf-8") == "<html/>"

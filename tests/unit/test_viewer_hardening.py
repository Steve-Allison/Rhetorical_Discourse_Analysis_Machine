"""Viewer hardening: XXE posture, HTML escape, per-render SQLite."""

from pathlib import Path

import pytest

from isanlp_rst.rstviewer.main import rs3tohtml
from isanlp_rst.rstviewer.rstweb_reader import read_rst
from isanlp_rst.rstviewer.rstweb_sql import _resolve_dbpath, temporary_db

VIEWER_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "viewer"
MINIMAL_RS3 = (VIEWER_FIXTURES / "minimal.rs3").read_text(encoding="utf-8")


def _write_rs3(tmp_path: Path, name: str, body: str) -> Path:
    path = tmp_path / name
    path.write_text(body, encoding="utf-8")
    return path


def test_rs3tohtml_escapes_edu_text(tmp_path: Path) -> None:
    # Entities in the RS3 become literal ``<script>`` in node.text after parse;
    # HTML output must escape them again.
    rs3 = _write_rs3(
        tmp_path,
        "xss.rs3",
        MINIMAL_RS3.replace(
            "Hello &amp; welcome",
            "&lt;script&gt;alert(1)&lt;/script&gt;",
        ),
    )
    html_out = rs3tohtml(str(rs3))
    assert "<script>alert(1)</script>" not in html_out
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html_out


def test_rs3tohtml_escapes_basename_in_header(tmp_path: Path) -> None:
    rs3 = _write_rs3(tmp_path, 'evil"name.rs3', MINIMAL_RS3)
    html_out = rs3tohtml(str(rs3))
    assert 'evil"name.rs3' not in html_out
    assert "evil&quot;name.rs3" in html_out


def test_rs3tohtml_relation_options_use_json_entries(tmp_path: Path) -> None:
    rs3 = _write_rs3(tmp_path, "opts.rs3", MINIMAL_RS3)
    html_out = rs3tohtml(str(rs3))
    assert "var multi_rel_entries =" in html_out
    assert "var rst_rel_entries =" in html_out
    assert 'var multi_options = "' not in html_out


def test_xxe_external_entity_does_not_expand(tmp_path: Path) -> None:
    secret = tmp_path / "secret.txt"
    secret.write_text("TOPSECRET", encoding="utf-8")
    # File URI for local entity — must not be loaded.
    entity = secret.resolve().as_uri()
    evil = f"""\
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE rst [
  <!ENTITY xxe SYSTEM "{entity}">
]>
<rst>
  <header>
    <relations>
      <rel name="elaboration" type="rst"/>
    </relations>
  </header>
  <body>
    <segment id="1" parent="0" relname="elaboration">&xxe;</segment>
  </body>
</rst>
"""
    rs3 = _write_rs3(tmp_path, "xxe.rs3", evil)
    rel_hash: dict = {}
    result = read_rst(str(rs3), rel_hash)
    # Either parse fails closed, or segments load without secret contents.
    if isinstance(result, str):
        assert "TOPSECRET" not in result
    else:
        texts = " ".join(n.text or "" for n in result.values())
        assert "TOPSECRET" not in texts


def test_temporary_db_unlinks_and_requires_context(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="No active viewer SQLite"):
        _resolve_dbpath()

    with temporary_db() as path:
        assert Path(path).is_file()
        assert _resolve_dbpath() == path
    assert not Path(path).exists()

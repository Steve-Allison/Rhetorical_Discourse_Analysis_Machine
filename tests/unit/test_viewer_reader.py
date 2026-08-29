"""Characterization of RS3 / text / relation-file parsing."""

from pathlib import Path

from isanlp_rst.rstviewer.rstweb_reader import read_relfile, read_rst, read_text

VIEWER_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "viewer"
MINIMAL = VIEWER_FIXTURES / "minimal.rs3"
NO_PARENT = VIEWER_FIXTURES / "no_parent.rs3"
SCHEMA = VIEWER_FIXTURES / "schema.rs3"
EMPTY_BODY = VIEWER_FIXTURES / "empty_body.rs3"


def test_read_rst_happy_path_suffixes() -> None:
    rel_hash: dict[str, str] = {}
    nodes = read_rst(str(MINIMAL), rel_hash)
    assert isinstance(nodes, dict)
    assert rel_hash == {"elaboration_r": "rst", "joint_m": "multinuc"}
    assert nodes["1"].parent == "3"
    assert nodes["1"].relname == "elaboration_r"
    assert nodes["2"].relname == "joint_m"
    assert nodes["3"].parent == "0"
    assert nodes["1"].text == "Hello & welcome"


def test_read_rst_missing_parent_becomes_zero() -> None:
    rel_hash: dict[str, str] = {}
    nodes = read_rst(str(NO_PARENT), rel_hash)
    assert isinstance(nodes, dict)
    assert nodes["1"].parent == "0"
    assert nodes["1"].relname == "elaboration_r"


def test_read_rst_schema_relation_becomes_span_r_on_root() -> None:
    rel_hash: dict[str, str] = {}
    nodes = read_rst(str(SCHEMA), rel_hash)
    assert isinstance(nodes, dict)
    assert "schemarel" not in rel_hash
    assert rel_hash == {"elaboration_r": "rst"}
    # Root parent is not in element_types, so the schema→span rewrite still gets _r.
    assert nodes["1"].relname == "span_r"


def test_read_rst_invalid_xml_returns_message(tmp_path: Path) -> None:
    rs3 = tmp_path / "bad.rs3"
    rs3.write_text("not xml", encoding="utf-8")
    assert read_rst(str(rs3), {}) == "Invalid .rs3 file"


def test_read_rst_empty_body_returns_warning_html() -> None:
    result = read_rst(str(EMPTY_BODY), {})
    assert result == '<div class="warn">No segment elements found in .rs3 file</div>'


def test_read_rst_unreadable_file_returns_message(tmp_path: Path) -> None:
    missing = tmp_path / "nope.rs3"
    result = read_rst(str(missing), {})
    assert isinstance(result, str)
    assert result.startswith("Unable to read '")
    assert "No such file or directory" in result


def test_read_text_fills_default_relations(tmp_path: Path) -> None:
    text_path = tmp_path / "lines.txt"
    text_path.write_text("one line\ntwo line\n", encoding="utf-8")
    rel_hash: dict[str, str] = {}
    nodes = read_text(str(text_path), rel_hash)
    assert rel_hash == {"elaboration_r": "rst", "joint_m": "multinuc"}
    assert nodes["1"].text == "one line"
    assert nodes["1"].relname == "elaboration_r"
    assert nodes["1"].relkind == "rst"
    assert nodes["2"].text == "two line"
    assert nodes["2"].kind == "edu"
    assert nodes["2"].parent == "0"


def test_read_relfile_parses_tab_rows(tmp_path: Path) -> None:
    rel_path = tmp_path / "rels.txt"
    rel_path.write_text(
        "elaboration\trst\njoint\tmultinuc\nignored\nspanish\trst\n",
        encoding="utf-8",
    )
    assert read_relfile(str(rel_path)) == {
        "elaboration_r": "rst",
        "joint_m": "multinuc",
        "spanish_r": "rst",
    }

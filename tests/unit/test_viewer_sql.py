"""Characterization of the per-render SQLite API, including editor mutators."""

from pathlib import Path

from rdam.rst.rstviewer import rstweb_sql
from rdam.rst.rstviewer.rstweb_sql import (
    NODE,
    count_children,
    get_children,
    get_def_rel,
    get_kind,
    get_left_right,
    get_max_right,
    get_multinuc_children_lr,
    get_parent,
    get_rel,
    get_rst_doc,
    get_rst_rels,
    import_document,
    insert_seg,
    merge_seg_forward,
    node_exists,
    read_rst,
    temporary_db,
    update_parent,
)

VIEWER_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "viewer"
MINIMAL = VIEWER_FIXTURES / "minimal.rs3"
TWO_EDU = VIEWER_FIXTURES / "two_edu.rs3"


def test_sql_reexports_reader_and_node_names() -> None:
    assert rstweb_sql.read_rst is read_rst
    assert rstweb_sql.NODE is NODE
    assert rstweb_sql.get_left_right is get_left_right
    assert callable(rstweb_sql.insert_seg)
    assert callable(rstweb_sql.read_text)
    assert callable(rstweb_sql.read_relfile)


def test_import_and_query_minimal_tree() -> None:
    with temporary_db():
        import_document(str(MINIMAL), "proj", "user")
        rows = get_rst_doc("minimal.rs3", "proj", "user")
        assert rows == [
            ("1", 1.0, 1.0, "3", 0.0, "edu", "Hello & welcome", "elaboration_r", "minimal.rs3", "proj", "user"),
            ("2", 2.0, 2.0, "3", 0.0, "edu", "second EDU", "joint_m", "minimal.rs3", "proj", "user"),
            ("3", 2.0, 2.0, "0", 0.0, "multinuc", "", "", "minimal.rs3", "proj", "user"),
        ]
        assert get_rst_rels("minimal.rs3", "proj") == [
            ("elaboration_r", "rst"),
            ("joint_m", "multinuc"),
        ]
        assert get_def_rel("rst", "minimal.rs3", "proj") == "elaboration_r"
        assert get_def_rel("multinuc", "minimal.rs3", "proj") == "joint_m"
        assert get_max_right("minimal.rs3", "proj", "user") == 2.0
        assert get_multinuc_children_lr("3", "minimal.rs3", "proj", "user") == [2, 2]
        assert get_kind("3", "minimal.rs3", "proj", "user") == "multinuc"
        assert get_rel("1", "minimal.rs3", "proj", "user") == "elaboration_r"
        assert get_parent("1", "minimal.rs3", "proj", "user") == "3"
        assert get_children("3", "minimal.rs3", "proj", "user") == [("1",), ("2",)]
        assert count_children("3", "minimal.rs3", "proj", "user") == 2


def test_update_parent_moves_rst_child_and_keeps_multinuc() -> None:
    with temporary_db():
        import_document(str(MINIMAL), "proj", "user")
        update_parent("1", "0", "minimal.rs3", "proj", "user")
        assert get_parent("1", "minimal.rs3", "proj", "user") == "0"
        assert get_rel("1", "minimal.rs3", "proj", "user") == "elaboration_r"
        assert get_parent("2", "minimal.rs3", "proj", "user") == "3"
        assert node_exists("3", "minimal.rs3", "proj", "user")


def test_update_parent_last_multinuc_child_deletes_parent() -> None:
    with temporary_db():
        import_document(str(MINIMAL), "proj", "user")
        update_parent("1", "0", "minimal.rs3", "proj", "user")
        update_parent("2", "0", "minimal.rs3", "proj", "user")
        assert not node_exists("3", "minimal.rs3", "proj", "user")
        assert get_parent("2", "minimal.rs3", "proj", "user") == "0"
        assert get_rel("2", "minimal.rs3", "proj", "user") == "elaboration_r"


def test_insert_seg_and_merge_seg_forward_round_trip() -> None:
    with temporary_db():
        import_document(str(TWO_EDU), "proj", "user")
        insert_seg(2, "two_edu.rs3", "proj", "user")
        rows = get_rst_doc("two_edu.rs3", "proj", "user")
        texts = [(row[0], row[5], row[6], row[3]) for row in rows]
        assert texts == [
            ("1", "edu", "alpha beta", "0"),
            ("2", "edu", "gamma", "0"),
            ("3", "edu", "delta epsilon", "0"),
        ]
        merge_seg_forward(2, "two_edu.rs3", "proj", "user")
        merged = [(row[0], row[6], row[3]) for row in get_rst_doc("two_edu.rs3", "proj", "user")]
        assert merged == [
            ("1", "alpha beta gamma", "0"),
            ("2", "delta epsilon", "0"),
        ]

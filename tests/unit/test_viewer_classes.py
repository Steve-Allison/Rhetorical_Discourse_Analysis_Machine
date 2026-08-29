"""Characterization of NODE / SEGMENT and the parent-chain walks."""

from pathlib import Path

from isanlp_rst.rstviewer.rstweb_classes import NODE, SEGMENT, get_depth, get_left_right
from isanlp_rst.rstviewer.rstweb_reader import read_rst

VIEWER_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "viewer"
MINIMAL = VIEWER_FIXTURES / "minimal.rs3"
CLASSIC = VIEWER_FIXTURES / "classic_span.rs3"


def _assign_html_relkinds(nodes: dict, rel_hash: dict[str, str]) -> None:
    """Match ``rs3tohtml``: relkind comes from the relation table, else ``span``."""
    for node in nodes.values():
        node.relkind = rel_hash.get(node.relname, "span")


def test_segment_tokens_are_a_split_snapshot() -> None:
    seg = SEGMENT("1", "hello world  extra")
    assert seg.tokens == ["hello", "world", "", "extra"]
    assert seg.id == "1"
    assert seg.text == "hello world  extra"


def test_node_copies_depth_to_sortdepth() -> None:
    node = NODE("1", 1, 1, "0", 3, "edu", "hi", "elaboration_r", "rst")
    assert node.sortdepth == 3
    assert node.depth == 3


def test_minimal_multinuc_left_right_from_read() -> None:
    rel_hash: dict[str, str] = {}
    nodes = read_rst(str(MINIMAL), rel_hash)
    assert isinstance(nodes, dict)
    assert rel_hash == {"elaboration_r": "rst", "joint_m": "multinuc"}
    assert nodes["1"].left == 1 and nodes["1"].right == 1
    assert nodes["2"].left == 2 and nodes["2"].right == 2
    # Only the multinuc child expands the parent; the RST satellite does not.
    assert nodes["3"].left == 2 and nodes["3"].right == 2
    assert nodes["1"].relname == "elaboration_r"
    assert nodes["2"].relname == "joint_m"
    assert nodes["3"].kind == "multinuc"


def test_rst_satellite_does_not_increment_graphical_depth() -> None:
    rel_hash: dict[str, str] = {}
    nodes = read_rst(str(MINIMAL), rel_hash)
    assert isinstance(nodes, dict)
    _assign_html_relkinds(nodes, rel_hash)
    for key in nodes:
        get_depth(nodes[key], nodes[key], nodes)

    # RST satellite under a multinuc: graphical depth stays 0.
    assert nodes["1"].depth == 0
    assert nodes["1"].sortdepth == 0
    # Multinuc child: both depth counters increment.
    assert nodes["2"].depth == 1
    assert nodes["2"].sortdepth == 1
    assert nodes["3"].depth == 0


def test_span_child_increments_depth_satellite_does_not() -> None:
    rel_hash: dict[str, str] = {}
    nodes = read_rst(str(CLASSIC), rel_hash)
    assert isinstance(nodes, dict)
    _assign_html_relkinds(nodes, rel_hash)
    for key in nodes:
        get_depth(nodes[key], nodes[key], nodes)
    for key in nodes:
        if nodes[key].kind == "edu":
            get_left_right(key, nodes, 0, 0, rel_hash)

    assert nodes["1"].relname == "span"
    assert nodes["1"].depth == 1
    assert nodes["2"].relname == "elaboration_r"
    assert nodes["2"].depth == 0
    # Parent coverage comes from the span child only.
    assert nodes["3"].left == 1
    assert nodes["3"].right == 1

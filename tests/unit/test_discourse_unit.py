"""Comprehensive unit tests for native DiscourseUnit, RS3 Exporters, and backward compatibility."""

import importlib
from pathlib import Path

from isanlp_rst.annotation_rst import (
    DiscourseUnit,
    Exporter,
    ForestExporter,
    Group,
    Root,
    Segment,
    register_isanlp_compat,
)
from isanlp_rst.utils.serialization import tree_from_dict, tree_to_dict


def test_discourse_unit_leaf_creation():
    unit = DiscourseUnit(id=1, text="This is a test.", start=0, end=15, relation="elementary")
    assert unit.id == 1
    assert unit.text == "This is a test."
    assert unit.start == 0
    assert unit.end == 15
    assert unit.relation == "elementary"
    assert unit.nuclearity == ""
    assert unit.left is None
    assert unit.right is None
    assert repr(unit) == "(id=1, start=0, end=15)"


def test_discourse_unit_internal_node():
    left = DiscourseUnit(id=1, text="Left clause", start=0, end=11, relation="elementary")
    right = DiscourseUnit(id=2, text="right clause", start=12, end=24, relation="elementary")
    parent = DiscourseUnit(
        id=3,
        left=left,
        right=right,
        text="Left clause right clause",
        relation="elaboration",
        nuclearity="NS",
        proba=0.95,
        entropy=0.08,
    )
    assert parent.id == 3
    assert parent.start == 0
    assert parent.end == 24
    assert parent.relation == "elaboration"
    assert parent.nuclearity == "NS"
    assert parent.proba == 0.95
    assert parent.entropy == 0.08

    s = str(parent)
    assert "id: 3" in s
    assert "relation: elaboration" in s
    assert "nuclearity: NS" in s


def test_discourse_unit_textfields_manipulation():
    full_text = "Primary sentence. Secondary expansion."
    left = DiscourseUnit(id=1, text="Primary sentence.", start=0, end=17)
    right = DiscourseUnit(id=2, text="Secondary expansion.", start=18, end=38)
    parent = DiscourseUnit(id=3, left=left, right=right, relation="elaboration", nuclearity="NS")

    parent.clear_textfields()
    assert parent.text == ""
    assert left.text == ""
    assert right.text == ""

    parent.fill_textfields(full_text)
    assert left.text == "Primary sentence."
    assert right.text == "Secondary expansion."


def test_discourse_unit_to_rs3_export(tmp_path: Path):
    left = DiscourseUnit(id=1, text="First statement.", start=0, end=16, relation="elementary")
    right = DiscourseUnit(id=2, text="second statement.", start=17, end=34, relation="elementary")
    root = DiscourseUnit(
        id=3,
        left=left,
        right=right,
        text="First statement. second statement.",
        relation="elaboration",
        nuclearity="NS",
    )

    rs3_file = tmp_path / "sample.rs3"
    root.to_rs3(rs3_file)
    assert rs3_file.is_file()

    content = rs3_file.read_text(encoding="utf-8")
    assert "<rst>" in content
    assert "<header>" in content
    assert '<rel name="elaboration" type="rst" />' in content
    assert "<body>" in content
    assert "First statement." in content
    assert "second statement." in content
    assert "</rst>" in content


def test_forest_exporter(tmp_path: Path):
    tree1 = DiscourseUnit(id=1, text="Solo tree 1", start=0, end=11, relation="elementary")
    tree2 = DiscourseUnit(id=2, text="Solo tree 2", start=12, end=23, relation="elementary")

    forest_file = tmp_path / "forest.rs3"
    exporter = ForestExporter(encoding="utf-8")
    exporter([tree1, tree2], forest_file)
    assert forest_file.is_file()

    content = forest_file.read_text(encoding="utf-8")
    assert "<rst>" in content
    assert "Solo tree 1" in content
    assert "Solo tree 2" in content


def test_tree_dict_roundtrip():
    left = DiscourseUnit(id=1, text="Left EDU", start=0, end=8, relation="elementary")
    right = DiscourseUnit(id=2, text="Right EDU", start=9, end=18, relation="elementary")
    root = DiscourseUnit(
        id=3,
        left=left,
        right=right,
        text="Left EDU Right EDU",
        relation="contrast",
        nuclearity="NN",
        proba=0.88,
        entropy=0.12,
    )

    d = tree_to_dict(root)
    reconstructed = tree_from_dict(d)
    assert reconstructed is not None

    assert reconstructed.id == root.id
    assert reconstructed.relation == root.relation
    assert reconstructed.nuclearity == root.nuclearity
    assert reconstructed.proba == root.proba
    assert reconstructed.entropy == root.entropy
    assert reconstructed.left is not None and reconstructed.left.text == "Left EDU"
    assert reconstructed.right is not None and reconstructed.right.text == "Right EDU"


def test_xml_structural_elements():
    seg_root = Segment(_id=0, parent=-2, relname="", text="Raw <text> & test")
    assert seg_root.id == 1
    assert seg_root.parent == -1
    assert "Raw &lt;text&gt; &amp; test" in str(seg_root)
    assert 'parent="' not in str(seg_root)

    seg_child = Segment(_id=1, parent=2, relname="elaboration", text="Child text")
    assert seg_child.id == 2
    assert seg_child.parent == 3
    assert 'parent="3"' in str(seg_child)
    assert 'relname="elaboration"' in str(seg_child)

    group = Group(_id=2, type="span", parent=0, relname="span")
    assert group.id == 3
    assert group.parent == 1
    assert str(group) == '<group id="3" type="span" parent="1" relname="span"/>'

    root_group = Root(_id=3, type="multinuc")
    assert root_group.id == 4
    assert root_group.parent == 0
    assert str(root_group) == '<group id="4" type="multinuc"/>'


def test_isanlp_annotation_rst_compatibility_shim():
    register_isanlp_compat()

    # Verify that importing from isanlp.annotation_rst resolves to our DiscourseUnit
    isanlp_module = importlib.import_module("isanlp.annotation_rst")
    assert hasattr(isanlp_module, "DiscourseUnit")
    assert isanlp_module.DiscourseUnit is DiscourseUnit
    assert isanlp_module.Exporter is Exporter

    compat_unit = isanlp_module.DiscourseUnit(id=10, text="Compat unit", start=0, end=11)
    assert isinstance(compat_unit, DiscourseUnit)
    assert compat_unit.id == 10

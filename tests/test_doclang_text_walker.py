"""Regression tests for exactly-once DocLang text traversal."""

from lxml import etree

from isanlp_rst.doclang.harvester import harvest_doclang_tables, harvest_doclang_text
from isanlp_rst.doclang.text_walker import body_text


def _tree(xml: bytes) -> etree._ElementTree:
    return etree.ElementTree(etree.fromstring(xml))


def test_nested_metadata_and_its_content_are_excluded_but_tail_is_preserved() -> None:
    tree = _tree(
        b"<doclang><text>Before <bold>bold <description>derived</description>after</bold> end</text></doclang>"
    )
    result = harvest_doclang_text(tree)
    assert [span.text for span in result.spans] == ["Before bold after end"]
    assert "derived" not in result.full_text


def test_summary_cdata_is_metadata_while_body_cdata_is_text() -> None:
    tree = _tree(
        b"<doclang><text><summary><![CDATA[derived <summary>]]></summary>"
        b"<![CDATA[body <literal>]]></text></doclang>"
    )
    result = harvest_doclang_text(tree)
    assert result.full_text == "body <literal>"


def test_nested_formatting_text_and_tails_appear_once() -> None:
    element = etree.fromstring(b"<text>A <bold>B <italic>C</italic> D</bold> E</text>")
    assert body_text(element) == "A B C D E"


def test_virtual_list_metadata_and_nested_list_are_not_duplicated() -> None:
    tree = _tree(
        b"<doclang><list><ldiv/>outer <description>meta</description>item"
        b"<list><ldiv/>nested</list> tail</list></doclang>"
    )
    result = harvest_doclang_text(tree)
    assert [span.text for span in result.spans] == ["outer item tail", "nested"]
    assert result.full_text.count("nested") == 1
    assert "meta" not in result.full_text


def test_virtual_table_metadata_and_tails_appear_once() -> None:
    tree = _tree(
        b"<doclang><table><fcel/>A<bold>B</bold>C<summary>meta</summary>D<nl/></table></doclang>"
    )
    (table,) = harvest_doclang_tables(tree)
    assert [span.text for span in table.spans] == ["ABCD"]
    assert "meta" not in table.full_text

"""Regression tests for the private exactly-once DocLang text walker."""

from lxml import etree

from rdam.rst.doclang.text_walker import body_text, iter_body_text, iter_sibling_body_text


def test_nested_metadata_and_its_content_are_excluded_but_tail_is_preserved() -> None:
    element = etree.fromstring(
        b"<text>Before <bold>bold <description>derived</description>after</bold> end</text>"
    )
    assert body_text(element) == "Before bold after end"


def test_summary_cdata_is_metadata_while_body_cdata_is_text() -> None:
    element = etree.fromstring(
        b"<text><summary><![CDATA[derived <summary>]]></summary>"
        b"<![CDATA[body <literal>]]></text>"
    )
    assert body_text(element) == "body <literal>"


def test_nested_formatting_text_and_tails_appear_once() -> None:
    element = etree.fromstring(b"<text>A <bold>B <italic>C</italic> D</bold> E</text>")
    assert body_text(element) == "A B C D E"


def test_comment_and_excluded_subtree_contents_are_omitted_without_dropping_tails() -> None:
    element = etree.fromstring(
        b"<text>before<!-- internal --> after<picture>derived</picture> tail</text>"
    )
    assert "".join(iter_body_text(element, excluded_subtrees=frozenset({"picture"}))) == "before after tail"


def test_sibling_walker_includes_eligible_body_and_tail_exactly_once() -> None:
    root = etree.fromstring(b"<root><text>body</text> tail</root>")
    assert "".join(iter_sibling_body_text(root[0])) == "body tail"


def test_sibling_walker_excludes_metadata_and_named_subtrees_but_preserves_tail() -> None:
    metadata_root = etree.fromstring(b"<root><description>derived</description> after</root>")
    excluded_root = etree.fromstring(b"<root><picture>derived</picture> after</root>")
    assert "".join(iter_sibling_body_text(metadata_root[0])) == " after"
    assert "".join(
        iter_sibling_body_text(excluded_root[0], excluded_subtrees=frozenset({"picture"}))
    ) == " after"

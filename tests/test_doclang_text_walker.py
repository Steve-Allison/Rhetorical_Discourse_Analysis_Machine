"""Regression tests for the private exactly-once DocLang text walker."""

from lxml import etree

from isanlp_rst.doclang.text_walker import body_text


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

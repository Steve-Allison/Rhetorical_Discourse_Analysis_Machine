"""Tokenise a markdown source string into a ``markdown-it-py`` token stream.

The parser is constructed from the CommonMark preset plus the
``front_matter`` plugin (YAML-style ``---...---``). When ``gfm=True``,
the GFM ``table`` rule is enabled — required for the harvester to see
``th_open`` / ``td_open`` cell tokens.

Front-matter is removed from the body token stream and surfaced
separately on ``LoadResult.front_matter`` / ``front_matter_format``;
the harvester receives a prose-only stream so YAML never lands in the
RST input text.

API verified against the live token stream emitted by ``markdown-it-py``
3.x in the active pixi env on 2026-06-12.
"""

from __future__ import annotations

from dataclasses import dataclass

from markdown_it import MarkdownIt
from markdown_it.token import Token
from mdit_py_plugins.front_matter import front_matter_plugin


@dataclass(frozen=True, slots=True)
class LoadResult:
    """The output of ``load_markdown``.

    ``tokens`` is the body token stream (front-matter removed).
    ``front_matter`` is the raw inner text between the ``---`` delimiters
    when present, otherwise ``None``. ``front_matter_format`` is
    ``"yaml"`` when the block was present, ``None`` otherwise.
    """

    tokens: tuple[Token, ...]
    front_matter: str | None
    front_matter_format: str | None


def build_parser(*, gfm: bool = True) -> MarkdownIt:
    """Construct a configured ``MarkdownIt`` instance.

    The ``front_matter`` plugin is always enabled. ``gfm=True``
    additionally enables the ``table`` rule (GFM tables tokenise to
    ``table_open`` / ``th_open`` / ``td_open`` / …) and the
    ``strikethrough`` rule (``~~text~~`` tokenises to ``s_open`` /
    ``text`` / ``s_close`` — the harvester drops the wrappers and keeps
    the text, instead of literal tildes polluting the RST input).
    """
    md = MarkdownIt("commonmark").use(front_matter_plugin)
    if gfm:
        md.enable("table")
        md.enable("strikethrough")
    return md


def load_markdown(source_text: str, *, gfm: bool = True) -> LoadResult:
    """Tokenise ``source_text`` and split out the YAML front-matter."""
    md = build_parser(gfm=gfm)
    raw_tokens = md.parse(source_text)

    front_matter_text: str | None = None
    front_matter_format: str | None = None
    body_tokens: list[Token] = []
    for tok in raw_tokens:
        if tok.type == "front_matter":
            front_matter_text = tok.content
            front_matter_format = "yaml"
            continue
        body_tokens.append(tok)

    return LoadResult(
        tokens=tuple(body_tokens),
        front_matter=front_matter_text,
        front_matter_format=front_matter_format,
    )


__all__ = ["LoadResult", "build_parser", "load_markdown"]

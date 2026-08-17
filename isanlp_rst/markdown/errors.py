"""Custom exceptions for Markdown-native RST parsing."""


class MarkdownRstError(Exception):
    """Base class for parse_markdown errors."""


class EmptyMarkdownError(MarkdownRstError):
    """The source file has no harvestable content (whitespace / front-matter only)."""


class EmptyHarvestError(MarkdownRstError):
    """The harvest produced no text (e.g. all knobs gated their content out)."""


class InputTooLargeError(MarkdownRstError):
    """Harvested text exceeds the configured length threshold."""

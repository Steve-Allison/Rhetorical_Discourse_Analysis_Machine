"""``parse_doclang`` entry point — orchestrates load → harvest → boundaries → parse → flatten.

The underlying ``Parser`` is injectable so batch consumers construct it
once and reuse it across many ``parse_doclang`` calls (otherwise each
call reloads the ~2 GB model from disk).

XML validation is delegated to the ``doclang`` PyPI package (validator-
only — see [[verified-doclang-spec]]). When ``validate_xml=True``
(default) and the package is importable, the file is run through
``doclang.validate(path)`` before parsing; otherwise the validation step
is skipped silently.
"""

from __future__ import annotations

import importlib
import subprocess
from functools import cache
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .boundaries import detect_boundaries
from .errors import (
    EmptyDoclangError,
    EmptyHarvestError,
    InputTooLargeError,
    InvalidDoclangError,
)
from .harvester import harvest_doclang_text
from .loader import local_name, parse_doclang_xml
from .mapper import flatten_tree
from .schema import DoclangRstResult

if TYPE_CHECKING:
    from isanlp_rst.parser import Parser

SCHEMA_NAME = "isanlp_rst_doclang"
SCHEMA_VERSION = "1.0"
TOOL_NAME = "isanlp_rst"
DEFAULT_MAX_HARVEST_CHARS = 200_000

# DocLang XML namespace per spec.md:219-241 (default xmlns when declared).
DOCLANG_NS = "https://www.doclang.ai/ns/v0"


# --- Helpers ----------------------------------------------------------------


def _resolve_device(device: str) -> int:
    """Translate the string device API to ``cuda_device: int`` on ``Parser``.

    ``"auto"`` → 0 (Parser auto-selects CUDA → MPS → error); ``"cpu"`` →
    -1; ``"mps"`` → 0 (integer is ignored on Apple Silicon);
    ``"cuda"`` / ``"cuda:0"`` → 0; ``"cuda:N"`` → N.
    """
    if device == "auto":
        return 0
    if device == "cpu":
        return -1
    if device == "mps":
        return 0
    if device in ("cuda", "cuda:0"):
        return 0
    if device.startswith("cuda:"):
        try:
            n = int(device.split(":", 1)[1])
        except ValueError as exc:
            raise ValueError(f"Invalid CUDA device specifier: {device!r}") from exc
        if n < 0:
            raise ValueError(f"CUDA device index must be non-negative: {device!r}")
        return n
    raise ValueError(
        f"Unrecognised device {device!r}. Expected one of "
        f"'auto', 'cpu', 'mps', 'cuda', 'cuda:N'."
    )


@cache
def _resolve_tool_version() -> str:
    """Resolve a stable tool-version string.

    Tries, in order: ``git describe --always --dirty`` (when run inside a
    git checkout); ``importlib.metadata.version("isanlp_rst")`` (when
    installed); ``"unknown"`` (fallback). Never raises.
    """
    package_dir = Path(__file__).resolve().parent.parent.parent
    try:
        result = subprocess.run(
            ["git", "describe", "--always", "--dirty"],
            cwd=package_dir,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass

    try:
        return version("isanlp_rst")
    except PackageNotFoundError:
        pass

    return "unknown"


def _resolve_inventory(hf_model_version: str, relinventory: str | None) -> str:
    """Pick the inventory string for the result metadata.

    Explicit ``relinventory`` wins; otherwise fall back to
    ``hf_model_version`` as a coarse identifier.
    """
    return relinventory or hf_model_version


def _validate_xml(path: Path) -> None:
    """Validate ``path`` against DocLang 0.5 via the ``doclang`` package.

    When the package is not importable in the active env, validation is
    skipped silently (the harvester / loader still runs). When the
    package IS importable and validation fails, raises
    ``InvalidDoclangError`` wrapping the original error.
    """
    try:
        doclang_pkg = importlib.import_module("doclang")
    except ImportError:
        return
    try:
        doclang_pkg.validate(path)
    except Exception as exc:
        raise InvalidDoclangError(
            f"{path}: failed DocLang 0.5 validation: {exc}"
        ) from exc


def _source_origin(tree: Any) -> dict[str, Any]:
    """Capture lightweight provenance from the parsed tree.

    Reports: declared namespace (or ``""``), version attribute (or default
    ``"0.5"`` per spec), and any first-level ``<head>`` child names.
    """
    root = tree.getroot()
    ns = ""
    if isinstance(root.tag, str) and root.tag.startswith("{"):
        ns = root.tag.split("}", 1)[0][1:]
    version_attr = root.get("version", "0.5")
    head_children: list[str] = []
    for child in root:
        if isinstance(child.tag, str) and local_name(child) == "head":
            head_children = [
                local_name(c) for c in child if isinstance(c.tag, str)
            ]
            break
    return {
        "format": "doclang",
        "namespace": ns,
        "version": version_attr,
        "head_children": head_children,
    }


# --- Orchestrator -----------------------------------------------------------


def parse_doclang(
    path: str | Path,
    *,
    parser: "Parser | None" = None,
    hf_model_name: str = "tchewik/isanlp_rst_v3",
    hf_model_version: str = "gumrrg",
    relinventory: str | None = None,
    device: str = "auto",
    include_picture_captions: bool = True,
    include_background: bool = False,
    include_furniture: bool = False,
    include_field_regions: bool = False,
    include_code_blocks: bool = False,
    include_formulas: bool = False,
    harvest_separator: str = "\n\n",
    note_threshold: float = 0.90,
    validate_xml: bool = True,
    max_harvest_chars: int = DEFAULT_MAX_HARVEST_CHARS,
) -> DoclangRstResult:
    """Parse a DocLang XML file and return its RST analysis.

    Args:
        path: filesystem path to a ``.dclg.xml`` file.
        parser: a pre-constructed ``Parser`` to reuse. Batch consumers
            should construct once and inject — otherwise each call
            reloads the model from disk.
        hf_model_name, hf_model_version, relinventory: passed to a new
            ``Parser`` only when ``parser is None``.
        device: ``"auto" | "cpu" | "mps" | "cuda" | "cuda:N"``. Used only
            when constructing a new ``Parser``.
        include_picture_captions: harvest ``<picture><caption>`` text.
        include_background: include layer ``"background"`` items.
        include_furniture: include layer ``"furniture"`` items plus
            ``<page_header>`` / ``<page_footer>``.
        include_field_regions: harvest text inside ``<field_region>``
            (default off — boundary-only).
        include_code_blocks: harvest ``<code>`` text (default off).
        include_formulas: harvest ``<formula>`` text (default off).
        harvest_separator: inserted between harvested spans.
        note_threshold: relations whose overlap is >= this ratio
            dominated by a single span get a ``note`` field.
        validate_xml: when True (default), validate against DocLang 0.5
            via the ``doclang`` PyPI package before parsing. Silently
            skipped when the package is not importable.
        max_harvest_chars: raise ``InputTooLargeError`` above this size.

    Raises:
        InvalidDoclangError: ``validate_xml=True`` and validation failed.
        EmptyDoclangError: the document has no harvestable content.
        EmptyHarvestError: harvest produced no text.
        InputTooLargeError: harvest exceeds ``max_harvest_chars``.
    """
    src_path = Path(path)
    if validate_xml:
        _validate_xml(src_path)

    tree = parse_doclang_xml(src_path)
    root = tree.getroot()

    body_children = [
        c for c in root
        if isinstance(c.tag, str) and local_name(c) != "head"
    ]
    if not body_children:
        raise EmptyDoclangError(
            f"DocLang document at {src_path} has no body content — nothing to harvest."
        )

    harvest = harvest_doclang_text(
        tree,
        include_picture_captions=include_picture_captions,
        include_background=include_background,
        include_furniture=include_furniture,
        include_field_regions=include_field_regions,
        include_code_blocks=include_code_blocks,
        include_formulas=include_formulas,
        harvest_separator=harvest_separator,
    )
    if not harvest.full_text:
        raise EmptyHarvestError(
            f"No text harvested from {src_path}. Document may be tables-only "
            f"or have all eligible content excluded by knobs."
        )

    if len(harvest.full_text) > max_harvest_chars:
        raise InputTooLargeError(
            f"Harvested text is {len(harvest.full_text)} chars, exceeds "
            f"max_harvest_chars={max_harvest_chars}. Chunk upstream or raise the limit."
        )

    boundaries = detect_boundaries(tree)

    if parser is None:
        from isanlp_rst.parser import Parser
        parser = Parser(
            hf_model_name=hf_model_name,
            hf_model_version=hf_model_version,
            relinventory=relinventory,
            cuda_device=_resolve_device(device),
        )

    result = parser(harvest.full_text)
    rst_tree = result["rst"][0]

    relations, edus = flatten_tree(
        rst_tree, harvest.spans, boundaries, note_threshold=note_threshold
    )

    return DoclangRstResult(
        schema_name=SCHEMA_NAME,
        schema_version=SCHEMA_VERSION,
        tool=TOOL_NAME,
        tool_version=_resolve_tool_version(),
        model_version=hf_model_version,
        inventory=_resolve_inventory(hf_model_version, relinventory),
        source=src_path.name,
        source_origin=_source_origin(tree),
        boundaries=boundaries,
        relations=relations,
        edus=edus,
    )

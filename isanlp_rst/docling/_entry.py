"""``parse_docling`` entry point — orchestrates load → harvest → boundaries → parse → flatten.

The underlying ``Parser`` is injectable so batch consumers construct it
once and reuse it across many ``parse_docling`` calls (otherwise each
call reloads the ~2 GB model from disk).
"""

from __future__ import annotations

import subprocess
from functools import cache
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import TYPE_CHECKING, Any

from docling_core.types.doc.document import DoclingDocument

from .boundaries import detect_boundaries
from .errors import EmptyDoclingError, EmptyHarvestError, InputTooLargeError
from .harvester import harvest_docling_text
from .mapper import flatten_tree
from .schema import DoclingRstResult

if TYPE_CHECKING:
    from isanlp_rst.parser import Parser

SCHEMA_NAME = "isanlp_rst_docling"
SCHEMA_VERSION = "1.0"
TOOL_NAME = "isanlp_rst"
DEFAULT_MAX_HARVEST_CHARS = 200_000


# --- Helpers ----------------------------------------------------------------


def _resolve_device(device: str) -> int:
    """Translate the string device API to ``cuda_device: int`` on ``Parser``.

    Per plan §Decisions: ``"auto"`` → 0 (Parser auto-selects CUDA → MPS →
    error); ``"cpu"`` → -1; ``"mps"`` → 0 (integer is ignored on Apple
    Silicon); ``"cuda"`` / ``"cuda:0"`` → 0; ``"cuda:N"`` → N.
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


def _serialise_source_origin(origin: Any) -> dict[str, Any]:
    """Serialise ``doc.origin`` (a Pydantic model) to a JSON-safe dict.

    Returns ``{}`` when origin is None.
    """
    if origin is None:
        return {}
    if hasattr(origin, "model_dump"):
        return origin.model_dump(mode="json")
    return {}


def _resolve_inventory(hf_model_version: str, relinventory: str | None) -> str:
    """Pick the inventory string for the result metadata.

    Explicit ``relinventory`` wins; otherwise fall back to
    ``hf_model_version`` as a coarse identifier. ASSUMED imperfect for
    UniRST without an explicit ``relinventory`` (the parser actually uses
    ``relinventory_idx=0``'s dataset); revisit if a consumer needs
    precise inventory reporting at result-time.
    """
    return relinventory or hf_model_version


# --- Orchestrator -----------------------------------------------------------


def parse_docling(
    path: str | Path,
    *,
    parser: "Parser | None" = None,
    hf_model_name: str = "tchewik/isanlp_rst_v3",
    hf_model_version: str = "gumrrg",
    relinventory: str | None = None,
    device: str = "auto",
    include_picture_descriptions: bool = True,
    include_slide_notes: bool = True,
    include_furniture: bool = False,
    harvest_separator: str = "\n\n",
    coalesce_speaker_turns: bool = True,
    note_threshold: float = 0.90,
    max_harvest_chars: int = DEFAULT_MAX_HARVEST_CHARS,
) -> DoclingRstResult:
    """Parse a Docling JSON file and return its RST analysis.

    Args:
        path: filesystem path to a Docling JSON file.
        parser: a pre-constructed ``Parser`` to reuse. Batch consumers
            should construct once and inject — otherwise each call
            reloads the model from disk.
        hf_model_name, hf_model_version, relinventory: passed to a new
            ``Parser`` only when ``parser is None``.
        device: ``"auto" | "cpu" | "mps" | "cuda" | "cuda:N"``. Used only
            when constructing a new ``Parser``.
        include_picture_descriptions: harvest
            ``picture.meta.description.text`` when present.
        include_slide_notes: include ``ContentLayer.NOTES`` items.
        include_furniture: include ``ContentLayer.FURNITURE`` items.
        harvest_separator: inserted between harvested spans.
        coalesce_speaker_turns: VTT only — coalesce consecutive
            same-voice runs into one ``turn-K`` boundary.
        note_threshold: relations whose overlap is >= this ratio
            dominated by a single span get a ``note`` field.
        max_harvest_chars: raise ``InputTooLargeError`` above this size.

    Raises:
        EmptyDoclingError: the document has no body content.
        EmptyHarvestError: harvest produced no text.
        InputTooLargeError: harvest exceeds ``max_harvest_chars``.
    """
    src_path = Path(path)
    doc = DoclingDocument.load_from_json(src_path)

    body_children = getattr(getattr(doc, "body", None), "children", None) or ()
    if not body_children:
        raise EmptyDoclingError(
            f"DoclingDocument at {src_path} has an empty body — nothing to harvest."
        )

    harvest = harvest_docling_text(
        doc,
        include_picture_descriptions=include_picture_descriptions,
        include_slide_notes=include_slide_notes,
        include_furniture=include_furniture,
        harvest_separator=harvest_separator,
    )
    if not harvest.full_text:
        raise EmptyHarvestError(
            f"No text harvested from {src_path}. Document may be tables-only or "
            f"have all content layers filtered out."
        )

    if len(harvest.full_text) > max_harvest_chars:
        raise InputTooLargeError(
            f"Harvested text is {len(harvest.full_text)} chars, exceeds "
            f"max_harvest_chars={max_harvest_chars}. Chunk upstream or raise the limit."
        )

    boundaries = detect_boundaries(doc, coalesce_speaker_turns=coalesce_speaker_turns)

    if parser is None:
        from isanlp_rst.parser import Parser  # lazy import — avoids loading on every import
        parser = Parser(
            hf_model_name=hf_model_name,
            hf_model_version=hf_model_version,
            relinventory=relinventory,
            cuda_device=_resolve_device(device),
        )

    result = parser(harvest.full_text)
    tree = result["rst"][0]

    relations, edus = flatten_tree(
        tree, harvest.spans, boundaries, note_threshold=note_threshold
    )

    return DoclingRstResult(
        schema_name=SCHEMA_NAME,
        schema_version=SCHEMA_VERSION,
        tool=TOOL_NAME,
        tool_version=_resolve_tool_version(),
        model_version=hf_model_version,
        inventory=_resolve_inventory(hf_model_version, relinventory),
        source=src_path.name,
        source_origin=_serialise_source_origin(getattr(doc, "origin", None)),
        boundaries=boundaries,
        relations=relations,
        edus=edus,
    )

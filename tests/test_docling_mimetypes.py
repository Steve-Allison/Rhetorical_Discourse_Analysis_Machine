"""Production MIME registration for Docling ImageRef validation."""

from __future__ import annotations

import mimetypes
from pathlib import Path

import pytest
from docling_core.types.doc.document import DoclingDocument
from pydantic import ValidationError

import isanlp_rst.docling._mimetypes as mime_mod
from isanlp_rst.docling._mimetypes import ensure_docling_mimetypes

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "docling"
PPTX_FIXTURE = FIXTURES / "pptx.docling.json"


def _clear_webp_mapping() -> str | None:
    """Remove ``.webp`` from the stdlib MIME map; return prior value if any."""
    prior = mimetypes.types_map.pop(".webp", None)
    # common_types can shadow types_map on some platforms.
    mimetypes.common_types.pop(".webp", None)
    return prior


def test_ensure_docling_mimetypes_makes_webp_pptx_loadable() -> None:
    """Production registration — not conftest — must make WebP fixtures load.

    Forces the platform gap by clearing ``.webp``, then asserts
    ``ensure_docling_mimetypes`` restores loadability.
    """
    prior = _clear_webp_mapping()
    # Reset the module latch so ensure() actually re-registers.
    mime_mod._REGISTERED = False

    with pytest.raises(ValidationError, match="image/webp"):
        DoclingDocument.load_from_json(str(PPTX_FIXTURE))

    ensure_docling_mimetypes()
    doc = DoclingDocument.load_from_json(str(PPTX_FIXTURE))
    assert doc is not None

    # Restore prior host mapping for other tests in this process.
    if prior is not None:
        mimetypes.add_type(prior, ".webp")

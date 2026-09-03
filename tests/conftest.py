"""Pytest session fixtures / env bootstrap for the isanlp_rst suite.

Registers ``image/webp`` with the stdlib ``mimetypes`` database. Some
platforms' default ``types_map`` omit it, and ``docling-core``'s
``ImageRef`` pydantic validator rejects unknown MIME strings when loading
Docling JSON fixtures — even though the fixture correctly uses WebP
(``.webp`` URIs). This is a platform MIME-database gap, not a Docling
content-type preference.
"""

import mimetypes
import os

import pytest

# Idempotent: add_type replaces any prior mapping for the extension.
mimetypes.add_type("image/webp", ".webp")


@pytest.fixture
def live_model_requests() -> None:
    """Require deliberate authorization before a test calls a paid external model."""

    if os.environ.get("RDAM_RUN_LIVE_MODEL_TESTS") != "1":
        pytest.skip("set RDAM_RUN_LIVE_MODEL_TESTS=1 to authorize live model requests")

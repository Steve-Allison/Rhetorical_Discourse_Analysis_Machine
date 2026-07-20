"""Pytest session fixtures / env bootstrap for the isanlp_rst suite.

Registers ``image/webp`` with the stdlib ``mimetypes`` database. Some
platforms' default ``types_map`` omit it, and ``docling-core``'s
``ImageRef`` pydantic validator rejects unknown MIME strings when loading
Docling JSON fixtures — even though the fixture correctly uses WebP
(``.webp`` URIs). This is a platform MIME-database gap, not a Docling
content-type preference.
"""

from __future__ import annotations

import mimetypes

# Idempotent: add_type replaces any prior mapping for the extension.
mimetypes.add_type("image/webp", ".webp")

"""Platform MIME registrations required by Docling JSON validation.

``docling-core``'s ``ImageRef`` pydantic validator checks image mimetypes
against the stdlib ``mimetypes`` database. Some platforms omit
``image/webp`` from the default ``types_map``, so PPTX/Docling exports that
correctly use WebP fail to load unless we register it ourselves.
"""

import mimetypes

_REGISTERED = False


def ensure_docling_mimetypes() -> None:
    """Idempotently register MIME types Docling ImageRef may require."""
    global _REGISTERED
    if _REGISTERED:
        return
    # Idempotent even across processes that already mapped the extension.
    mimetypes.add_type("image/webp", ".webp")
    _REGISTERED = True


__all__ = ["ensure_docling_mimetypes"]

"""Immutable upstream model revisions used by the production parsers."""

from collections.abc import Mapping
from types import MappingProxyType
from typing import Final

# Retained for the separately frozen eRST scorer; these are not primary-RST defaults.
DEFAULT_ENCODER_MODEL_ID = "roberta-base"
DEFAULT_ENCODER_REVISION = "e2da8e2f811d1448a5b465c236feacd80ffbac7b"
XLM_ROBERTA_LARGE_MODEL_ID: Final = "xlm-roberta-large"
XLM_ROBERTA_LARGE_REVISION: Final = "c23d21b0620b635a76227c604d44e43a9f0ee389"
PUBLISHED_RST_REVISIONS: Final[Mapping[str, str]] = MappingProxyType({
    "gumrrg": "eb1d5745f3a18b8894ce72abad3c2a76442d1107",
    "rrtrrg": "a4d19fc65bb17f399ddcbc909c8650c2fad8e55b",
    "rstdt": "cc01afde123253fec70787f6442642f5b7634587",
    "rstreebank": "a3df81661baa4ed41755155eec141f9bf83733b4",
    "unirst": "9407970f1d9d2435b5f875a0cd14293a16646304",
})


def published_rst_revision(version: str | None) -> str | None:
    """Resolve a supported public version name to its immutable source commit."""

    if version is None:
        return None
    return PUBLISHED_RST_REVISIONS.get(version, version)

__all__ = [
    "PUBLISHED_RST_REVISIONS",
    "XLM_ROBERTA_LARGE_MODEL_ID",
    "XLM_ROBERTA_LARGE_REVISION",
    "published_rst_revision",
]

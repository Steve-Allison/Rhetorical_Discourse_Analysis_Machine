"""Immutable upstream model revisions and static family authority used by the production parsers."""

from collections.abc import Mapping
from types import MappingProxyType
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from rdam.rst.model_loading import ParserCapacity

XLM_ROBERTA_LARGE_MODEL_ID: Final = "xlm-roberta-large"
XLM_ROBERTA_LARGE_REVISION: Final = "c23d21b0620b635a76227c604d44e43a9f0ee389"
DMRST_PARSERS: Final[tuple[str, ...]] = ("gumrrg", "rstdt", "rstreebank")
UNIVERSAL_PARSERS: Final[tuple[str, ...]] = ("rrtrrg", "unirst")
AVAILABLE_VERSIONS: Final[tuple[str, ...]] = DMRST_PARSERS + UNIVERSAL_PARSERS
AVAILABLE_FAMILIES: Final[tuple[str, ...]] = ("dmrst", "unirst")
DEFAULT_HF_MODEL_NAME: Final = "tchewik/isanlp_rst_v3"
DEFAULT_HF_MODEL_VERSION: Final = "gumrrg"
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


def declared_analysis_capacity() -> ParserCapacity:
    """No checkpoint- or runtime-derived EDU maximum has been established."""

    from rdam.rst.model_loading import ParserCapacity

    return ParserCapacity(unit="edu_count", maximum=None, source="isanlp_rst.parser/edu_capacity_not_established-v1")


def family_for_runtime_contract(runtime_contract: str) -> str:
    """Resolve canonical parser family from runtime contract string."""

    prefix = "isanlp_rst.parser/"
    if not runtime_contract.startswith(prefix):
        raise ValueError(f"Invalid parser runtime contract prefix: {runtime_contract!r}")
    suffix = runtime_contract[len(prefix) :]
    family = suffix.split("-v", 1)[0]
    if family not in AVAILABLE_FAMILIES:
        raise ValueError(
            f"Unknown parser family {family!r} for contract {runtime_contract!r}. Available: {AVAILABLE_FAMILIES}"
        )
    return family


__all__ = [
    "AVAILABLE_FAMILIES",
    "AVAILABLE_VERSIONS",
    "DEFAULT_HF_MODEL_NAME",
    "DEFAULT_HF_MODEL_VERSION",
    "DMRST_PARSERS",
    "PUBLISHED_RST_REVISIONS",
    "UNIVERSAL_PARSERS",
    "XLM_ROBERTA_LARGE_MODEL_ID",
    "XLM_ROBERTA_LARGE_REVISION",
    "declared_analysis_capacity",
    "family_for_runtime_contract",
    "published_rst_revision",
]

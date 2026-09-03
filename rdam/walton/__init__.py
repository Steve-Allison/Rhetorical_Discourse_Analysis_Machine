"""rdam.walton — Walton argumentation-scheme provider for the Rhetorical Discourse Analysis Machine.

Presumptive schemes (Walton, Reed & Macagno 2008) matched over raw text, each instance
tested against that scheme's critical questions. The provider records which questions the
passage leaves open; it never answers them. LLM-backed per 006 FR-032.
"""

from importlib.metadata import PackageNotFoundError, version

from rdam.walton.provider import (
    CONTRACT_VERSION,
    FORMALISM_ID,
    INSTRUCTIONS,
    LICENCE,
    PROVIDER_ID_PREFIX,
    WaltonProvider,
    source_identity,
)
from rdam.walton.schemes import (
    SCHEMES,
    SCHEME_SET_ID,
    CriticalQuestion,
    CriticalQuestionStatus,
    Scheme,
    SchemeError,
    SchemeId,
    SchemeInstance,
    WaltonAnalysis,
)

try:
    __version__ = version("rdam")
except PackageNotFoundError:
    __version__ = "unknown"

__all__ = [
    "CONTRACT_VERSION",
    "FORMALISM_ID",
    "INSTRUCTIONS",
    "LICENCE",
    "PROVIDER_ID_PREFIX",
    "SCHEMES",
    "SCHEME_SET_ID",
    "CriticalQuestion",
    "CriticalQuestionStatus",
    "Scheme",
    "SchemeError",
    "SchemeId",
    "SchemeInstance",
    "WaltonAnalysis",
    "WaltonProvider",
    "__version__",
    "source_identity",
]

"""rdam.toulmin — Toulmin layout-of-argument provider for the Rhetorical Discourse Analysis Machine.

Toulmin's six elements (1958) over raw text, with the warrant recovered rather than
skipped: claim-and-premise extraction alone is refused, not relabelled (006 FR-019).
The provider is LLM-backed, which FR-032 makes a first-class production provider.
"""

from importlib.metadata import PackageNotFoundError, version

from rdam.toulmin.argument import (
    IncompleteLayoutError,
    LayoutError,
    Rebuttal,
    ToulminAnalysis,
    ToulminLayout,
)
from rdam.toulmin.provider import (
    CONTRACT_VERSION,
    FORMALISM_ID,
    INSTRUCTIONS,
    LICENCE,
    PROVIDER_ID_PREFIX,
    ToulminProvider,
    source_identity,
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
    "IncompleteLayoutError",
    "LayoutError",
    "Rebuttal",
    "ToulminAnalysis",
    "ToulminLayout",
    "ToulminProvider",
    "__version__",
    "source_identity",
]

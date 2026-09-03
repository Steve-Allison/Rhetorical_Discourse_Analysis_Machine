"""rdam.dung — Dung abstract argumentation provider for the Rhetorical Discourse Analysis Machine.

Formal evaluation of a supplied argument-and-attack framework under grounded, complete,
preferred, and stable semantics (Dung 1995). Never raw-text inference (FR-016).
"""

from importlib.metadata import PackageNotFoundError, version

from rdam.dung.provider import CONTRACT_VERSION, FORMALISM_ID, PROVIDER_ID, DungProvider, source_identity
from rdam.dung.semantics import (
    DEFAULT_CAPACITY,
    ArgumentationFramework,
    FrameworkCapacityError,
    FrameworkError,
    Semantics,
    evaluate,
    grounded_extension,
)

try:
    __version__ = version("rdam")
except PackageNotFoundError:
    __version__ = "unknown"

__all__ = [
    "CONTRACT_VERSION",
    "DEFAULT_CAPACITY",
    "FORMALISM_ID",
    "PROVIDER_ID",
    "ArgumentationFramework",
    "DungProvider",
    "FrameworkCapacityError",
    "FrameworkError",
    "Semantics",
    "__version__",
    "evaluate",
    "grounded_extension",
    "source_identity",
]

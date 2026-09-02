"""rdam.ibis — IBIS provider for the Rhetorical Discourse Analysis Machine.

Typed issue–position–argument structures validated under the gIBIS link grammar
(Kunz & Rittel 1970; Conklin & Begeman 1988). Records what was said; extracts nothing
from text (FR-017).
"""

from importlib.metadata import PackageNotFoundError, version

from rdam.ibis.grammar import GRAMMAR, IbisStructure, Link, Node, NodeKind, Relation, StructureError, deliberation_map
from rdam.ibis.provider import CONTRACT_VERSION, FORMALISM_ID, PROVIDER_ID, IbisProvider, packaged_decision, source_identity

try:
    __version__ = version("rdam")
except PackageNotFoundError:
    __version__ = "unknown"

__all__ = [
    "CONTRACT_VERSION",
    "FORMALISM_ID",
    "GRAMMAR",
    "PROVIDER_ID",
    "IbisProvider",
    "IbisStructure",
    "Link",
    "Node",
    "NodeKind",
    "Relation",
    "StructureError",
    "__version__",
    "deliberation_map",
    "packaged_decision",
    "source_identity",
]

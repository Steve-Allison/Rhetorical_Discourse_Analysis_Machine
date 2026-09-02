"""rdam — the Rhetorical Discourse Analysis Machine's aggregate analysis contract.

A permanently analysis-only machine that runs several discourse and argumentation
techniques natively, side by side, without collapsing them into a common formalism.
Authority: ``specs/006-rhetorical-discourse-machine/``.
"""

from importlib.metadata import PackageNotFoundError, version

from rdam._strict import SemanticVersion, Sha256Identity, StrictModel, canonical_json_bytes, semantic_sha256
from rdam.contracts import (
    AggregateAnalysis,
    AggregateRequest,
    AvailableCapability,
    CapabilityState,
    FailedOutcome,
    FormalismDeclaration,
    MachineCapabilities,
    NativeTechniqueResult,
    Outcome,
    ProviderDeclaration,
    ProviderDependencyReference,
    ProviderError,
    ProviderFailure,
    ProviderProvenance,
    ProviderRequest,
    ResultOutcome,
    Retryability,
    SourceIdentity,
    StructuredInput,
    TechniqueCapability,
    UnavailableCapability,
    UnavailableOutcome,
    UnavailableReason,
    outcome_technique,
)
from rdam.frameworks import (
    BOUNDARY_TECHNIQUES,
    FRAMEWORK_SCHEME,
    STRUCTURED_INPUT_TECHNIQUES,
    FrameworkIdentity,
    FrameworkResolutionError,
    Technique,
    framework_identities,
    technique_curie,
)
from rdam.machine import Machine, Provider
from rdam.serialization import PersistedRecord, UnsupportedRecordError, load, serialize

try:
    __version__ = version("rdam")
except PackageNotFoundError:
    __version__ = "unknown"

__all__ = [
    "BOUNDARY_TECHNIQUES",
    "FRAMEWORK_SCHEME",
    "STRUCTURED_INPUT_TECHNIQUES",
    "AggregateAnalysis",
    "AggregateRequest",
    "AvailableCapability",
    "CapabilityState",
    "FailedOutcome",
    "FormalismDeclaration",
    "FrameworkIdentity",
    "FrameworkResolutionError",
    "Machine",
    "MachineCapabilities",
    "NativeTechniqueResult",
    "Outcome",
    "PersistedRecord",
    "Provider",
    "ProviderDeclaration",
    "ProviderDependencyReference",
    "ProviderError",
    "ProviderFailure",
    "ProviderProvenance",
    "ProviderRequest",
    "ResultOutcome",
    "Retryability",
    "SemanticVersion",
    "Sha256Identity",
    "SourceIdentity",
    "StrictModel",
    "StructuredInput",
    "Technique",
    "TechniqueCapability",
    "UnavailableCapability",
    "UnavailableOutcome",
    "UnavailableReason",
    "UnsupportedRecordError",
    "__version__",
    "canonical_json_bytes",
    "framework_identities",
    "load",
    "outcome_technique",
    "semantic_sha256",
    "serialize",
    "technique_curie",
]

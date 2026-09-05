"""rdam — the Rhetorical Discourse Analysis Machine's aggregate analysis contract.

A permanently analysis-only machine that runs several discourse and argumentation
techniques natively, side by side, without collapsing them into a common formalism.
Authority: ``specs/006-rhetorical-discourse-machine/``.
"""

from importlib.metadata import PackageNotFoundError, version

from rdam._strict import SemanticVersion, Sha256Identity, StrictModel, canonical_json_bytes, semantic_sha256
from rdam._execution import ExecutionPolicy
from rdam.configuration import MachineConfig, LlmSettings, TechniqueModels, RstSettings, PublishedRstModel, LocalRstModel, ExecutionSettings
from rdam.ingest.contracts.evidence import SourceEvidenceSpan
from rdam.contracts import (
    AggregateAnalysis,
    AggregateRequest,
    PreparationRequest,
    MachinePreparation,
    ProviderConfiguration,
    BoundaryConfiguration,
    OperationFailure,
    OperationError,
    VersionInfo,
    AvailableCapability,
    CapabilityState,
    FailedOutcome,
    FormalismChoice,
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
    ResultSourceAlignment,
    Retryability,
    SourceIdentity,
    SourceArtifactRef,
    StructuredInput,
    TechniqueCapability,
    UnavailableCapability,
    UnavailableOutcome,
    UnavailableReason,
    UpstreamResultReference,
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
from rdam.composition import production_machine
from rdam.serialization import (PersistedRecord, UnsupportedRecordError, load, serialize, load_config, serialize_config,
    load_request, serialize_request, load_preparation_request, serialize_preparation_request,
    load_view_request, serialize_view_request, version_info, schema)
from rdam.interpretation import AnalysisReadingGuide, NativeInterpretationDescriptor, AnalysisView, ViewRequest, select_analysis
from rdam.summary import summarise

try:
    __version__ = version("rdam")
except PackageNotFoundError:
    __version__ = "unknown"

__all__ = [
    "schema",
    "MachineConfig", "LlmSettings", "TechniqueModels", "RstSettings", "PublishedRstModel", "LocalRstModel", "ExecutionSettings",
    "SourceEvidenceSpan", "PreparationRequest", "MachinePreparation", "ProviderConfiguration", "BoundaryConfiguration",
    "OperationFailure", "OperationError", "VersionInfo", "AnalysisReadingGuide", "NativeInterpretationDescriptor",
    "AnalysisView", "ViewRequest", "select_analysis", "summarise", "load_config", "serialize_config", "load_request", "serialize_request",
    "load_preparation_request", "serialize_preparation_request", "load_view_request", "serialize_view_request", "version_info",
    "BOUNDARY_TECHNIQUES",
    "FRAMEWORK_SCHEME",
    "STRUCTURED_INPUT_TECHNIQUES",
    "AggregateAnalysis",
    "AggregateRequest",
    "AvailableCapability",
    "CapabilityState",
    "ExecutionPolicy",
    "FailedOutcome",
    "FormalismChoice",
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
    "ResultSourceAlignment",
    "Retryability",
    "SemanticVersion",
    "Sha256Identity",
    "SourceIdentity",
    "SourceArtifactRef",
    "StrictModel",
    "StructuredInput",
    "Technique",
    "TechniqueCapability",
    "UnavailableCapability",
    "UnavailableOutcome",
    "UnavailableReason",
    "UnsupportedRecordError",
    "UpstreamResultReference",
    "__version__",
    "canonical_json_bytes",
    "framework_identities",
    "load",
    "outcome_technique",
    "production_machine",
    "semantic_sha256",
    "serialize",
    "technique_curie",
]

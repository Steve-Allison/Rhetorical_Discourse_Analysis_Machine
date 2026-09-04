"""The RST provider: ``rdam.rst`` presented to the machine through its own declaration.

Capability means the provider can run. Configured with a published parser version it is
available, because that version is one the façade knows how to load. Configured with a
local model release it is available only after the immutable manifest, compatibility,
membership, sizes, and hashes validate. That local validation is cached per provider;
neither path constructs a parser or touches the network, and the parser is constructed
only by the first ``analyse``.

Formalisms (006 data-model §Formalism): ``rst_tree`` carries ``…/rst``; ``erst_graph``
carries ``…/erst`` and is available only when a validated eRST completion bundle
resolves. Failures are ``rdam.rst``'s typed failures mapped one-to-one, same code and
same retryability, onto the machine's ``ProviderFailure``; the machine never retries.
"""

from collections.abc import Mapping
import json
from pathlib import Path
from typing import Final
from uuid import uuid4
from threading import RLock
from time import perf_counter
import sys

from rdam.rst import Parser
from rdam.rst.erst.checkpoint import resolve_default_erst_checkpoint
from rdam.ingest import (
    WRITE_CONTRACT_VERSION,
    AnalysisPolicy,
    OutputFormalism,
    ProductionIngestError,
    ProductionIngestor,
    SourceArtifact,
    serialize_contract,
)
from rdam.ingest.service import DEFAULT_ANALYSIS_POLICY
from rdam.ingest.service import declared_capacity
from rdam.ingest.contracts.preparation import (
    ContentInventory,
    ContentRequirement,
    PreparationOutcome,
    PreparationExecutionEvidence,
)
from rdam.ingest.policy import DEFAULT_PLANNING_POLICY, DEFAULT_PREPARATION_POLICY
from rdam.ingest.projection import project, bind_preparation
from rdam.rst.model_loading import ModelReleaseError, ValidatedModelRelease, load_model_release
from rdam import (
    AvailableCapability,
    FormalismDeclaration,
    NativeTechniqueResult,
    ProviderDeclaration,
    ProviderError,
    ProviderFailure,
    ProviderRequest,
    Retryability,
    SemanticVersion,
    Technique,
    UnavailableCapability,
    UnavailableReason,
    technique_curie,
)
from rdam._strict import JsonValue
from rdam._provider_provenance import provider_provenance

PACKAGE: Final = "rdam.rst"
RST_TREE: Final = "rst_tree"
ERST_GRAPH: Final = "erst_graph"
# The weights published under tchewik/isanlp_rst_v3, which every hf_model_version pulls.
PUBLISHED_WEIGHTS_LICENCE: Final = "CC BY-NC 4.0 — research and non-commercial use only (LICENSE_MODELS)"
INVALID_LOCAL_RELEASE_LICENCE: Final = "Unknown — configured local model release is unavailable or invalid"
_FORMALISM_OUTPUT: Final[Mapping[str, OutputFormalism]] = {
    RST_TREE: OutputFormalism.RST_TREE,
    ERST_GRAPH: OutputFormalism.ERST_GRAPH,
}
_FORMALISM_TECHNIQUE: Final[Mapping[str, Technique]] = {RST_TREE: Technique.RST, ERST_GRAPH: Technique.ERST}


class ProviderConfigurationError(ValueError):
    """The provider was configured with neither a parser version nor a local release."""


class RstProvider:
    """One configured ``rdam.rst`` parser, declared to the machine (006 data-model §Provider).

    Configure it either with a published parser version, which the façade fetches on
    first use, or with a local immutable model release:

        RstProvider()                                             # the default family
        RstProvider(hf_model_version="unirst", relinventory="eng.erst.gum")
        RstProvider(store=Path("models/model-releases"), release_id="gumrrg-eb1d5745f3a1")
    """

    def __init__(
        self,
        *,
        hf_model_version: str | None = None,
        store: Path | None = None,
        release_id: str | None = None,
        relinventory: str | None = None,
        device: str = "auto",
        erst_scorer_checkpoint: Path | None = None,
        cache_directory: Path | None = None,
    ) -> None:
        if (store is None) != (release_id is None):
            raise ProviderConfigurationError("a local release needs both store and release_id")
        if store is not None and hf_model_version is not None:
            raise ProviderConfigurationError("configure either a published version or a local release, not both")
        if store is None and hf_model_version is None:
            hf_model_version = Parser.DEFAULT_HF_MODEL_VERSION
        self._hf_model_version = hf_model_version
        self._store = Path(store) if store is not None else None
        self._release_id = release_id
        self._relinventory = relinventory
        self._device = device
        self._erst_checkpoint = erst_scorer_checkpoint
        self._cache_directory = cache_directory
        self._parser: Parser | None = None
        self._initialization_lock = RLock()
        self._local_release_checked = False
        self._validated_local_release: ValidatedModelRelease | None = None
        self._validated_local_family: str | None = None

    @property
    def model_identity(self) -> str:
        return self._release_id if self._release_id is not None else str(self._hf_model_version)

    @property
    def provider_id(self) -> str:
        return f"{PACKAGE}/{self.model_identity}"

    def _unavailable_reason(self) -> UnavailableReason | None:
        """Can this configuration produce a parser? Checked without loading one."""

        if self._hf_model_version is not None:
            if self._hf_model_version not in Parser.AVAILABLE_VERSIONS:
                return UnavailableReason.MODEL_UNAVAILABLE
            return None
        return None if self._inspect_local_release() is not None else UnavailableReason.MODEL_UNAVAILABLE

    def _inspect_local_release(self) -> ValidatedModelRelease | None:
        """Validate the configured immutable release once without constructing a parser."""

        with self._initialization_lock:
            return self._inspect_local_release_locked()

    def _inspect_local_release_locked(self) -> ValidatedModelRelease | None:

        if self._local_release_checked:
            return self._validated_local_release
        self._local_release_checked = True
        if self._store is None or self._release_id is None:
            return None
        try:
            release = load_model_release(self._store, self._release_id)
            family = Parser.family_for_runtime_contract(release.manifest.runtime_contract)
        except ModelReleaseError, ValueError:
            return None
        self._validated_local_release = release
        self._validated_local_family = family
        return release

    @property
    def content_requirement(self) -> ContentRequirement:
        return ContentRequirement(
            requirement_id="rst/authored-prose-v1",
            admitted_classes=DEFAULT_PREPARATION_POLICY.primary_classes,
            capacity=declared_capacity(Parser.declared_analysis_capacity()),
            boundary_preference=DEFAULT_PLANNING_POLICY.boundary_preference,
            normalization=DEFAULT_PREPARATION_POLICY.normalization,
            requires_speaker_identity=False,
        )

    @property
    def declaration(self) -> ProviderDeclaration:
        """Side-effect-free: resolves configuration and looks for a bundle; loads no model."""

        contract_version = SemanticVersion(root=WRITE_CONTRACT_VERSION)
        reason = self._unavailable_reason()
        available = AvailableCapability(provider_id=self.provider_id, contract_version=contract_version)
        capability = available if reason is None else UnavailableCapability(reason=reason)
        erst_bundle = resolve_default_erst_checkpoint(self._erst_checkpoint) is not None
        erst_capability = (
            available
            if reason is None and erst_bundle
            else UnavailableCapability(reason=reason or UnavailableReason.MODEL_UNAVAILABLE)
        )
        return ProviderDeclaration(
            provider_id=self.provider_id,
            technique=Technique.RST,
            technique_curie=technique_curie(Technique.RST),
            formalisms=(
                FormalismDeclaration(
                    formalism_id=RST_TREE,
                    technique=Technique.RST,
                    technique_curie=technique_curie(Technique.RST),
                    capability=capability,
                ),
                FormalismDeclaration(
                    formalism_id=ERST_GRAPH,
                    technique=Technique.ERST,
                    technique_curie=technique_curie(Technique.ERST),
                    capability=erst_capability,
                ),
            ),
            contract_version=contract_version,
            provenance=provider_provenance(
                package=PACKAGE,
                model_identity=self.model_identity,
                licence=self._licence(),
            ),
            capability=capability,
            requires_structured_input=False,
            content_requirement=self.content_requirement,
            # T073/T082 measured full cold initialization and inference on CPU
            # and MPS. Other devices and eRST completion remain unmeasured.
            parallel_safety=(
                "concurrent"
                if not erst_bundle
                and (self._device in {"cpu", "mps"} or (self._device == "auto" and sys.platform == "darwin"))
                else "serialized"
            ),
        )

    def _licence(self) -> str:
        """The terms the loaded weights carry, read from the release manifest when there is one."""

        if self._store is None or self._release_id is None:
            return PUBLISHED_WEIGHTS_LICENCE
        release = self._inspect_local_release()
        return release.manifest.licence if release is not None else INVALID_LOCAL_RELEASE_LICENCE

    def analyse(self, request: ProviderRequest) -> NativeTechniqueResult:
        declaration = self.declaration
        formalism_id = request.formalism_id or RST_TREE
        formalism = declaration.formalism(formalism_id)
        if formalism is None:
            raise ProviderError(
                self._failure("analyse", Retryability.NOT_RETRYABLE, "formalism_not_declared", "ValueError")
            )
        if not isinstance(formalism.capability, AvailableCapability):
            raise ProviderError(
                self._failure(
                    "analyse",
                    Retryability.NOT_RETRYABLE,
                    "provider_not_available",
                    "ValueError",
                    formalism.capability.reason.value,
                )
            )
        if request.text is None:
            raise ProviderError(self._failure("analyse", Retryability.NOT_RETRYABLE, "text_required", "ValueError"))
        try:
            parser = self._load_parser()
        except ModelReleaseError as error:
            raise ProviderError(
                self._failure(
                    "analyse",
                    Retryability.NOT_RETRYABLE,
                    "model_release_invalid",
                    "ModelReleaseError",
                    str(error),
                )
            ) from error
        policy = AnalysisPolicy.model_validate(
            {
                **DEFAULT_ANALYSIS_POLICY.model_dump(exclude={"semantic_digest"}),
                "output_formalism": _FORMALISM_OUTPUT[formalism_id],
            }
        )
        try:
            ingestor = ProductionIngestor(parser=parser)
            if request.projection is not None and request.preparation is not None:
                binding_started = perf_counter()
                inventory = request.preparation.inventory
                projection = request.projection
                semantic = bind_preparation(inventory, self.content_requirement, projection)
                preparation = PreparationOutcome(
                    semantic=semantic,
                    execution=PreparationExecutionEvidence(
                        execution_id=str(uuid4()), adapters=(), duration_ms=(perf_counter() - binding_started) * 1000.0
                    ),
                )
                outcome = ingestor.analyse_prepared(
                    preparation,
                    analysis_policy=policy,
                    cache_directory=self._cache_directory,
                )
            else:
                source = SourceArtifact.from_text(request.text, source_name=request.source.source_name or "rdam-source")
                preparation = ingestor.prepare(source, capacity=self.content_requirement.capacity)
                inventory = ContentInventory.from_preparation(preparation)
                projection = project(inventory, self.content_requirement)
                preparation = PreparationOutcome(
                    semantic=bind_preparation(inventory, self.content_requirement, projection),
                    execution=preparation.execution,
                )
                outcome = ingestor.analyse(
                    source,
                    preparation=preparation,
                    analysis_policy=policy,
                    cache_directory=self._cache_directory,
                )
        except ProductionIngestError as error:
            raise ProviderError(
                ProviderFailure(
                    technique=Technique.RST,
                    provider_id=self.provider_id,
                    failed_operation="analyse",
                    retryability=Retryability(error.failure.retryability.value),
                    code=error.failure.code,
                    exception_type="ProductionIngestError",
                    message_template=error.failure.message_template,
                    message_parameters=(
                        ("failed_stage", error.failure.failed_stage.value),
                        ("category", error.failure.category.value),
                    ),
                )
            ) from error
        payload: Mapping[str, JsonValue] = json.loads(serialize_contract(outcome))
        return NativeTechniqueResult(
            technique=_FORMALISM_TECHNIQUE[formalism_id],
            formalism_id=formalism_id,
            provider_id=self.provider_id,
            provider_contract_version=declaration.contract_version,
            source=request.source,
            payload=payload,
            provenance=declaration.provenance,
            execution_fields=_execution_fields(payload),
        )

    def _load_parser(self) -> Parser:
        with self._initialization_lock:
            return self._load_parser_locked()

    def _load_parser_locked(self) -> Parser:
        if self._parser is not None:
            return self._parser
        if self._store is not None and self._release_id is not None:
            release = self._inspect_local_release()
            if release is None or self._validated_local_family is None:
                raise ModelReleaseError("configured local model release is unavailable or invalid")
            self._parser = Parser.from_model_release(
                self._store,
                self._release_id,
                family=self._validated_local_family,
                relinventory=self._relinventory,
                device=self._device,
                erst_scorer_checkpoint=self._erst_checkpoint,
            )
            return self._parser
        self._parser = Parser(
            hf_model_version=self._hf_model_version,
            relinventory=self._relinventory,
            device=self._device,
            erst_scorer_checkpoint=self._erst_checkpoint,
        )
        return self._parser

    def _failure(
        self,
        operation: str,
        retryability: Retryability,
        code: str,
        exception_type: str,
        detail: str | None = None,
    ) -> ProviderFailure:
        return ProviderFailure(
            technique=Technique.RST,
            provider_id=self.provider_id,
            failed_operation=operation,
            retryability=retryability,
            code=code,
            exception_type=exception_type,
            message_template=code,
            message_parameters=(("detail", detail),) if detail is not None else (),
        )


def _execution_fields(payload: Mapping[str, JsonValue]) -> tuple[tuple[str, ...], ...]:
    """Declare the native contract's execution-only fields without changing its payload."""
    candidates = (
        ("execution",),
        ("semantic", "preparation", "execution"),
        ("semantic", "parser_result", "execution"),
        ("semantic", "analysis", "timing"),
        ("semantic", "analysis", "provenance", "timestamp"),
        ("semantic", "parser_result", "semantic", "analysis", "timing"),
        ("semantic", "parser_result", "semantic", "analysis", "provenance", "timestamp"),
        ("semantic", "recombination", "unit_durations_ms"),
        ("semantic", "parser_result", "semantic", "recombination", "unit_durations_ms"),
    )
    present: list[tuple[str, ...]] = []
    for path in candidates:
        current: object = payload
        for key in path:
            if not isinstance(current, Mapping) or key not in current:
                break
            current = current[key]
        else:
            present.append(path)
    return tuple(present)


__all__ = ["ERST_GRAPH", "PUBLISHED_WEIGHTS_LICENCE", "RST_TREE", "ProviderConfigurationError", "RstProvider"]

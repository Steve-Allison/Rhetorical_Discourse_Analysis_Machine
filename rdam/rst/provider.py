"""The RST provider: ``rdam.rst`` presented to the machine through its own declaration.

Capability means the provider can run. Configured with a published parser version it is
available, because that version is one the façade knows how to load. Configured with a
local model release it is available when that release is present. Neither check loads a
model or touches the network: reporting capability is cheap by contract, and the parser
is constructed on the first ``analyse``.

Formalisms (006 data-model §Formalism): ``rst_tree`` carries ``…/rst``; ``erst_graph``
carries ``…/erst`` and is available only when a validated eRST completion bundle
resolves. Failures are ``rdam.rst``'s typed failures mapped one-to-one, same code and
same retryability, onto the machine's ``ProviderFailure``; the machine never retries.
"""

from collections.abc import Mapping
import json
from pathlib import Path
from typing import Final

import rdam.rst
from rdam.rst import Parser
from rdam.rst.erst.checkpoint import resolve_default_erst_checkpoint
from rdam.rst.ingest import (
    WRITE_CONTRACT_VERSION,
    AnalysisPolicy,
    OutputFormalism,
    ProductionIngestError,
    ProductionIngestor,
    SourceArtifact,
    serialize_contract,
)
from rdam.rst.ingest.service import DEFAULT_ANALYSIS_POLICY
from rdam.rst.model_loading.release import MODEL_RELEASE_MANIFEST
from rdam import (
    AvailableCapability,
    FormalismDeclaration,
    NativeTechniqueResult,
    ProviderDeclaration,
    ProviderError,
    ProviderFailure,
    ProviderProvenance,
    ProviderRequest,
    Retryability,
    SemanticVersion,
    Technique,
    UnavailableCapability,
    UnavailableReason,
    technique_curie,
)
from rdam._strict import JsonValue

PACKAGE: Final = "rdam.rst"
RST_TREE: Final = "rst_tree"
ERST_GRAPH: Final = "erst_graph"
# The weights published under tchewik/isanlp_rst_v3, which every hf_model_version pulls.
PUBLISHED_WEIGHTS_LICENCE: Final = "CC BY-NC 4.0 — research and non-commercial use only (LICENSE_MODELS)"
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
            hf_model_version = Parser._DEFAULT_HF_MODEL_VERSION
        self._hf_model_version = hf_model_version
        self._store = Path(store) if store is not None else None
        self._release_id = release_id
        self._relinventory = relinventory
        self._device = device
        self._erst_checkpoint = erst_scorer_checkpoint
        self._cache_directory = cache_directory
        self._parser: Parser | None = None

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
        if self._store is None or self._release_id is None:
            return UnavailableReason.MODEL_UNAVAILABLE
        manifest = self._store / self._release_id / MODEL_RELEASE_MANIFEST
        return None if manifest.is_file() else UnavailableReason.MODEL_UNAVAILABLE

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
            provenance=ProviderProvenance(
                package=PACKAGE,
                version=rdam.rst.__version__,
                model_identity=self.model_identity,
                licence=self._licence(),
            ),
            capability=capability,
            requires_structured_input=False,
        )

    def _licence(self) -> str:
        """The terms the loaded weights carry, read from the release manifest when there is one."""

        if self._store is None or self._release_id is None:
            return PUBLISHED_WEIGHTS_LICENCE
        manifest = self._store / self._release_id / MODEL_RELEASE_MANIFEST
        if not manifest.is_file():
            return PUBLISHED_WEIGHTS_LICENCE
        declared = json.loads(manifest.read_text(encoding="utf-8")).get("licence")
        return declared if isinstance(declared, str) and declared else PUBLISHED_WEIGHTS_LICENCE

    def analyse(self, request: ProviderRequest) -> NativeTechniqueResult:
        declaration = self.declaration
        formalism_id = request.formalism_id or RST_TREE
        formalism = declaration.formalism(formalism_id)
        if formalism is None:
            raise ProviderError(self._failure("analyse", Retryability.NOT_RETRYABLE, "formalism_not_declared", "ValueError"))
        if not isinstance(formalism.capability, AvailableCapability):
            raise ProviderError(
                self._failure("analyse", Retryability.NOT_RETRYABLE, "provider_not_available", "ValueError", formalism.capability.reason.value)
            )
        if request.text is None:
            raise ProviderError(self._failure("analyse", Retryability.NOT_RETRYABLE, "text_required", "ValueError"))
        parser = self._load_parser()
        policy = AnalysisPolicy.model_validate(
            {
                **DEFAULT_ANALYSIS_POLICY.model_dump(exclude={"semantic_digest"}),
                "output_formalism": _FORMALISM_OUTPUT[formalism_id],
            }
        )
        source = SourceArtifact.from_text(request.text, source_name=request.source.source_name or "rdam-source")
        try:
            outcome = ProductionIngestor(parser=parser).analyse(
                source, analysis_policy=policy, cache_directory=self._cache_directory
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
                    message_parameters=(("failed_stage", error.failure.failed_stage.value), ("category", error.failure.category.value)),
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
        )

    def _load_parser(self) -> Parser:
        if self._parser is not None:
            return self._parser
        if self._store is not None and self._release_id is not None:
            from rdam.rst.model_loading import peek_runtime_contract

            contract = peek_runtime_contract(self._store / self._release_id)
            family = Parser.family_for_runtime_contract(contract)
            self._parser = Parser.from_model_release(
                self._store,
                self._release_id,
                family=family,
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


__all__ = ["ERST_GRAPH", "PUBLISHED_WEIGHTS_LICENCE", "RST_TREE", "ProviderConfigurationError", "RstProvider"]

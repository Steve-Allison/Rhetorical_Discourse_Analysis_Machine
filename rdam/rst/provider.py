"""The RST provider: ``rdam.rst`` presented to the machine through its own declaration.

Capability is derived from the **published promotion decision** beside the configured
release (``<store>/<release_id>.promotion.json``, feature 008) — never from whether a
model happens to load. No decision → ``unavailable(no_promoted_implementation)``;
``withhold`` → ``unavailable(withheld)``; ``retire`` → ``unavailable(retired)``;
``promote``/``replace`` → ``available``. Reporting capability loads nothing (capability
contract §Aggregate behaviour 2). The parser is loaded on the first ``analyse`` and the
decision's artifact digest is checked against the release's manifest before any
inference, so a decision cannot be borrowed by a different artifact.

Formalisms (006 data-model §Formalism): ``rst_tree`` carries ``…/rst``; ``erst_graph``
carries ``…/erst`` and is available only when a validated eRST completion bundle
resolves. Failures are ``rdam.rst``'s typed failures mapped one-to-one — same code, same
retryability — onto the machine's ``ProviderFailure``; the machine never retries.
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
from rdam.rst.model_loading import load_model_release
from rdam import (
    AvailableCapability,
    FormalismDeclaration,
    NativeTechniqueResult,
    PromotionDecision,
    PromotionOutcome,
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
    load_published_decision,
    technique_curie,
)
from rdam._strict import JsonValue

PACKAGE: Final = "rdam.rst"
RST_TREE: Final = "rst_tree"
ERST_GRAPH: Final = "erst_graph"
_FORMALISM_OUTPUT: Final[Mapping[str, OutputFormalism]] = {
    RST_TREE: OutputFormalism.RST_TREE,
    ERST_GRAPH: OutputFormalism.ERST_GRAPH,
}
_FORMALISM_TECHNIQUE: Final[Mapping[str, Technique]] = {RST_TREE: Technique.RST, ERST_GRAPH: Technique.ERST}
_DECISION_STATE: Final[Mapping[PromotionOutcome, UnavailableReason | None]] = {
    PromotionOutcome.PROMOTE: None,
    PromotionOutcome.REPLACE: None,
    PromotionOutcome.WITHHOLD: UnavailableReason.WITHHELD,
    PromotionOutcome.RETIRE: UnavailableReason.RETIRED,
}


class ProviderConfigurationError(ValueError):
    """The provider was configured with a decision that does not match its release."""


class RstProvider:
    """One configured ``rdam.rst`` release, declared to the machine (006 data-model §Provider)."""

    def __init__(
        self,
        *,
        store: Path,
        release_id: str,
        device: str = "auto",
        erst_scorer_checkpoint: Path | None = None,
        cache_directory: Path | None = None,
        decision: PromotionDecision | None = None,
    ) -> None:
        self._store = Path(store)
        self._release_id = release_id
        self._device = device
        self._erst_checkpoint = erst_scorer_checkpoint
        self._cache_directory = cache_directory
        self._decision = decision if decision is not None else load_published_decision(self._store, release_id)
        if self._decision is not None and self._decision.candidate.candidate_id != release_id:
            raise ProviderConfigurationError(
                f"decision is about {self._decision.candidate.candidate_id!r}, not release {release_id!r}"
            )
        self._parser: Parser | None = None

    @property
    def release_id(self) -> str:
        return self._release_id

    @property
    def decision(self) -> PromotionDecision | None:
        return self._decision

    @property
    def provider_id(self) -> str:
        return f"{PACKAGE}/{self._release_id}"

    @property
    def declaration(self) -> ProviderDeclaration:
        """Side-effect-free: reads the decision and checks for a bundle path; loads no model."""

        contract_version = SemanticVersion(root=WRITE_CONTRACT_VERSION)
        reason = self._unavailable_reason()
        available = AvailableCapability(provider_id=self.provider_id, contract_version=contract_version)
        capability = available if reason is None else UnavailableCapability(reason=reason)
        erst_bundle = resolve_default_erst_checkpoint(self._erst_checkpoint) is not None
        erst_capability = (
            available
            if reason is None and erst_bundle
            else UnavailableCapability(reason=reason or UnavailableReason.NO_PROMOTED_IMPLEMENTATION)
        )
        decision = self._decision
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
                model_identity=self._release_id,
                licence_decision=(
                    decision.licensing.decision_note if decision is not None else "no promotion decision published for this release"
                ),
            ),
            capability=capability,
            requires_structured_input=False,
        )

    def _unavailable_reason(self) -> UnavailableReason | None:
        if self._decision is None:
            return UnavailableReason.NO_PROMOTED_IMPLEMENTATION
        return _DECISION_STATE[self._decision.outcome]

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
        release = load_model_release(self._store, self._release_id, expected_runtime_contract="isanlp_rst.parser/modernbert-v1")
        decision = self._decision
        if decision is None:
            raise ProviderConfigurationError("cannot analyse without a promotion decision")
        actual = release.one_file_for_role("parser_state").sha256
        if decision.candidate.artifact_identity.hex_digest != actual:
            raise ProviderConfigurationError(
                f"promotion decision names artifact {decision.candidate.artifact_identity.hex_digest[:12]}…; "
                f"release {self._release_id} carries {actual[:12]}…"
            )
        self._parser = Parser.from_model_release(
            self._store,
            self._release_id,
            family="modernbert",
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


__all__ = ["ERST_GRAPH", "RST_TREE", "ProviderConfigurationError", "RstProvider"]

"""Inference Anchoring Theory (IAT) Argument Mining provider."""

from threading import Lock
from typing import Final

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
    Sha256Identity,
    Technique,
    UnavailableCapability,
    canonical_json_bytes,
    semantic_sha256,
    technique_curie,
)
from rdam._grounding import prompt_payload_for_request
from rdam._llm import (
    DEFAULT_OUTPUT_RETRIES,
    DEFAULT_TRANSPORT_DEADLINE_SECONDS,
    DEFAULT_TRANSPORT_RETRIES,
    LlmError,
    StructuredAnalyst,
    load_shared_system_prompt,
    resolved_model_identity,
    unavailable_reason,
)
from rdam._provider_provenance import (
    llm_configuration,
    llm_provider_failure,
    provider_failure,
    provider_provenance,
    require_llm_text,
    source_identity as _source_identity,
)
from rdam._strict import JsonValue
from rdam.argument_mining.iat import ArgumentMiningError, IatGraphProposal
from rdam.argument_mining.interpretation import describe
from rdam.argument_mining.output import ArgumentMiningOutput
from rdam.ingest.alignment import SourceSelection, align_payload
from rdam.ingest.contracts.preparation import ContentRequirement
from rdam.ingest.requirements import SUBSTANTIVE_CLASSES, llm_requirement

PROVIDER_ID_PREFIX: Final = "rdam.argument_mining/iat-v1"
FORMALISM_ID: Final = "iat_graph"
CONTRACT_VERSION: Final = SemanticVersion(root="1.0.0")
LICENCE: Final = "MIT (LICENSE); analyses produced by a third-party model under that model's own terms"
_SOURCE_FILES: Final = ("iat.py", "provider.py")


def source_identity() -> Sha256Identity:
    return _source_identity("rdam.argument_mining", _SOURCE_FILES)


INSTRUCTIONS: Final = """\
Extract an Inference Anchoring Theory (Budzynska & Reed 2011; Peldszus & Stede 2013) argument graph
across `<source_document>`:

1. `adu_nodes`: Argumentative Discourse Units present in `<source_document>` (prose, lists, tables,
   charts, diagrams, visual descriptions, notes, or speaker turns):
   - `role`: `major_claim` (top-level thesis/standpoint), `claim` (intermediate conclusion), or `premise` (supporting/attacking ground).
   - `proposition`: concise, self-contained propositional statement of the ADU.
   - `speaker`: speaker name if attributed in `[u_k | ... | speaker=...]`, otherwise `"author"`.
   - `evidence`: exact verbatim `QuoteRef` (`quote` + 1-based `occurrence`) from `<source_document>`.
2. `relations`: directed propositional relations between distinct `adu_nodes`:
   - `inference` (RA): `source_id` supports `target_id` (the inference subgraph MUST be acyclic / DAG).
   - `conflict` (CA): `source_id` attacks/rebuts/undercuts `target_id`.
   - `rephrase` (MA): `source_id` reformulates `target_id`.
3. `enthymemes`: unstated implicit premises required by an `inference` edge (`inference_relation_id` MUST
   reference a relation with `relation_type="inference"`). Never add unstated enthymemes into `adu_nodes`.
"""


class ArgumentMiningProvider:
    """IAT Argument Mining provider."""

    def __init__(
        self,
        *,
        model: str | None = None,
        output_retries: int = DEFAULT_OUTPUT_RETRIES,
        transport_retries: int = DEFAULT_TRANSPORT_RETRIES,
        transport_deadline_seconds: float = DEFAULT_TRANSPORT_DEADLINE_SECONDS,
    ) -> None:
        self._model = resolved_model_identity(model)
        from rdam.configuration import LlmSettings

        settings = LlmSettings(
            model=self._model,
            output_retries=output_retries,
            transport_retries=transport_retries,
            transport_deadline_seconds=transport_deadline_seconds,
        )
        self._output_retries = settings.output_retries
        self._transport_retries = settings.transport_retries
        self._transport_deadline_seconds = settings.transport_deadline_seconds
        self._build_lock = Lock()
        self._analyst: StructuredAnalyst[IatGraphProposal] | None = None

    @property
    def model(self) -> str:
        return self._model

    @property
    def provider_id(self) -> str:
        return f"{PROVIDER_ID_PREFIX}/{self._model}"

    @property
    def effective_instructions(self) -> str:
        return f"{load_shared_system_prompt()}\n\n{INSTRUCTIONS}"

    @property
    def content_requirement(self) -> ContentRequirement:
        return llm_requirement(
            "rdam/substantive-stream-v2",
            SUBSTANTIVE_CLASSES,
            requires_speaker_identity=False,
        )

    @property
    def declaration(self) -> ProviderDeclaration:
        reason = unavailable_reason(self._model)
        capability = (
            AvailableCapability(provider_id=self.provider_id, contract_version=CONTRACT_VERSION)
            if reason is None
            else UnavailableCapability(reason=reason)
        )
        effective = self.effective_instructions
        return ProviderDeclaration(
            provider_id=self.provider_id,
            technique=Technique.ARGUMENT_MINING,
            technique_curie=technique_curie(Technique.ARGUMENT_MINING),
            formalisms=(
                FormalismDeclaration(
                    formalism_id=FORMALISM_ID,
                    technique=Technique.ARGUMENT_MINING,
                    technique_curie=technique_curie(Technique.ARGUMENT_MINING),
                    capability=capability,
                ),
            ),
            contract_version=CONTRACT_VERSION,
            provenance=provider_provenance(
                package="rdam.argument_mining",
                model_identity=self._model,
                licence=LICENCE,
                instructions=effective,
            ),
            capability=capability,
            requires_structured_input=False,
            content_requirement=self.content_requirement,
            parallel_safety="concurrent",
            instructions_identity=Sha256Identity(hex_digest=semantic_sha256(effective)),
            configuration=llm_configuration(
                self._model,
                IatGraphProposal,
                output_retries=self._output_retries,
                transport_retries=self._transport_retries,
                transport_deadline_seconds=self._transport_deadline_seconds,
                evidence_policy="argument_mining/iat-quote-ref-v1",
            ),
            interpretations=(describe(FORMALISM_ID, str(CONTRACT_VERSION)),),
        )

    @property
    def analyst(self) -> StructuredAnalyst[IatGraphProposal]:
        return self._built()

    def _built(self) -> StructuredAnalyst[IatGraphProposal]:
        with self._build_lock:
            if self._analyst is None:
                self._analyst = StructuredAnalyst(
                    output_type=IatGraphProposal,
                    instructions=INSTRUCTIONS,
                    model=self._model,
                    output_retries=self._output_retries,
                    transport_retries=self._transport_retries,
                    transport_deadline_seconds=self._transport_deadline_seconds,
                    source_validator=IatGraphProposal.validate_source,
                    use_shared_constitution=True,
                )
        return self._analyst

    def analyse(self, request: ProviderRequest) -> NativeTechniqueResult:
        declaration = self.declaration
        if not isinstance(declaration.capability, AvailableCapability):
            raise ProviderError(
                self._failure(
                    "provider_not_available",
                    Retryability.NOT_RETRYABLE,
                    "ValueError",
                    declaration.capability.reason.value,
                )
            )
        if request.formalism_id not in (None, FORMALISM_ID):
            raise ProviderError(
                self._failure(
                    "formalism_not_declared",
                    Retryability.NOT_RETRYABLE,
                    "ValueError",
                    str(request.formalism_id),
                )
            )
        text = require_llm_text(
            request.projection.prepared_document.text if request.projection is not None else request.text,
            technique=Technique.ARGUMENT_MINING,
            provider_id=self.provider_id,
        )
        prompt_payload = prompt_payload_for_request(request)
        try:
            analyst = self._built()
            extraction = (
                analyst.extract_prompt(prompt_payload)
                if prompt_payload is not None
                else analyst.extract(text)
            )
            spans_by_id = extraction.structure.validate_source(text)
        except ArgumentMiningError as error:
            raise ProviderError(
                self._failure(
                    "invalid_argument_mining_graph",
                    Retryability.NOT_RETRYABLE,
                    "ArgumentMiningError",
                    str(error),
                )
            ) from error
        except LlmError as error:
            raise ProviderError(
                llm_provider_failure(error, technique=Technique.ARGUMENT_MINING, provider_id=self.provider_id)
            ) from error

        selections: list[SourceSelection] = []
        adu_payload: list[JsonValue] = []
        major_claim_ids: list[str] = []
        for idx, node in enumerate(extraction.structure.adu_nodes):
            span = spans_by_id[node.id]
            adu_payload.append(
                {
                    "id": node.id,
                    "role": node.role,
                    "proposition": node.proposition,
                    "speaker": node.speaker,
                    "span": span.model_dump(),
                }
            )
            if node.role == "major_claim":
                major_claim_ids.append(node.id)
            selections.append(
                SourceSelection(payload_path=f"/adu_nodes/{idx}/span/text", relationship="exact_quote", span=span)
            )

        relations_payload: list[JsonValue] = [
            {
                "id": rel.id,
                "relation_type": rel.relation_type,
                "source_id": rel.source_id,
                "target_id": rel.target_id,
            }
            for rel in extraction.structure.relations
        ]
        enthymemes_payload: list[JsonValue] = [
            {
                "id": enth.id,
                "inference_relation_id": enth.inference_relation_id,
                "reconstructed_premise": enth.reconstructed_premise,
                "grounded": False,
            }
            for enth in extraction.structure.enthymemes
        ]

        payload: dict[str, JsonValue] = {
            "adu_nodes": adu_payload,
            "relations": relations_payload,
            "enthymemes": enthymemes_payload,
            "major_claim_ids": major_claim_ids,
            "node_count": len(adu_payload),
            "relation_count": len(relations_payload),
            "extraction": {
                "model": extraction.model,
                "output_attempts": extraction.output_attempts,
                "transport_attempts": extraction.transport_attempts,
                "instructions_digest": semantic_sha256(self.effective_instructions),
            },
        }
        ArgumentMiningOutput.model_validate_json(canonical_json_bytes(payload))
        alignment = align_payload(payload, request.projection, selections=tuple(selections))
        return NativeTechniqueResult(
            technique=Technique.ARGUMENT_MINING,
            formalism_id=FORMALISM_ID,
            provider_id=self.provider_id,
            provider_contract_version=CONTRACT_VERSION,
            source=request.source,
            payload=payload,
            source_alignment=alignment,
            provenance=declaration.provenance,
        )

    def _failure(
        self,
        code: str,
        retryability: Retryability,
        exception_type: str,
        detail: str | None = None,
    ) -> ProviderFailure:
        return provider_failure(
            technique=Technique.ARGUMENT_MINING,
            provider_id=self.provider_id,
            code=code,
            retryability=retryability,
            exception_type=exception_type,
            detail=detail,
        )


__all__ = [
    "CONTRACT_VERSION",
    "FORMALISM_ID",
    "INSTRUCTIONS",
    "LICENCE",
    "PROVIDER_ID_PREFIX",
    "ArgumentMiningProvider",
    "source_identity",
]

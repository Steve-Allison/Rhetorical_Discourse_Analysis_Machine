"""Speech Act & Hamblin Commitment Store provider."""

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
from rdam.ingest.alignment import SourceSelection, align_payload
from rdam.ingest.contracts.evidence import SourceEvidenceSpan
from rdam.ingest.contracts.preparation import ContentRequirement
from rdam.ingest.requirements import SUBSTANTIVE_CLASSES, llm_requirement
from rdam.speech_acts.acts import SpeechActError, SpeechActProposal
from rdam.speech_acts.commitments import replay_commitments
from rdam.speech_acts.interpretation import describe
from rdam.speech_acts.output import SpeechActsOutput

PROVIDER_ID_PREFIX: Final = "rdam.speech_acts/iso24617-hamblin-v1"
FORMALISM_ID: Final = "speech_act_sequence"
CONTRACT_VERSION: Final = SemanticVersion(root="1.0.0")
LICENCE: Final = "MIT (LICENSE); analyses produced by a third-party model under that model's own terms"
_SOURCE_FILES: Final = ("acts.py", "commitments.py", "provider.py")


def source_identity() -> Sha256Identity:
    return _source_identity("rdam.speech_acts", _SOURCE_FILES)


INSTRUCTIONS: Final = """\
Segment and classify the illocutionary speech acts in `<source_document>` under Searle (1976) and
ISO 24617-2 (Bunt et al. 2012), and label each act's dialogue commitment operation (Hamblin 1970).

Searle class -> allowed ISO 24617-2 communicative functions (enforced deterministically):
- `assertive`: `inform`, `agreement`, `disagreement`, `correction`, `answer`, `confirm`, `disconfirm`
- `directive`: `question`, `request`, `instruct`, `suggest`
- `commissive`: `promise`, `offer`, `threat`
- `expressive`: `apology`, `thank`, `congratulate`
- `declaration`: `declare`

Commitment operations:
- `assert`: speaker commits to `propositional_content` (`target_proposition` MUST be null).
- `concede`: speaker accepts another party's proposition (`target_proposition` MUST be null).
- `retract`: speaker withdraws a prior commitment (`target_proposition` MUST name the withdrawn proposition).
- `challenge`: speaker demands justification for `target_proposition` (`target_proposition` required).
- `none`: questions, directives, or expressives that do not add/remove propositional commitments (`target_proposition` MUST be null).

Use the `speaker` attribute from `[u_k | ... | speaker=...]` when present; otherwise use `"author"`.
Every act requires an exact verbatim `evidence` `QuoteRef` from `<source_document>`.
"""


class SpeechActsProvider:
    """Speech Act & Hamblin Commitment Store provider."""

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
        self._analyst: StructuredAnalyst[SpeechActProposal] | None = None

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
            "rdam/substantive-speaker-stream-v2",
            SUBSTANTIVE_CLASSES,
            requires_speaker_identity=True,
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
            technique=Technique.SPEECH_ACTS,
            technique_curie=technique_curie(Technique.SPEECH_ACTS),
            formalisms=(
                FormalismDeclaration(
                    formalism_id=FORMALISM_ID,
                    technique=Technique.SPEECH_ACTS,
                    technique_curie=technique_curie(Technique.SPEECH_ACTS),
                    capability=capability,
                ),
            ),
            contract_version=CONTRACT_VERSION,
            provenance=provider_provenance(
                package="rdam.speech_acts",
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
                SpeechActProposal,
                output_retries=self._output_retries,
                transport_retries=self._transport_retries,
                transport_deadline_seconds=self._transport_deadline_seconds,
                evidence_policy="speech_acts/quote-ref-v1",
            ),
            interpretations=(describe(FORMALISM_ID, str(CONTRACT_VERSION)),),
        )

    @property
    def analyst(self) -> StructuredAnalyst[SpeechActProposal]:
        return self._built()

    def _built(self) -> StructuredAnalyst[SpeechActProposal]:
        with self._build_lock:
            if self._analyst is None:
                self._analyst = StructuredAnalyst(
                    output_type=SpeechActProposal,
                    instructions=INSTRUCTIONS,
                    model=self._model,
                    output_retries=self._output_retries,
                    transport_retries=self._transport_retries,
                    transport_deadline_seconds=self._transport_deadline_seconds,
                    source_validator=SpeechActProposal.validate_source,
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
            technique=Technique.SPEECH_ACTS,
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
        except SpeechActError as error:
            raise ProviderError(
                self._failure("invalid_speech_acts", Retryability.NOT_RETRYABLE, "SpeechActError", str(error))
            ) from error
        except LlmError as error:
            raise ProviderError(
                llm_provider_failure(error, technique=Technique.SPEECH_ACTS, provider_id=self.provider_id)
            ) from error

        store_summary = replay_commitments(extraction.structure.acts)
        selections: list[SourceSelection] = []
        acts_payload: list[JsonValue] = []
        for idx, act in enumerate(extraction.structure.acts):
            span: SourceEvidenceSpan = spans_by_id[act.act_id]
            acts_payload.append(
                {
                    "act_id": act.act_id,
                    "speaker": act.speaker,
                    "searle_class": act.searle_class,
                    "iso_communicative_function": act.iso_communicative_function,
                    "propositional_content": act.propositional_content,
                    "commitment_operation": act.commitment_operation,
                    "target_proposition": act.target_proposition,
                    "span": span.model_dump(),
                }
            )
            selections.append(
                SourceSelection(
                    payload_path=f"/acts/{idx}/span/text",
                    relationship="exact_quote",
                    span=span,
                )
            )

        payload: dict[str, JsonValue] = {
            "acts": acts_payload,
            "act_count": len(acts_payload),
            "commitment_store": [
                {
                    "speaker": s.speaker,
                    "active_commitments": list(s.active_commitments),
                    "retracted_commitments": list(s.retracted_commitments),
                    "challenges_raised": list(s.challenges_raised),
                }
                for s in store_summary.speakers
            ],
            "conflicts": [
                {
                    "speaker": c.speaker,
                    "earlier_act_id": c.earlier_act_id,
                    "later_act_id": c.later_act_id,
                    "earlier_proposition": c.earlier_proposition,
                    "later_proposition": c.later_proposition,
                }
                for c in store_summary.conflicts
            ],
            "extraction": {
                "model": extraction.model,
                "output_attempts": extraction.output_attempts,
                "transport_attempts": extraction.transport_attempts,
                "instructions_digest": semantic_sha256(self.effective_instructions),
            },
        }
        SpeechActsOutput.model_validate_json(canonical_json_bytes(payload))
        alignment = align_payload(payload, request.projection, selections=tuple(selections))
        return NativeTechniqueResult(
            technique=Technique.SPEECH_ACTS,
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
            technique=Technique.SPEECH_ACTS,
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
    "SpeechActsProvider",
    "source_identity",
]

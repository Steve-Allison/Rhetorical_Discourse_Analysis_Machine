"""Pragma-Dialectics provider (van Eemeren & Grootendorst 2004; van Eemeren 2010)."""

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
from rdam.ingest.contracts.preparation import ContentRequirement
from rdam.ingest.requirements import SUBSTANTIVE_CLASSES, llm_requirement
from rdam.pragma_dialectics.dialectics import CriticalDiscussionProposal, PragmaDialecticsError
from rdam.pragma_dialectics.interpretation import describe
from rdam.pragma_dialectics.output import PragmaDialecticsOutput
from rdam.pragma_dialectics.rules import CRITICAL_DISCUSSION_RULES

PROVIDER_ID_PREFIX: Final = "rdam.pragma_dialectics/critical-discussion-v1"
FORMALISM_ID: Final = "critical_discussion"
CONTRACT_VERSION: Final = SemanticVersion(root="1.0.0")
LICENCE: Final = "MIT (LICENSE); analyses produced by a third-party model under that model's own terms"
_SOURCE_FILES: Final = ("rules.py", "dialectics.py", "provider.py")


def source_identity() -> Sha256Identity:
    return _source_identity("rdam.pragma_dialectics", _SOURCE_FILES)


def _render_rule_catalogue() -> str:
    lines: list[str] = []
    for rule in CRITICAL_DISCUSSION_RULES.values():
        fallacies = ", ".join(sorted(rule.recognized_fallacies))
        lines.append(f"- `{rule.rule_id}` ({rule.title}): `fallacy_type` in {{{fallacies}}}")
    return "\n".join(lines)


INSTRUCTIONS: Final = f"""\
Reconstruct the argumentative discourse in `<source_document>` under Pragma-Dialectics
(van Eemeren & Grootendorst 2004; van Eemeren 2010):

1. `standpoints`: contested or defended positions (`polarity`: `positive`, `negative`, or `doubt`;
   `protagonist` from speaker metadata or `"author"`).
2. `stage_segments`: critical-discussion stages realized in the text (`confrontation`, `opening`,
   `argumentation`, `concluding`).
3. `strategic_manoeuvres`: how the arguer balances dialectical reasonableness with rhetorical
   effectiveness across `topical_potential`, `audience_demand`, and `presentational_device`.
4. `derailments`: ONLY genuine fallacious derailments of strategic manoeuvring. Every derailment MUST
   pair a `rule_id` with one of its exact catalogued `fallacy_type` values (enforced deterministically):
{_render_rule_catalogue()}

Do not over-flag sound rhetorical emphasis as a derailment. Every item requires an exact verbatim
`evidence` `QuoteRef` from `<source_document>`.
"""


class PragmaDialecticsProvider:
    """Pragma-Dialectics provider."""

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
        self._analyst: StructuredAnalyst[CriticalDiscussionProposal] | None = None

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
            technique=Technique.PRAGMA_DIALECTICS,
            technique_curie=technique_curie(Technique.PRAGMA_DIALECTICS),
            formalisms=(
                FormalismDeclaration(
                    formalism_id=FORMALISM_ID,
                    technique=Technique.PRAGMA_DIALECTICS,
                    technique_curie=technique_curie(Technique.PRAGMA_DIALECTICS),
                    capability=capability,
                ),
            ),
            contract_version=CONTRACT_VERSION,
            provenance=provider_provenance(
                package="rdam.pragma_dialectics",
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
                CriticalDiscussionProposal,
                output_retries=self._output_retries,
                transport_retries=self._transport_retries,
                transport_deadline_seconds=self._transport_deadline_seconds,
                evidence_policy="pragma_dialectics/quote-ref-v1",
            ),
            interpretations=(describe(FORMALISM_ID, str(CONTRACT_VERSION)),),
        )

    @property
    def analyst(self) -> StructuredAnalyst[CriticalDiscussionProposal]:
        return self._built()

    def _built(self) -> StructuredAnalyst[CriticalDiscussionProposal]:
        with self._build_lock:
            if self._analyst is None:
                self._analyst = StructuredAnalyst(
                    output_type=CriticalDiscussionProposal,
                    instructions=INSTRUCTIONS,
                    model=self._model,
                    output_retries=self._output_retries,
                    transport_retries=self._transport_retries,
                    transport_deadline_seconds=self._transport_deadline_seconds,
                    source_validator=CriticalDiscussionProposal.validate_source,
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
            technique=Technique.PRAGMA_DIALECTICS,
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
            sp_spans, st_spans, sm_spans, dr_spans = extraction.structure.validate_source(text)
        except PragmaDialecticsError as error:
            raise ProviderError(
                self._failure(
                    "invalid_pragma_dialectics",
                    Retryability.NOT_RETRYABLE,
                    "PragmaDialecticsError",
                    str(error),
                )
            ) from error
        except LlmError as error:
            raise ProviderError(
                llm_provider_failure(error, technique=Technique.PRAGMA_DIALECTICS, provider_id=self.provider_id)
            ) from error

        selections: list[SourceSelection] = []
        standpoints_payload: list[JsonValue] = []
        for idx, sp in enumerate(extraction.structure.standpoints):
            span = sp_spans[sp.id]
            standpoints_payload.append(
                {
                    "id": sp.id,
                    "protagonist": sp.protagonist,
                    "polarity": sp.polarity,
                    "proposition": sp.proposition,
                    "span": span.model_dump(),
                }
            )
            selections.append(
                SourceSelection(payload_path=f"/standpoints/{idx}/span/text", relationship="exact_quote", span=span)
            )

        stages_payload: list[JsonValue] = []
        for idx, st in enumerate(extraction.structure.stage_segments):
            span = st_spans[st.id]
            stages_payload.append(
                {
                    "id": st.id,
                    "stage": st.stage,
                    "summary": st.summary,
                    "span": span.model_dump(),
                }
            )
            selections.append(
                SourceSelection(payload_path=f"/stage_segments/{idx}/span/text", relationship="exact_quote", span=span)
            )

        manoeuvres_payload: list[JsonValue] = []
        for idx, sm in enumerate(extraction.structure.strategic_manoeuvres):
            span = sm_spans[sm.id]
            manoeuvres_payload.append(
                {
                    "id": sm.id,
                    "stage": sm.stage,
                    "topical_potential": sm.topical_potential,
                    "audience_demand": sm.audience_demand,
                    "presentational_device": sm.presentational_device,
                    "span": span.model_dump(),
                }
            )
            selections.append(
                SourceSelection(
                    payload_path=f"/strategic_manoeuvres/{idx}/span/text",
                    relationship="exact_quote",
                    span=span,
                )
            )

        derailments_payload: list[JsonValue] = []
        violated_rules: list[str] = []
        for idx, dr in enumerate(extraction.structure.derailments):
            span = dr_spans[dr.id]
            rule = CRITICAL_DISCUSSION_RULES[dr.rule_id]
            if dr.rule_id not in violated_rules:
                violated_rules.append(dr.rule_id)
            derailments_payload.append(
                {
                    "id": dr.id,
                    "stage": dr.stage,
                    "rule_id": dr.rule_id,
                    "rule_title": rule.title,
                    "fallacy_type": dr.fallacy_type,
                    "explanation": dr.explanation,
                    "span": span.model_dump(),
                }
            )
            selections.append(
                SourceSelection(payload_path=f"/derailments/{idx}/span/text", relationship="exact_quote", span=span)
            )

        payload: dict[str, JsonValue] = {
            "standpoints": standpoints_payload,
            "stage_segments": stages_payload,
            "strategic_manoeuvres": manoeuvres_payload,
            "derailments": derailments_payload,
            "derailment_count": len(derailments_payload),
            "violated_rules": violated_rules,
            "extraction": {
                "model": extraction.model,
                "output_attempts": extraction.output_attempts,
                "transport_attempts": extraction.transport_attempts,
                "instructions_digest": semantic_sha256(self.effective_instructions),
            },
        }
        PragmaDialecticsOutput.model_validate_json(canonical_json_bytes(payload))
        alignment = align_payload(payload, request.projection, selections=tuple(selections))
        return NativeTechniqueResult(
            technique=Technique.PRAGMA_DIALECTICS,
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
            technique=Technique.PRAGMA_DIALECTICS,
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
    "PragmaDialecticsProvider",
    "source_identity",
]

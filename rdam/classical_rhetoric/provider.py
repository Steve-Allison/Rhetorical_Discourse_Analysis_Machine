"""Classical Rhetoric provider: Aristotelian pisteis, kairos, Hermagorean stasis, and schemes."""

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
from rdam.classical_rhetoric.interpretation import describe
from rdam.classical_rhetoric.output import ClassicalRhetoricOutput
from rdam.classical_rhetoric.rhetoric import ClassicalRhetoricError, ClassicalRhetoricProposal
from rdam.ingest.alignment import SourceSelection, align_payload
from rdam.ingest.contracts.preparation import ContentRequirement
from rdam.ingest.requirements import SUBSTANTIVE_CLASSES, llm_requirement

PROVIDER_ID_PREFIX: Final = "rdam.classical_rhetoric/aristotle-stasis-v1"
FORMALISM_ID: Final = "rhetorical_appeals_and_schemes"
CONTRACT_VERSION: Final = SemanticVersion(root="1.0.0")
LICENCE: Final = "MIT (LICENSE); analyses produced by a third-party model under that model's own terms"
_SOURCE_FILES: Final = ("rhetoric.py", "provider.py")


def source_identity() -> Sha256Identity:
    return _source_identity("rdam.classical_rhetoric", _SOURCE_FILES)


INSTRUCTIONS: Final = """\
Analyse `<source_document>` using Classical Rhetoric (Aristotle *Rhetoric* I.2, Hermagoras stasis theory,
and classical elocutio schemes):

1. `appeals` (Aristotelian *pisteis*):
   - `pistis="ethos"`: `sub_mode` MUST be one of `phronesis` (practical wisdom/competence), `arete` (virtue/integrity), `eunoia` (goodwill toward audience).
   - `pistis="pathos"`: `sub_mode` names the targeted audience emotion (e.g. `urgency`, `fear`, `indignation`, `confidence`, `compassion`).
   - `pistis="logos"`: `sub_mode` MUST be one of `enthymeme`, `example`, `maxim`, `data_evidence`.
   Note: tables, charts, diagrams, and VLM visual descriptions inside `<source_document>` frequently carry `logos` (`data_evidence` / `example`) or `pathos` appeals — include them when present!
2. `kairos_cues`: explicit appeals to timeliness, windows of opportunity, or deadline urgency.
3. `stasis` (Hermagoras):
   - `conjectural` (did X happen / does X exist?), `definitional` (what kind of thing is X?), `qualitative` (how serious/justified is X?), `translative` (is this the right forum/procedure?), or `none` (purely descriptive text with `contested_question=null` and `evidence=null`).
4. `figures` (surface schemes only when genuinely realized in verbatim text):
   - `anaphora`, `epistrophe`, `antithesis`, `tricolon`, `rhetorical_question` (quote MUST include `?`), `chiasmus`, `klimax`, `paraleipsis`.

Every extracted item requires an exact verbatim `evidence` `QuoteRef` from `<source_document>`.
"""


class ClassicalRhetoricProvider:
    """Classical Rhetoric provider."""

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
        self._analyst: StructuredAnalyst[ClassicalRhetoricProposal] | None = None

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
            technique=Technique.CLASSICAL_RHETORIC,
            technique_curie=technique_curie(Technique.CLASSICAL_RHETORIC),
            formalisms=(
                FormalismDeclaration(
                    formalism_id=FORMALISM_ID,
                    technique=Technique.CLASSICAL_RHETORIC,
                    technique_curie=technique_curie(Technique.CLASSICAL_RHETORIC),
                    capability=capability,
                ),
            ),
            contract_version=CONTRACT_VERSION,
            provenance=provider_provenance(
                package="rdam.classical_rhetoric",
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
                ClassicalRhetoricProposal,
                output_retries=self._output_retries,
                transport_retries=self._transport_retries,
                transport_deadline_seconds=self._transport_deadline_seconds,
                evidence_policy="classical_rhetoric/quote-ref-v1",
            ),
            interpretations=(describe(FORMALISM_ID, str(CONTRACT_VERSION)),),
        )

    @property
    def analyst(self) -> StructuredAnalyst[ClassicalRhetoricProposal]:
        return self._built()

    def _built(self) -> StructuredAnalyst[ClassicalRhetoricProposal]:
        with self._build_lock:
            if self._analyst is None:
                self._analyst = StructuredAnalyst(
                    output_type=ClassicalRhetoricProposal,
                    instructions=INSTRUCTIONS,
                    model=self._model,
                    output_retries=self._output_retries,
                    transport_retries=self._transport_retries,
                    transport_deadline_seconds=self._transport_deadline_seconds,
                    source_validator=ClassicalRhetoricProposal.validate_source,
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
            technique=Technique.CLASSICAL_RHETORIC,
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
            appeal_spans, kairos_spans, stasis_span, figure_spans = extraction.structure.validate_source(text)
        except ClassicalRhetoricError as error:
            raise ProviderError(
                self._failure(
                    "invalid_classical_rhetoric",
                    Retryability.NOT_RETRYABLE,
                    "ClassicalRhetoricError",
                    str(error),
                )
            ) from error
        except LlmError as error:
            raise ProviderError(
                llm_provider_failure(error, technique=Technique.CLASSICAL_RHETORIC, provider_id=self.provider_id)
            ) from error

        selections: list[SourceSelection] = []
        appeals_payload: list[JsonValue] = []
        for idx, app in enumerate(extraction.structure.appeals):
            span = appeal_spans[app.appeal_id]
            appeals_payload.append(
                {
                    "appeal_id": app.appeal_id,
                    "pistis": app.pistis,
                    "sub_mode": app.sub_mode,
                    "rationale": app.rationale,
                    "span": span.model_dump(),
                }
            )
            selections.append(
                SourceSelection(payload_path=f"/appeals/{idx}/span/text", relationship="exact_quote", span=span)
            )

        kairos_payload: list[JsonValue] = []
        for idx, cue in enumerate(extraction.structure.kairos_cues):
            span = kairos_spans[cue.cue_id]
            kairos_payload.append(
                {
                    "cue_id": cue.cue_id,
                    "urgency_or_timeliness": cue.urgency_or_timeliness,
                    "span": span.model_dump(),
                }
            )
            selections.append(
                SourceSelection(payload_path=f"/kairos_cues/{idx}/span/text", relationship="exact_quote", span=span)
            )

        stasis_payload: dict[str, JsonValue] = {
            "dominant_stasis": extraction.structure.stasis.dominant_stasis,
            "contested_question": extraction.structure.stasis.contested_question,
            "span": stasis_span.model_dump() if stasis_span is not None else None,
        }
        if stasis_span is not None:
            selections.append(
                SourceSelection(payload_path="/stasis/span/text", relationship="exact_quote", span=stasis_span)
            )

        figures_payload: list[JsonValue] = []
        for idx, fig in enumerate(extraction.structure.figures):
            span = figure_spans[fig.figure_id]
            figures_payload.append(
                {
                    "figure_id": fig.figure_id,
                    "scheme": fig.scheme,
                    "explanation": fig.explanation,
                    "span": span.model_dump(),
                }
            )
            selections.append(
                SourceSelection(payload_path=f"/figures/{idx}/span/text", relationship="exact_quote", span=span)
            )

        appeals = extraction.structure.appeals
        payload: dict[str, JsonValue] = {
            "appeals": appeals_payload,
            "pistis_balance": {
                "ethos": sum(a.pistis == "ethos" for a in appeals),
                "pathos": sum(a.pistis == "pathos" for a in appeals),
                "logos": sum(a.pistis == "logos" for a in appeals),
            },
            "kairos_cues": kairos_payload,
            "stasis": stasis_payload,
            "figures": figures_payload,
            "extraction": {
                "model": extraction.model,
                "output_attempts": extraction.output_attempts,
                "transport_attempts": extraction.transport_attempts,
                "instructions_digest": semantic_sha256(self.effective_instructions),
            },
        }
        ClassicalRhetoricOutput.model_validate_json(canonical_json_bytes(payload))
        alignment = align_payload(payload, request.projection, selections=tuple(selections))
        return NativeTechniqueResult(
            technique=Technique.CLASSICAL_RHETORIC,
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
            technique=Technique.CLASSICAL_RHETORIC,
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
    "ClassicalRhetoricProvider",
    "source_identity",
]

"""Dual-mode ASPIC+ provider: deterministic formal evaluation of a supplied theory or grounded source extraction."""

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
    canonical_json_bytes,
    semantic_sha256,
    technique_curie,
)
from rdam._grounding import prompt_payload_for_request
from rdam._immutable_json import thaw_json
from rdam._llm import (
    DEFAULT_MODEL,
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
from rdam.aspic.interpretation import describe
from rdam.aspic.output import AspicOutput
from rdam.aspic.theory import (
    DEFAULT_ARGUMENT_CAPACITY,
    AspicError,
    AspicEvaluation,
    AspicTheoryInput,
    ExtractedAspicProposal,
    evaluate_aspic,
)
from rdam.ingest.alignment import SourceSelection, align_payload
from rdam.ingest.contracts.preparation import ContentRequirement
from rdam.ingest.requirements import SUBSTANTIVE_CLASSES, llm_requirement

PROVIDER_ID_PREFIX: Final = "rdam.aspic/aspic-plus-v1"
PROVIDER_ID: Final = f"{PROVIDER_ID_PREFIX}/{DEFAULT_MODEL}"
FORMALISM_ID: Final = "aspic_theory"
CONTRACT_VERSION: Final = SemanticVersion(root="1.0.0")
LICENCE: Final = "MIT (LICENSE); extracted theories produced by a third-party model under that model's own terms"
_SOURCE_FILES: Final = ("theory.py", "provider.py")


def source_identity() -> Sha256Identity:
    return _source_identity("rdam.aspic", _SOURCE_FILES)


INSTRUCTIONS: Final = """\
Formalize the structured argumentation in `<source_document>` as an ASPIC+ argumentation theory
(Modgil & Prakken 2013):

- `premises`: atomic propositional symbols (`symbol`, e.g. `rain`, `wet_pitch`, `match_halted`):
  - `kind="axiom"` ONLY for undisputed factual/definitional givens (`Kn`);
  - `kind="ordinary"` for contestable/defeasible premises (`Kp`).
  Axioms and ordinary premises MUST have disjoint symbol sets.
- `rules`: inference licences (`id`, `kind`: `"strict"` for deductive/definitional rules `Rs` or
  `"defeasible"` for presumptive rules `Rd`, `antecedents`, `consequent`).
  Rule IDs MUST be unique. To model an undercut against defeasible rule `d_1`, derive `~d_1` as a
  consequent or premise!
- `contraries`: conflict pairs (`symbol`, `contrary`, `symmetric`). Classical `~x` vs `x` is also
  recognized automatically.
- `premise_preferences`: `(weaker_ordinary_premise, stronger_ordinary_premise)` pairs, acyclic.
- `rule_preferences`: `(weaker_defeasible_rule_id, stronger_defeasible_rule_id)` pairs, acyclic.

Every extracted premise and rule MUST carry an exact verbatim `evidence` `QuoteRef` from `<source_document>`.
"""


def _evaluation_to_payload(
    evaluation: AspicEvaluation,
    *,
    input_origin: str,
    extraction_meta: dict[str, JsonValue] | None,
    evidence_list: list[JsonValue] | None = None,
    derived_from: dict[str, JsonValue] | None = None,
) -> dict[str, JsonValue]:
    payload: dict[str, JsonValue] = {
        "theory": evaluation.theory.model_dump(),
        "input_origin": input_origin,
        "extraction": extraction_meta,
        "arguments": [
            {
                "id": arg.id,
                "conclusion": arg.conclusion,
                "top_rule_id": arg.top_rule_id,
                "top_rule_strict": arg.top_rule_strict,
                "direct_sub_ids": list(arg.direct_sub_ids),
                "all_sub_ids": list(arg.all_sub_ids),
                "ordinary_premises_used": list(arg.ordinary_premises_used),
                "defeasible_rules_used": list(arg.defeasible_rules_used),
                "last_defeasible_rules": list(arg.last_defeasible_rules),
                "is_strict": arg.is_strict,
                "is_firm": arg.is_firm,
            }
            for arg in evaluation.arguments
        ],
        "attacks": [
            {
                "attacker": att.attacker,
                "target": att.target,
                "on_sub_argument": att.on_sub_argument,
                "kind": att.kind,
                "succeeded_as_defeat": att.succeeded_as_defeat,
            }
            for att in evaluation.attacks
        ],
        "defeat_framework": {
            "arguments": [arg.id for arg in evaluation.arguments],
            "attacks": [[src, dst] for src, dst in evaluation.defeats],
        },
        "extensions": evaluation.extensions,
        "rationality_postulates": {
            "sub_argument_closure": evaluation.rationality.sub_argument_closure,
            "strict_closure": evaluation.rationality.strict_closure,
            "direct_consistency": evaluation.rationality.direct_consistency,
            "indirect_consistency": evaluation.rationality.indirect_consistency,
            "all_satisfied": evaluation.rationality.all_satisfied,
        },
        "argument_count": len(evaluation.arguments),
        "defeat_count": len(evaluation.defeats),
    }
    if evidence_list is not None:
        payload["evidence"] = evidence_list
    if derived_from is not None:
        payload["derived_from"] = derived_from
    return payload


class AspicProvider:
    """Dual-mode ASPIC+ structured argumentation provider."""

    def __init__(
        self,
        *,
        model: str | None = None,
        capacity: int = DEFAULT_ARGUMENT_CAPACITY,
        output_retries: int = DEFAULT_OUTPUT_RETRIES,
        transport_retries: int = DEFAULT_TRANSPORT_RETRIES,
        transport_deadline_seconds: float = DEFAULT_TRANSPORT_DEADLINE_SECONDS,
    ) -> None:
        if capacity <= 0:
            raise ValueError("ASPIC+ capacity must be positive")
        self._capacity = capacity
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
        self._analyst: StructuredAnalyst[ExtractedAspicProposal] | None = None

    @property
    def model(self) -> str:
        return self._model

    @property
    def capacity(self) -> int:
        return self._capacity

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
        capability = AvailableCapability(provider_id=self.provider_id, contract_version=CONTRACT_VERSION)
        effective = self.effective_instructions
        return ProviderDeclaration(
            provider_id=self.provider_id,
            technique=Technique.ASPIC,
            technique_curie=technique_curie(Technique.ASPIC),
            formalisms=(
                FormalismDeclaration(
                    formalism_id=FORMALISM_ID,
                    technique=Technique.ASPIC,
                    technique_curie=technique_curie(Technique.ASPIC),
                    capability=capability,
                ),
            ),
            contract_version=CONTRACT_VERSION,
            provenance=provider_provenance(
                package="rdam.aspic",
                model_identity=self._model,
                licence=LICENCE,
                instructions=effective,
            ),
            capability=capability,
            requires_structured_input=False,
            accepts_structured_input=True,
            content_requirement=self.content_requirement,
            parallel_safety="concurrent",
            instructions_identity=Sha256Identity(hex_digest=semantic_sha256(effective)),
            configuration=llm_configuration(
                self._model,
                ExtractedAspicProposal,
                output_retries=self._output_retries,
                transport_retries=self._transport_retries,
                transport_deadline_seconds=self._transport_deadline_seconds,
                evidence_policy="aspic/dual-mode-quote-ref-v1",
            ),
            interpretations=(describe(FORMALISM_ID, str(CONTRACT_VERSION)),),
        )

    @property
    def analyst(self) -> StructuredAnalyst[ExtractedAspicProposal]:
        return self._built()

    def _built(self) -> StructuredAnalyst[ExtractedAspicProposal]:
        with self._build_lock:
            if self._analyst is None:
                self._analyst = StructuredAnalyst(
                    output_type=ExtractedAspicProposal,
                    instructions=INSTRUCTIONS,
                    model=self._model,
                    output_retries=self._output_retries,
                    transport_retries=self._transport_retries,
                    transport_deadline_seconds=self._transport_deadline_seconds,
                    source_validator=ExtractedAspicProposal.validate_source,
                    use_shared_constitution=True,
                )
        return self._analyst

    def analyse(self, request: ProviderRequest) -> NativeTechniqueResult:
        declaration = self.declaration
        if request.formalism_id not in (None, FORMALISM_ID):
            raise ProviderError(
                self._failure(
                    "formalism_not_declared",
                    Retryability.NOT_RETRYABLE,
                    "ValueError",
                    str(request.formalism_id),
                )
            )
        if request.structured_input is not None:
            try:
                theory = AspicTheoryInput.from_payload(thaw_json(request.structured_input))
                evaluation = evaluate_aspic(theory, capacity=self._capacity)
            except AspicError as error:
                raise ProviderError(
                    self._failure("invalid_aspic_theory", Retryability.NOT_RETRYABLE, "AspicError", str(error))
                ) from error
            derived_record: dict[str, JsonValue] | None = None
            if request.derived_from is not None:
                derived_record = {
                    "technique": request.derived_from.technique.value,
                    "result_identity": request.derived_from.result_identity.hex_digest,
                }
            payload = _evaluation_to_payload(
                evaluation,
                input_origin="explicitly_derived" if request.derived_from is not None else "supplied",
                extraction_meta=None,
                derived_from=derived_record,
            )
            AspicOutput.model_validate_json(canonical_json_bytes(payload))
            return NativeTechniqueResult(
                technique=Technique.ASPIC,
                formalism_id=FORMALISM_ID,
                provider_id=self.provider_id,
                provider_contract_version=CONTRACT_VERSION,
                source=request.source,
                payload=payload,
                provenance=declaration.provenance,
            )

        reason = unavailable_reason(self._model)
        if reason is not None:
            raise ProviderError(
                self._failure("provider_not_available", Retryability.NOT_RETRYABLE, "ValueError", reason.value)
            )
        text = require_llm_text(
            request.projection.prepared_document.text if request.projection is not None else request.text,
            technique=Technique.ASPIC,
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
            prem_spans, rule_spans = extraction.structure.validate_source(text)
            theory = extraction.structure.to_theory_input()
            evaluation = evaluate_aspic(theory, capacity=self._capacity)
        except AspicError as error:
            raise ProviderError(
                self._failure("invalid_aspic_theory", Retryability.NOT_RETRYABLE, "AspicError", str(error))
            ) from error
        except LlmError as error:
            raise ProviderError(
                llm_provider_failure(error, technique=Technique.ASPIC, provider_id=self.provider_id)
            ) from error

        evidence_list: list[JsonValue] = []
        selections: list[SourceSelection] = []
        for prem in extraction.structure.premises:
            span = prem_spans[prem.symbol]
            ev_idx = len(evidence_list)
            evidence_list.append(
                {"item_kind": "premise", "identifier": prem.symbol, "span": span.model_dump()}
            )
            selections.append(
                SourceSelection(payload_path=f"/evidence/{ev_idx}/span/text", relationship="exact_quote", span=span)
            )
        for rule in extraction.structure.rules:
            span = rule_spans[rule.id]
            ev_idx = len(evidence_list)
            evidence_list.append(
                {"item_kind": "rule", "identifier": rule.id, "span": span.model_dump()}
            )
            selections.append(
                SourceSelection(payload_path=f"/evidence/{ev_idx}/span/text", relationship="exact_quote", span=span)
            )

        extracted_payload = _evaluation_to_payload(
            evaluation,
            input_origin="extracted",
            extraction_meta={
                "model": extraction.model,
                "output_attempts": extraction.output_attempts,
                "transport_attempts": extraction.transport_attempts,
                "instructions_digest": semantic_sha256(self.effective_instructions),
            },
            evidence_list=evidence_list,
        )
        AspicOutput.model_validate_json(canonical_json_bytes(extracted_payload))
        alignment = align_payload(extracted_payload, request.projection, selections=tuple(selections))
        return NativeTechniqueResult(
            technique=Technique.ASPIC,
            formalism_id=FORMALISM_ID,
            provider_id=self.provider_id,
            provider_contract_version=CONTRACT_VERSION,
            source=request.source,
            payload=extracted_payload,
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
            technique=Technique.ASPIC,
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
    "PROVIDER_ID",
    "PROVIDER_ID_PREFIX",
    "AspicProvider",
    "source_identity",
]

"""Dual-mode IBIS provider: deterministic gIBIS validation of supplied structures or grounded DocLang extraction."""

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
from rdam.ibis.grammar import ExtractedIbisProposal, IbisStructure, StructureError, deliberation_map
from rdam.ibis.interpretation import describe
from rdam.ibis.output import IbisOutput
from rdam.ingest.alignment import SourceSelection, align_payload
from rdam.ingest.contracts.evidence import SourceEvidenceSpan
from rdam.ingest.contracts.preparation import ContentRequirement
from rdam.ingest.requirements import SUBSTANTIVE_CLASSES, llm_requirement

PROVIDER_ID_PREFIX: Final = "rdam.ibis/gibis-v2"
PROVIDER_ID: Final = f"{PROVIDER_ID_PREFIX}/{DEFAULT_MODEL}"
FORMALISM_ID: Final = "ibis_structure"
CONTRACT_VERSION: Final = SemanticVersion(root="2.0.0")
LICENCE: Final = "MIT (LICENSE); extracted analyses produced by a third-party model under that model's own terms"
_SOURCE_FILES: Final = ("grammar.py", "provider.py")


def source_identity() -> Sha256Identity:
    return _source_identity("rdam.ibis", _SOURCE_FILES)


INSTRUCTIONS: Final = """\
Extract an Issue-Based Information System (IBIS) deliberation map under the strict gIBIS link grammar
(Kunz & Rittel 1970; Conklin & Begeman 1988).

Identify:
- `issue` nodes: open questions, decisions, dilemmas, or wicked problems raised in the source.
- `position` nodes: candidate options, proposals, or stances responding to an issue.
- `argument` nodes: reasons offered in support of (`supports`) or against (`objects_to`) a position.

Strict gIBIS link grammar rules (enforced deterministically):
- `responds_to`: `position` -> `issue` (EVERY position MUST have EXACTLY ONE outgoing `responds_to` link).
- `supports` / `objects_to`: `argument` -> `position` (EVERY argument MUST have EXACTLY ONE outgoing `supports` or `objects_to` link).
- `generalizes` / `specializes` / `replaces`: `issue` -> `issue`.
- `questions` / `is_suggested_by`: `issue` -> `issue`, `position`, or `argument`.
- Self-links and duplicate links are forbidden.

Every extracted node must carry an exact verbatim `evidence` `QuoteRef` (`quote` + 1-based `occurrence`)
from `<source_document>`. If the source raises no deliberation issues, return empty `nodes` and `links`.
"""


def _source_selections(spans_by_index: list[tuple[int, SourceEvidenceSpan]]) -> tuple[SourceSelection, ...]:
    return tuple(
        SourceSelection(
            payload_path=f"/node_evidence/{idx}/span/text",
            relationship="exact_quote",
            span=span,
        )
        for idx, span in spans_by_index
    )


class IbisProvider:
    """Dual-mode gIBIS validator and grounded deliberation extractor."""

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
        self._analyst: StructuredAnalyst[ExtractedIbisProposal] | None = None

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
        capability = AvailableCapability(provider_id=self.provider_id, contract_version=CONTRACT_VERSION)
        effective = self.effective_instructions
        return ProviderDeclaration(
            provider_id=self.provider_id,
            technique=Technique.IBIS,
            technique_curie=technique_curie(Technique.IBIS),
            formalisms=(
                FormalismDeclaration(
                    formalism_id=FORMALISM_ID,
                    technique=Technique.IBIS,
                    technique_curie=technique_curie(Technique.IBIS),
                    capability=capability,
                ),
            ),
            contract_version=CONTRACT_VERSION,
            provenance=provider_provenance(
                package="rdam.ibis",
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
                ExtractedIbisProposal,
                output_retries=self._output_retries,
                transport_retries=self._transport_retries,
                transport_deadline_seconds=self._transport_deadline_seconds,
                evidence_policy="ibis/dual-mode-quote-ref-v2",
            ),
            interpretations=(describe(FORMALISM_ID, str(CONTRACT_VERSION)),),
        )

    def _built(self) -> StructuredAnalyst[ExtractedIbisProposal]:
        with self._build_lock:
            if self._analyst is None:
                self._analyst = StructuredAnalyst(
                    output_type=ExtractedIbisProposal,
                    instructions=INSTRUCTIONS,
                    model=self._model,
                    output_retries=self._output_retries,
                    transport_retries=self._transport_retries,
                    transport_deadline_seconds=self._transport_deadline_seconds,
                    source_validator=ExtractedIbisProposal.validate_source,
                    use_shared_constitution=True,
                )
        return self._analyst

    def analyse(self, request: ProviderRequest) -> NativeTechniqueResult:
        declaration = self.declaration
        if request.formalism_id not in (None, FORMALISM_ID):
            raise ProviderError(
                self._failure("formalism_not_declared", Retryability.NOT_RETRYABLE, "ValueError", str(request.formalism_id))
            )
        if request.structured_input is not None:
            try:
                structure = IbisStructure.from_payload(thaw_json(request.structured_input))
            except StructureError as error:
                raise ProviderError(
                    self._failure("invalid_ibis_structure", Retryability.NOT_RETRYABLE, "StructureError", str(error))
                ) from error
            payload: dict[str, JsonValue] = {
                "structure": structure.to_payload(),
                "input_origin": "explicitly_derived" if request.derived_from is not None else "supplied",
                "extraction": None,
                "grammar": "gibis-v1",
                "map": deliberation_map(structure),
            }
            if request.derived_from is not None:
                payload["derived_from"] = {
                    "technique": request.derived_from.technique.value,
                    "result_identity": request.derived_from.result_identity.hex_digest,
                }
            IbisOutput.model_validate_json(canonical_json_bytes(payload))
            return NativeTechniqueResult(
                technique=Technique.IBIS,
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
            technique=Technique.IBIS,
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
            spans_by_node = extraction.structure.validate_source(text)
        except StructureError as error:
            raise ProviderError(
                self._failure("invalid_ibis_structure", Retryability.NOT_RETRYABLE, "StructureError", str(error))
            ) from error
        except LlmError as error:
            raise ProviderError(
                llm_provider_failure(error, technique=Technique.IBIS, provider_id=self.provider_id)
            ) from error

        structure_payload = extraction.structure.to_structure_payload()
        if extraction.structure.nodes:
            validated_structure = IbisStructure.from_payload(structure_payload)
            map_payload: JsonValue = deliberation_map(validated_structure)
        else:
            map_payload = {
                "issues": [],
                "issues_without_positions": [],
                "positions_without_arguments": [],
                "isolated_nodes": [],
            }

        node_evidence_list: list[JsonValue] = []
        selection_spans: list[tuple[int, SourceEvidenceSpan]] = []
        for idx, node in enumerate(extraction.structure.nodes):
            span = spans_by_node[node.id]
            node_evidence_list.append({"node_id": node.id, "span": span.model_dump()})
            selection_spans.append((idx, span))

        extracted_payload: dict[str, JsonValue] = {
            "structure": structure_payload,
            "input_origin": "extracted",
            "extraction": {
                "model": extraction.model,
                "output_attempts": extraction.output_attempts,
                "transport_attempts": extraction.transport_attempts,
                "instructions_digest": semantic_sha256(self.effective_instructions),
            },
            "grammar": "gibis-v1",
            "map": map_payload,
        }
        if node_evidence_list:
            extracted_payload["node_evidence"] = node_evidence_list

        IbisOutput.model_validate_json(canonical_json_bytes(extracted_payload))
        alignment = align_payload(
            extracted_payload,
            request.projection,
            selections=_source_selections(selection_spans),
        )
        return NativeTechniqueResult(
            technique=Technique.IBIS,
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
            technique=Technique.IBIS,
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
    "IbisProvider",
    "source_identity",
]

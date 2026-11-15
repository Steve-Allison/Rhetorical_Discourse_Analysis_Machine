"""Deterministic Centering Theory & Entity Grid provider."""

from typing import Final

from rdam import (
    AvailableCapability,
    FormalismDeclaration,
    NativeTechniqueResult,
    ProviderConfiguration,
    ProviderDeclaration,
    ProviderError,
    ProviderFailure,
    ProviderRequest,
    Retryability,
    SemanticVersion,
    Sha256Identity,
    Technique,
    canonical_json_bytes,
    technique_curie,
)
from rdam._grounding import substrate_for_request
from rdam._provider_provenance import (
    provider_failure,
    provider_provenance,
    require_llm_text,
    source_identity as _source_identity,
)
from rdam._strict import JsonValue
from rdam.centering.grid import CenteringGridAnalysis, analyse_centering
from rdam.centering.interpretation import describe
from rdam.centering.output import CenteringOutput
from rdam.ingest.alignment import SourceSelection, align_payload
from rdam.ingest.contracts.evidence import SourceEvidenceSpan
from rdam.ingest.contracts.preparation import ContentRequirement
from rdam.ingest.requirements import SUBSTANTIVE_CLASSES, llm_requirement

PROVIDER_ID: Final = "rdam.centering/entity-grid-v1"
FORMALISM_ID: Final = "centering_grid"
CONTRACT_VERSION: Final = SemanticVersion(root="1.0.0")
LICENCE: Final = "MIT (LICENSE)"
_SOURCE_FILES: Final = ("grid.py", "provider.py")


def source_identity() -> Sha256Identity:
    return _source_identity("rdam.centering", _SOURCE_FILES)


def _selections(analysis: CenteringGridAnalysis) -> tuple[SourceSelection, ...]:
    items: list[SourceSelection] = []
    for u_idx, utt in enumerate(analysis.utterances):
        items.append(
            SourceSelection(
                payload_path=f"/utterances/{u_idx}/span/text",
                relationship="exact_quote",
                span=SourceEvidenceSpan(start=utt.start, end=utt.end, text=utt.text),
            )
        )
    for e_idx, ent in enumerate(analysis.entities):
        for m_idx, mention in enumerate(ent.mentions):
            items.append(
                SourceSelection(
                    payload_path=f"/entities/{e_idx}/mentions/{m_idx}/span/text",
                    relationship="exact_quote",
                    span=mention.span,
                )
            )
    return tuple(items)


class CenteringProvider:
    """Deterministic Centering Theory & Entity Grid provider."""

    @property
    def content_requirement(self) -> ContentRequirement:
        return llm_requirement(
            "rdam/substantive-stream-v2",
            SUBSTANTIVE_CLASSES,
            requires_speaker_identity=False,
        )

    @property
    def declaration(self) -> ProviderDeclaration:
        capability = AvailableCapability(provider_id=PROVIDER_ID, contract_version=CONTRACT_VERSION)
        return ProviderDeclaration(
            provider_id=PROVIDER_ID,
            technique=Technique.CENTERING,
            technique_curie=technique_curie(Technique.CENTERING),
            formalisms=(
                FormalismDeclaration(
                    formalism_id=FORMALISM_ID,
                    technique=Technique.CENTERING,
                    technique_curie=technique_curie(Technique.CENTERING),
                    capability=capability,
                ),
            ),
            contract_version=CONTRACT_VERSION,
            provenance=provider_provenance(package="rdam.centering", licence=LICENCE),
            capability=capability,
            requires_structured_input=False,
            content_requirement=self.content_requirement,
            parallel_safety="concurrent",
            configuration=ProviderConfiguration(
                settings={"algorithm": "grosz-joshi-weinstein-barzilay-lapata-v1"},
                cache_eligible=True,
                cache_reason="deterministic_entity_grid",
            ),
            interpretations=(describe(FORMALISM_ID, str(CONTRACT_VERSION)),),
        )

    def analyse(self, request: ProviderRequest) -> NativeTechniqueResult:
        declaration = self.declaration
        if request.formalism_id not in (None, FORMALISM_ID):
            raise ProviderError(
                self._failure("formalism_not_declared", "ValueError", str(request.formalism_id))
            )
        text = require_llm_text(
            request.projection.prepared_document.text if request.projection is not None else request.text,
            technique=Technique.CENTERING,
            provider_id=PROVIDER_ID,
        )
        substrate = substrate_for_request(request)
        analysis = analyse_centering(text, substrate)

        payload: dict[str, JsonValue] = {
            "entities": [
                {
                    "entity_id": ent.entity_id,
                    "canonical_name": ent.canonical_name,
                    "is_plural": ent.is_plural,
                    "mentions": [
                        {
                            "utterance_id": m.utterance_id,
                            "role": m.role,
                            "span": m.span.model_dump(),
                            "is_pronoun": m.is_pronoun,
                        }
                        for m in ent.mentions
                    ],
                }
                for ent in analysis.entities
            ],
            "utterances": [
                {
                    "utterance_id": utt.utterance_id,
                    "sentence_index": utt.sentence_index,
                    "span": {"start": utt.start, "end": utt.end, "text": utt.text},
                    "speaker": utt.speaker,
                    "cf_ranking": list(utt.cf_ranking),
                    "cp": utt.cp,
                    "cb": utt.cb,
                    "transition": utt.transition,
                }
                for utt in analysis.utterances
            ],
            "entity_grid": [
                {
                    "entity_id": ent.entity_id,
                    "roles": list(analysis.entity_grid[ent.entity_id]),
                }
                for ent in analysis.entities
            ],
            "transition_counts": {
                "establishment": analysis.transition_counts["establishment"],
                "continue_count": analysis.transition_counts["continue"],
                "retain": analysis.transition_counts["retain"],
                "smooth_shift": analysis.transition_counts["smooth_shift"],
                "rough_shift": analysis.transition_counts["rough_shift"],
                "zero_cb": analysis.transition_counts["zero_cb"],
            },
            "local_coherence_score": analysis.local_coherence_score,
            "entity_count": len(analysis.entities),
            "utterance_count": len(analysis.utterances),
        }
        CenteringOutput.model_validate_json(canonical_json_bytes(payload))
        alignment = align_payload(payload, request.projection, selections=_selections(analysis))
        return NativeTechniqueResult(
            technique=Technique.CENTERING,
            formalism_id=FORMALISM_ID,
            provider_id=PROVIDER_ID,
            provider_contract_version=CONTRACT_VERSION,
            source=request.source,
            payload=payload,
            source_alignment=alignment,
            provenance=declaration.provenance,
        )

    def _failure(self, code: str, exception_type: str, detail: str | None = None) -> ProviderFailure:
        return provider_failure(
            technique=Technique.CENTERING,
            provider_id=PROVIDER_ID,
            code=code,
            retryability=Retryability.NOT_RETRYABLE,
            exception_type=exception_type,
            detail=detail,
        )


__all__ = [
    "CONTRACT_VERSION",
    "FORMALISM_ID",
    "LICENCE",
    "PROVIDER_ID",
    "CenteringProvider",
    "source_identity",
]

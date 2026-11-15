"""SPEECH_ACTS-owned reading guide; no inference or payload rewriting."""

from rdam._interpretation_types import NativeInterpretationDescriptor, NativeSectionDescription
from rdam.contracts import NATIVE_RESULT_VERSION


def describe(formalism_id: str, provider_contract_version: str) -> NativeInterpretationDescriptor:
    return NativeInterpretationDescriptor(
        formalism_id=formalism_id,
        native_contract_version=NATIVE_RESULT_VERSION,
        provider_contract_version=provider_contract_version,
        purpose=(
            "Classify illocutionary speech acts under Searle (1976) and ISO 24617-2 communicative "
            "functions, and deterministically replay per-speaker Hamblin (1970) commitment stores."
        ),
        input_basis="source_projection",
        method="mixed",
        sections=(
            NativeSectionDescription(
                pointer="/payload/acts",
                meaning="Ordered illocutionary acts with Searle class, ISO 24617-2 function, commitment operation, and exact source span.",
            ),
            NativeSectionDescription(
                pointer="/payload/commitment_store",
                meaning="Deterministic per-speaker active commitments, retractions, and open challenges replayed from the speech-act sequence.",
            ),
            NativeSectionDescription(
                pointer="/payload/conflicts",
                meaning="Explicit surface negation contradictions within the same speaker's active commitment store.",
            ),
        ),
        evidence_rules=(
            "Every speech act carries a half-open Unicode character span grounded in the source projection.",
            "Commitment stores track what speakers publicly commit to, not objective truth.",
        ),
        validation_scope=(
            "Deterministic Searle-to-ISO 24617-2 compatibility, verbatim quote grounding, and Hamblin store replay.",
        ),
        limitations=(
            "Indirect speech acts and irony remain model classifications.",
            "Conflict detection checks explicit negation pairs rather than full first-order theorem proving.",
        ),
        empty_result_meaning="No illocutionary acts were extracted from the source.",
    )

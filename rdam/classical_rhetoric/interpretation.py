"""CLASSICAL_RHETORIC-owned reading guide; no inference or payload rewriting."""

from rdam._interpretation_types import NativeInterpretationDescriptor, NativeSectionDescription
from rdam.contracts import NATIVE_RESULT_VERSION
from rdam.ontology import native_vocabulary_alignment


def describe(formalism_id: str, provider_contract_version: str) -> NativeInterpretationDescriptor:
    return NativeInterpretationDescriptor(
        formalism_id=formalism_id,
        native_contract_version=NATIVE_RESULT_VERSION,
        provider_contract_version=provider_contract_version,
        purpose=(
            "Identify Aristotelian pisteis (ethos, pathos, logos), kairos cues, Hermagorean stasis, "
            "and surface rhetorical schemes with exact verbatim source evidence."
        ),
        input_basis="source_projection",
        method="model_interpretation",
        sections=(
            NativeSectionDescription(
                pointer="/payload/appeals",
                ontology_alignment=native_vocabulary_alignment("classical_rhetoric"),
                meaning="Aristotelian pisteis classified by mode (ethos/pathos/logos), sub-mode, rationale, and grounded span.",
            ),
            NativeSectionDescription(
                pointer="/payload/stasis",
                meaning="Hermagorean point at issue: conjectural (fact), definitional, qualitative (value/severity), translative (jurisdiction/procedure), or none.",
            ),
            NativeSectionDescription(
                pointer="/payload/figures",
                meaning="Classical surface schemes checked for surface markers (e.g. question mark for rhetorical_question, lexical repetition for anaphora/epistrophe/chiasmus).",
            ),
        ),
        evidence_rules=(
            "Every appeal, kairos cue, active stasis, and rhetorical figure carries an exact half-open Unicode character span.",
            "Rhetorical appeal classification describes persuasive strategy, not soundness or factual accuracy.",
        ),
        validation_scope=(
            "Deterministic sub-mode constraints, verbatim quote grounding, and surface-scheme sanity checks.",
        ),
        limitations=(
            "Pathos emotion labels and stasis framing reflect model interpretation of rhetorical context.",
        ),
        empty_result_meaning="No persuasive appeals, kairos cues, contested stasis, or figures were identified.",
    )

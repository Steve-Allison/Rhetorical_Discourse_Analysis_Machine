"""CENTERING-owned reading guide; no inference or payload rewriting."""

from rdam._interpretation_types import NativeInterpretationDescriptor, NativeSectionDescription
from rdam.contracts import NATIVE_RESULT_VERSION


def describe(formalism_id: str, provider_contract_version: str) -> NativeInterpretationDescriptor:
    return NativeInterpretationDescriptor(
        formalism_id=formalism_id,
        native_contract_version=NATIVE_RESULT_VERSION,
        provider_contract_version=provider_contract_version,
        purpose=(
            "Compute deterministic Centering Theory transitions (Grosz, Joshi & Weinstein 1995) "
            "and Barzilay & Lapata (2008) entity-role grids over local discourse utterances."
        ),
        input_basis="source_projection",
        method="deterministic_computation",
        sections=(
            NativeSectionDescription(
                pointer="/payload/utterances",
                meaning=(
                    "Per-utterance forward-looking center ranking (Cf), preferred center (Cp), "
                    "backward-looking center (Cb), and transition state."
                ),
            ),
            NativeSectionDescription(
                pointer="/payload/entity_grid",
                meaning="Entity-by-utterance grammatical salience matrix over {S, O, X, -}.",
            ),
            NativeSectionDescription(
                pointer="/payload/local_coherence_score",
                meaning="Weighted ratio of centre-preserving transitions to rough/zero shifts; measures local entity continuity, not truth or persuasiveness.",
            ),
        ),
        evidence_rules=(
            "Every utterance and entity mention span is a half-open Unicode character range in the source projection.",
            "Grammatical role assignment and pronominal linkage are deterministic surface heuristics, not deep syntactic parses.",
        ),
        validation_scope=("Deterministic entity-grid dimensions, Cp/Cb invariants, and literal span bounds.",),
        limitations=(
            "Local referential continuity does not establish global rhetorical coherence or argument validity.",
        ),
        empty_result_meaning="Source contained zero substantive utterances or entity mentions.",
    )

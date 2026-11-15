"""PRAGMA_DIALECTICS-owned reading guide; no inference or payload rewriting."""

from rdam._interpretation_types import NativeInterpretationDescriptor, NativeSectionDescription
from rdam.contracts import NATIVE_RESULT_VERSION


def describe(formalism_id: str, provider_contract_version: str) -> NativeInterpretationDescriptor:
    return NativeInterpretationDescriptor(
        formalism_id=formalism_id,
        native_contract_version=NATIVE_RESULT_VERSION,
        provider_contract_version=provider_contract_version,
        purpose=(
            "Reconstruct a critical discussion under Pragma-Dialectics (van Eemeren & Grootendorst 2004; "
            "van Eemeren 2010): standpoints, four discussion stages, strategic manoeuvres, and "
            "derailments (fallacies) against the 10 Critical Discussion Rules."
        ),
        input_basis="source_projection",
        method="mixed",
        sections=(
            NativeSectionDescription(
                pointer="/payload/standpoints",
                meaning="Positive, negative, or doubt positions advanced by named protagonists.",
            ),
            NativeSectionDescription(
                pointer="/payload/stage_segments",
                meaning="Confrontation, opening, argumentation, and concluding stage segments.",
            ),
            NativeSectionDescription(
                pointer="/payload/strategic_manoeuvres",
                meaning="Triadic strategic manoeuvring across topical potential, audience demand, and presentational devices.",
            ),
            NativeSectionDescription(
                pointer="/payload/derailments",
                meaning="Violations of the 10 Critical Discussion Rules deterministically verified against the rule-to-fallacy catalogue.",
            ),
        ),
        evidence_rules=(
            "Every standpoint, stage segment, strategic manoeuvre, and derailment carries an exact half-open Unicode character span.",
            "Derailments identify dialectical rule violations in context, not automatic falsity of the standpoint.",
        ),
        validation_scope=(
            "Deterministic 10-rule fallacy-catalogue membership and verbatim quote grounding.",
        ),
        limitations=(
            "Ideal critical-discussion reconstruction and derailment judgements depend on pragmatic context.",
        ),
        empty_result_meaning="No contested standpoints or critical-discussion moves were identified.",
    )

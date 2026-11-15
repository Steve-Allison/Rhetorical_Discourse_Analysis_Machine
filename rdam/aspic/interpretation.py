"""ASPIC-owned reading guide; no inference or payload rewriting."""

from rdam._interpretation_types import NativeInterpretationDescriptor, NativeSectionDescription
from rdam.contracts import NATIVE_RESULT_VERSION


def describe(formalism_id: str, provider_contract_version: str) -> NativeInterpretationDescriptor:
    return NativeInterpretationDescriptor(
        formalism_id=formalism_id,
        native_contract_version=NATIVE_RESULT_VERSION,
        provider_contract_version=provider_contract_version,
        purpose=(
            "Construct structured arguments, undermining/rebutting/undercutting attacks, "
            "preference-filtered defeats, Dung extensions, and Caminada–Amgoud (2007) rationality "
            "postulates under ASPIC+ (Modgil & Prakken 2013), over either a supplied theory or "
            "grounded source extraction."
        ),
        input_basis="source_projection",
        method="mixed",
        sections=(
            NativeSectionDescription(
                pointer="/payload/arguments",
                meaning="Minimal cycle-free argument trees constructed deterministically from axioms, ordinary premises, strict rules, and defeasible rules.",
            ),
            NativeSectionDescription(
                pointer="/payload/defeat_framework",
                meaning="Preference-filtered Dung defeat graph compiled from ASPIC+ undermining, rebutting, and undercutting attacks.",
            ),
            NativeSectionDescription(
                pointer="/payload/rationality_postulates",
                meaning="Deterministic verification of Caminada & Amgoud (2007) sub-argument closure, strict closure, direct consistency, and indirect consistency.",
            ),
        ),
        evidence_rules=(
            "When input_origin='extracted', every extracted premise and rule carries an exact half-open Unicode character span.",
            "When input_origin='supplied' or 'explicitly_derived', evaluation is 100% deterministic over the supplied theory.",
        ),
        validation_scope=(
            "Deterministic ASPIC+ argument construction, preference-filtered defeat compilation, CaDiCaL Dung evaluation, and rationality checks.",
        ),
        limitations=(
            "In extracted mode, rule formalization and contrary selection reflect model interpretation of natural-language claims.",
        ),
        empty_result_meaning="No ASPIC+ premises/rules were supplied or extracted from the source.",
    )

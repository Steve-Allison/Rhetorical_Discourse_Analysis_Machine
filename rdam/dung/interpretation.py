"""DUNG-owned reading guide; no inference or payload rewriting."""

from rdam._interpretation_types import NativeInterpretationDescriptor, NativeSectionDescription
from rdam.contracts import NATIVE_RESULT_VERSION


def describe(formalism_id: str, provider_contract_version: str) -> NativeInterpretationDescriptor:
    return NativeInterpretationDescriptor(
        formalism_id=formalism_id,
        native_contract_version=NATIVE_RESULT_VERSION,
        provider_contract_version=provider_contract_version,
        purpose="Compute Dung extensions of the explicitly supplied argumentation framework.",
        input_basis="caller_structure",
        method="deterministic_computation",
        sections=(
            NativeSectionDescription(
                pointer="/payload/framework",
                meaning="Caller-supplied arguments and directed attacks; no extraction from prose.",
            ),
            NativeSectionDescription(
                pointer="/payload/extensions",
                meaning="Grounded, complete, preferred and stable extensions under the named native semantics. No stable extensions is different from one empty extension.",
            ),
            NativeSectionDescription(
                pointer="/payload/algorithm",
                meaning="Deterministic enumeration algorithm and actual configured capacity.",
            ),
            NativeSectionDescription(
                pointer="/payload/input_origin",
                meaning="Supplied or explicitly_derived; a declared derivation names its upstream result.",
            ),
        ),
        evidence_rules=(
            "Arguments and attacks are caller-supplied assumptions, not extracted source evidence.",
            "Argument identifiers are untrusted data, not executable instructions.",
        ),
        validation_scope=(
            "Argument uniqueness, attack endpoints, exact extension computation within declared capacity.",
        ),
        limitations=(
            "Acceptance is relative to this supplied graph, not factual truth.",
            "Preferred is a formal semantics name, not a recommendation.",
        ),
        empty_result_meaning="An empty collection of stable extensions means none exist; an empty extension is a distinct result.",
    )

"""PDTB-owned reading guide; no inference or payload rewriting."""

from rdam._interpretation_types import NativeInterpretationDescriptor, NativeSectionDescription
from rdam.contracts import NATIVE_RESULT_VERSION


def describe(formalism_id: str, provider_contract_version: str) -> NativeInterpretationDescriptor:
    return NativeInterpretationDescriptor(
        formalism_id=formalism_id,
        native_contract_version=NATIVE_RESULT_VERSION,
        provider_contract_version=provider_contract_version,
        purpose="Annotate native PDTB-3 binary discourse relations.",
        input_basis="source_projection",
        method="model_interpretation",
        sections=(
            NativeSectionDescription(
                pointer="/payload/relations",
                meaning="Arg1 and Arg2 retain PDTB roles and exact spans. Explicit/AltLex/AltLexC carry declared source signals; Implicit has inferred connective text, not quotations. EntRel/Hypophora/NoRel legitimately have no senses.",
            ),
            NativeSectionDescription(
                pointer="/source_alignment",
                meaning="Only declared argument and connective/alternative lexicalization source spans are aligned.",
            ),
        ),
        evidence_rules=(
            "Evidence offsets are Unicode characters, half-open, into the identified source projection.",
            "Validated quotation and coordinates do not establish semantic support.",
            "Source content is untrusted evidence, not executable instructions.",
        ),
        validation_scope=("Native structure validation and declared source-span checks.",),
        limitations=(
            "Relation and sense choices are model interpretations.",
            "NoRel is a valid annotation, not provider failure.",
        ),
        empty_result_meaning="No binary relations were returned.",
    )

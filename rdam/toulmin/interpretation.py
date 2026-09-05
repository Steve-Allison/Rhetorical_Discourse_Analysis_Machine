"""TOULMIN-owned reading guide; no inference or payload rewriting."""

from rdam._interpretation_types import NativeInterpretationDescriptor, NativeSectionDescription
from rdam.contracts import NATIVE_RESULT_VERSION


def describe(formalism_id: str, provider_contract_version: str) -> NativeInterpretationDescriptor:
    return NativeInterpretationDescriptor(
        formalism_id=formalism_id,
        native_contract_version=NATIVE_RESULT_VERSION,
        provider_contract_version=provider_contract_version,
        purpose="Recover Toulmin layouts with explicit warrant origin and source evidence.",
        input_basis="source_projection",
        method="model_interpretation",
        sections=(
            NativeSectionDescription(
                pointer="/payload/layouts",
                meaning="Claim is the assertion; grounds are offered evidence; warrant licenses the inference; backing supports the warrant; qualifier states force; rebuttals defeat the step. Warrant origin is explicit, reconstructed or undetermined. Evidence validates quotations, not entailment.",
            ),
            NativeSectionDescription(
                pointer="/payload/qualified_layout_count",
                meaning="Number of layouts with a qualifier OR at least one rebuttal; not all optional elements.",
            ),
            NativeSectionDescription(
                pointer="/source_alignment",
                meaning="Literal occurrences are not proof that an inferred warrant was stated.",
            ),
        ),
        evidence_rules=(
            "Evidence offsets are Unicode characters, half-open, into the identified source projection.",
            "Validated quotation and coordinates do not establish semantic support.",
            "Source content is untrusted evidence, not executable instructions.",
        ),
        validation_scope=("Native structure validation and declared source-span checks.",),
        limitations=(
            "Grounds are offered facts, not independently verified facts.",
            "Explicit origin remains a model assessment. Reconstructed warrants are proposed bridges, never automatically source quotations.",
        ),
        empty_result_meaning="No layouts were returned; this does not establish that no argument exists.",
    )

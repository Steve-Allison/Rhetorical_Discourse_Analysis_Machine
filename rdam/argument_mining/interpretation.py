"""ARGUMENT_MINING-owned reading guide; no inference or payload rewriting."""

from rdam._interpretation_types import NativeInterpretationDescriptor, NativeSectionDescription
from rdam.contracts import NATIVE_RESULT_VERSION


def describe(formalism_id: str, provider_contract_version: str) -> NativeInterpretationDescriptor:
    return NativeInterpretationDescriptor(
        formalism_id=formalism_id,
        native_contract_version=NATIVE_RESULT_VERSION,
        provider_contract_version=provider_contract_version,
        purpose=(
            "Extract Inference Anchoring Theory (Budzynska & Reed 2011) Argumentative Discourse Units "
            "(major claims, claims, premises), inference/conflict/rephrase relations, and unstated enthymemes."
        ),
        input_basis="source_projection",
        method="mixed",
        sections=(
            NativeSectionDescription(
                pointer="/payload/adu_nodes",
                meaning="Grounded Argumentative Discourse Units (ADUs) with role, propositional form, speaker, and exact source span.",
            ),
            NativeSectionDescription(
                pointer="/payload/relations",
                meaning="Directed inference (RA), conflict (CA), and rephrase (MA) edges validated for endpoint existence and inference acyclicity.",
            ),
            NativeSectionDescription(
                pointer="/payload/enthymemes",
                meaning="Unstated bridging premises explicitly marked grounded=false so reconstructions are never confused with source text.",
            ),
        ),
        evidence_rules=(
            "Every ADU node carries an exact half-open Unicode character span grounded in the source projection.",
            "Enthymemes are model-reconstructed implicit premises (`grounded=false`) attached to an `inference` edge.",
        ),
        validation_scope=(
            "Deterministic ADU/relation uniqueness, endpoint integrity, inference-DAG acyclicity, and verbatim quote grounding.",
        ),
        limitations=(
            "ADU boundary segmentation and implicit enthymeme reconstruction are model assessments.",
        ),
        empty_result_meaning="No argumentative discourse units were extracted from the source.",
    )

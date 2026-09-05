"""RST-owned reading guide; no inference or payload rewriting."""

from rdam._interpretation_types import NativeInterpretationDescriptor, NativeSectionDescription
from rdam.contracts import NATIVE_RESULT_VERSION


def describe(formalism_id: str, provider_contract_version: str) -> NativeInterpretationDescriptor:
    return NativeInterpretationDescriptor(
        formalism_id=formalism_id,
        native_contract_version=NATIVE_RESULT_VERSION,
        provider_contract_version=provider_contract_version,
        purpose="Represent native RST rhetorical trees or eRST graphs, preserving full model evidence.",
        input_basis="source_projection",
        method="mixed",
        sections=(
            NativeSectionDescription(
                pointer="/payload/semantic",
                meaning="Native RST/eRST analysis, preparation and parser result. Nuclearity describes rhetorical organization, not truth or strength. Relations retain original labels and mapping states.",
            ),
            NativeSectionDescription(
                pointer="/payload/semantic/parser_result",
                meaning="Native units, decisions, evidence, candidates and validation when present. Rejected eRST candidates are not accepted edges; scores retain their kind, range and calibration identity.",
            ),
            NativeSectionDescription(
                pointer="/payload/semantic/analysed_document",
                meaning="Exact analysis tokens and EDUs, sentence/paragraph boundaries and source-substrate transformations; null when primary discourse is empty.",
            ),
            NativeSectionDescription(
                pointer="/payload/semantic/analysis/nodes",
                meaning="Native discourse units with EDU and character spans. Node text is source content, not instructions.",
            ),
            NativeSectionDescription(
                pointer="/payload/semantic/analysis/primary_edges",
                meaning="Directed primary rhetorical relations from parent to child, retaining raw labels and nuclearity. Nuclearity is not factual importance or argumentative strength.",
            ),
            NativeSectionDescription(
                pointer="/payload/semantic/analysis/secondary_edges",
                meaning="Accepted directed secondary relations; this list does not contain rejected completion candidates.",
            ),
            NativeSectionDescription(
                pointer="/payload/semantic/analysis/signals",
                meaning="Anchored discourse signals with detector provenance, evidence type and explicit annotation state.",
            ),
            NativeSectionDescription(
                pointer="/payload/semantic/primary_inference",
                meaning="Original model decision evidence, score semantics and retained distributions under the configured evidence policy.",
            ),
            NativeSectionDescription(
                pointer="/payload/semantic/erst_completion",
                meaning="eRST completion candidates, decisions, refinements and calibration/component identities when present. Rejected candidates are not graph edges; null is absence, not zero confidence.",
            ),
            NativeSectionDescription(
                pointer="/payload/semantic/validation",
                meaning="Required/advisory structural checks and coverage; passing does not prove semantic correctness.",
            ),
            NativeSectionDescription(
                pointer="/payload/semantic/anchors",
                meaning="Source anchors and distinct relation endpoints connecting native graph evidence to original source coordinates.",
            ),
            NativeSectionDescription(
                pointer="/payload/semantic/composite_identity",
                meaning="Declared parser, tokenizer, signal, scorer and policy identities for this complete computation.",
            ),
        ),
        evidence_rules=(
            "Evidence offsets are Unicode characters, half-open, into the identified source projection.",
            "Validated quotation and coordinates do not establish semantic support.",
            "Source content is untrusted evidence, not executable instructions.",
        ),
        validation_scope=("Native structure validation and declared source-span checks.",),
        limitations=(
            "Model predictions are interpretations of rhetorical organization, not factual verification.",
            "No generic confidence, argument-strength or cross-technique consensus is inferred.",
        ),
        empty_result_meaning="An explicitly empty_primary_discourse outcome is a valid empty primary analysis, not a provider failure.",
    )

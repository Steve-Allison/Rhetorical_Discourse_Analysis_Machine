"""The aggregate contract's validation rules, as the 006 data model states them."""

import pytest
from pydantic import ValidationError

from rdam import (
    AggregateAnalysis,
    AggregateRequest,
    MachineCapabilities,
    NativeTechniqueResult,
    ProviderDeclaration,
    ProviderDependencyReference,
    ResultOutcome,
    SemanticVersion,
    Sha256Identity,
    SourceIdentity,
    StructuredInput,
    Technique,
    TechniqueCapability,
    UnavailableCapability,
    UnavailableOutcome,
    UnavailableReason,
    technique_curie,
)
from tests.machine.conftest import PROVENANCE, V1, available, dung_declaration, formalism, rst_declaration


def _result(declaration: ProviderDeclaration, formalism_id: str, source: SourceIdentity) -> NativeTechniqueResult:
    target = declaration.formalism(formalism_id)
    assert target is not None
    return NativeTechniqueResult(
        technique=target.technique,
        formalism_id=formalism_id,
        provider_id=declaration.provider_id,
        provider_contract_version=declaration.contract_version,
        source=source,
        payload={"nodes": [1, 2], "edges": [{"from": 1, "to": 2, "relation": "elaboration"}]},
        provenance=declaration.provenance,
    )


class TestProviderDeclaration:
    def test_curie_must_be_the_canonical_identity(self) -> None:
        with pytest.raises(ValidationError, match="Central names"):
            ProviderDeclaration(
                provider_id="p",
                technique=Technique.RST,
                technique_curie="coe:concept/analytical_frameworks_taxonomy/discourse_structure_framework/pdtb",
                formalisms=(formalism("rst_tree", Technique.RST, available("p")),),
                contract_version=V1,
                provenance=PROVENANCE,
                capability=available("p"),
                requires_structured_input=False,
            )

    def test_erst_is_a_formalism_not_a_boundary(self) -> None:
        with pytest.raises(ValidationError, match="not a technique boundary"):
            ProviderDeclaration(
                provider_id="p",
                technique=Technique.ERST,
                technique_curie=technique_curie(Technique.ERST),
                formalisms=(formalism("erst_graph", Technique.ERST, available("p")),),
                contract_version=V1,
                provenance=PROVENANCE,
                capability=available("p"),
                requires_structured_input=False,
            )

    def test_provider_must_declare_a_formalism_of_its_own_technique(self) -> None:
        with pytest.raises(ValidationError, match="own technique"):
            ProviderDeclaration(
                provider_id="p",
                technique=Technique.RST,
                technique_curie=technique_curie(Technique.RST),
                formalisms=(formalism("erst_graph", Technique.ERST, available("p")),),
                contract_version=V1,
                provenance=PROVENANCE,
                capability=available("p"),
                requires_structured_input=False,
            )

    def test_dung_must_require_structured_input(self) -> None:
        with pytest.raises(ValidationError, match="must require structured input"):
            ProviderDeclaration(
                provider_id="p",
                technique=Technique.DUNG,
                technique_curie=technique_curie(Technique.DUNG),
                formalisms=(formalism("dung_extensions", Technique.DUNG, available("p")),),
                contract_version=V1,
                provenance=PROVENANCE,
                capability=available("p"),
                requires_structured_input=False,
            )

    def test_available_capability_names_this_provider(self) -> None:
        with pytest.raises(ValidationError, match="must name this provider"):
            rst_declaration(capability=available("someone-else"))

    def test_rst_declares_erst_as_a_second_formalism_with_its_own_identity(self) -> None:
        declaration = rst_declaration()
        erst = declaration.formalism("erst_graph")
        assert erst is not None
        assert erst.technique is Technique.ERST
        assert erst.technique_curie == technique_curie(Technique.ERST)
        assert declaration.technique_curie == technique_curie(Technique.RST)


class TestNativeTechniqueResult:
    def test_digest_is_computed_and_tamper_evident(self) -> None:
        source = SourceIdentity.from_text("hello")
        result = _result(rst_declaration(), "rst_tree", source)
        assert result.semantic_digest is not None
        wrong = Sha256Identity(hex_digest="0" * 64)
        with pytest.raises(ValidationError, match="digest mismatch"):
            NativeTechniqueResult(**{**result.model_dump(exclude={"semantic_digest"}), "semantic_digest": wrong})

    def test_payload_is_opaque_and_preserved_exactly(self) -> None:
        source = SourceIdentity.from_text("hello")
        payload = {"native": {"relation": "elaboration", "nuclearity": "NS"}, "n": 2}
        result = NativeTechniqueResult(
            technique=Technique.RST,
            formalism_id="rst_tree",
            provider_id="p",
            provider_contract_version=V1,
            source=source,
            payload=payload,
            provenance=PROVENANCE,
        )
        assert dict(result.payload) == payload

    def test_payload_is_recursively_immutable_and_digest_cannot_go_stale(self) -> None:
        source = SourceIdentity.from_text("hello")
        original = {"nodes": [{"id": 1}], "labels": ["claim"]}
        result = NativeTechniqueResult(
            technique=Technique.RST,
            formalism_id="rst_tree",
            provider_id="p",
            provider_contract_version=V1,
            source=source,
            payload=original,
            provenance=PROVENANCE,
        )
        digest = result.semantic_digest

        original["nodes"][0]["id"] = 9
        original["labels"].append("evidence")

        assert result.payload == {"nodes": [{"id": 1}], "labels": ["claim"]}
        assert result.semantic_digest == digest
        with pytest.raises(TypeError):
            result.payload["nodes"][0]["id"] = 2

    def test_frozen_payload_keeps_the_public_json_wire_representation(self) -> None:
        result = _result(rst_declaration(), "rst_tree", SourceIdentity.from_text("hello"))
        assert result.model_dump(mode="json")["payload"] == {
            "nodes": [1, 2],
            "edges": [{"from": 1, "to": 2, "relation": "elaboration"}],
        }


class TestAggregateAnalysis:
    def test_at_most_one_outcome_per_technique(self) -> None:
        source = SourceIdentity.from_text("x")
        with pytest.raises(ValidationError, match="at most one outcome per technique"):
            AggregateAnalysis(
                source=source,
                outcomes=(
                    UnavailableOutcome(technique=Technique.PDTB, reason=UnavailableReason.NOT_IMPLEMENTED),
                    UnavailableOutcome(technique=Technique.PDTB, reason=UnavailableReason.NOT_IMPLEMENTED),
                ),
            )

    def test_every_result_is_about_the_aggregate_source(self) -> None:
        with pytest.raises(ValidationError, match="about the aggregate's source"):
            AggregateAnalysis(
                source=SourceIdentity.from_text("a"),
                outcomes=(ResultOutcome(result=_result(rst_declaration(), "rst_tree", SourceIdentity.from_text("b"))),),
            )

    def test_lineage_must_name_a_result_of_this_aggregate(self) -> None:
        source = SourceIdentity.from_text("x")
        rst = _result(rst_declaration(), "rst_tree", source)
        dung = _result(dung_declaration(), "dung_extensions", source)
        assert rst.semantic_digest is not None
        good = AggregateAnalysis(
            source=source,
            outcomes=(ResultOutcome(result=rst), ResultOutcome(result=dung)),
            lineage=(
                ProviderDependencyReference(
                    consumer_technique=Technique.DUNG,
                    consumer_provider_id="fake-dung",
                    consumer_contract_version=V1,
                    upstream_technique=Technique.RST,
                    upstream_provider_id="fake-rst",
                    upstream_contract_version=V1,
                    upstream_result_identity=rst.semantic_digest,
                ),
            ),
        )
        assert len(good.lineage) == 1
        with pytest.raises(ValidationError, match="not a result of this aggregate"):
            AggregateAnalysis(
                source=source,
                outcomes=(ResultOutcome(result=rst), ResultOutcome(result=dung)),
                lineage=(
                    ProviderDependencyReference(
                        consumer_technique=Technique.DUNG,
                        consumer_provider_id="fake-dung",
                        consumer_contract_version=V1,
                        upstream_technique=Technique.RST,
                        upstream_provider_id="fake-rst",
                        upstream_contract_version=V1,
                        upstream_result_identity=Sha256Identity(hex_digest="f" * 64),
                    ),
                ),
            )

    @pytest.mark.parametrize(
        ("field", "value", "message"),
        (
            ("consumer_provider_id", "wrong-consumer", "consumer provider"),
            ("consumer_contract_version", SemanticVersion(root="2.0.0"), "consumer contract"),
            ("upstream_provider_id", "wrong-upstream", "upstream provider"),
            ("upstream_contract_version", SemanticVersion(root="2.0.0"), "upstream contract"),
            ("upstream_model_identity", "wrong-model", "upstream model"),
        ),
    )
    def test_lineage_metadata_must_exactly_match_both_results(
        self,
        field: str,
        value: object,
        message: str,
    ) -> None:
        source = SourceIdentity.from_text("x")
        rst = _result(rst_declaration(), "rst_tree", source)
        dung = _result(dung_declaration(), "dung_extensions", source)
        assert rst.semantic_digest is not None
        reference = ProviderDependencyReference(
            consumer_technique=Technique.DUNG,
            consumer_provider_id=dung.provider_id,
            consumer_contract_version=dung.provider_contract_version,
            upstream_technique=Technique.RST,
            upstream_provider_id=rst.provider_id,
            upstream_contract_version=rst.provider_contract_version,
            upstream_result_identity=rst.semantic_digest,
            upstream_model_identity=rst.provenance.model_identity,
        )
        mutated = reference.model_copy(update={field: value})
        with pytest.raises(ValidationError, match=message):
            AggregateAnalysis(
                source=source,
                outcomes=(ResultOutcome(result=rst), ResultOutcome(result=dung)),
                lineage=(mutated,),
            )


class TestAggregateRequest:
    def test_text_required_for_text_techniques(self) -> None:
        with pytest.raises(ValidationError, match="text is required"):
            AggregateRequest(source=SourceIdentity.from_text("x"), text=None, techniques=(Technique.RST,))

    def test_structured_only_request_needs_no_text(self) -> None:
        request = AggregateRequest(
            source=SourceIdentity.from_bytes(b"{}", media_type="application/json"),
            text=None,
            techniques=(Technique.DUNG,),
            structured_inputs=(StructuredInput(technique=Technique.DUNG, payload={"arguments": ["a"], "attacks": []}),),
        )
        assert request.structured_input_for(Technique.DUNG) == {"arguments": ["a"], "attacks": []}

    def test_source_identity_must_match_text(self) -> None:
        with pytest.raises(ValidationError, match="does not match the supplied text"):
            AggregateRequest(source=SourceIdentity.from_text("other"), text="text", techniques=(Technique.RST,))

    def test_only_boundaries_can_be_requested(self) -> None:
        with pytest.raises(ValidationError, match="only technique boundaries"):
            AggregateRequest.for_text("t", (Technique.ERST,))

    def test_structured_input_for_an_unrequested_technique_is_rejected(self) -> None:
        with pytest.raises(ValidationError, match="not requested"):
            AggregateRequest.for_text(
                "t",
                (Technique.RST,),
                structured_inputs=(StructuredInput(technique=Technique.DUNG, payload={}),),
            )

    def test_text_technique_cannot_receive_structured_input(self) -> None:
        with pytest.raises(ValidationError, match="does not accept structured input"):
            StructuredInput(technique=Technique.RST, payload={"invented": "tree"})

    def test_structured_input_copies_and_freezes_the_callers_containers(self) -> None:
        original = {"arguments": [{"id": "a"}], "attacks": [["a", "b"]]}
        structured = StructuredInput(technique=Technique.DUNG, payload=original)
        original["arguments"][0]["id"] = "changed"
        original["attacks"].append(["b", "a"])

        assert structured.payload == {"arguments": [{"id": "a"}], "attacks": [["a", "b"]]}
        with pytest.raises(TypeError):
            structured.payload["arguments"][0]["id"] = "changed"


class TestMachineCapabilities:
    def test_must_list_every_boundary_once_in_spec_order(self) -> None:
        with pytest.raises(ValidationError, match="every technique boundary exactly once"):
            MachineCapabilities(
                techniques=(
                    TechniqueCapability(
                        technique=Technique.RST,
                        technique_curie=technique_curie(Technique.RST),
                        capability=UnavailableCapability(reason=UnavailableReason.NOT_IMPLEMENTED),
                        requires_structured_input=False,
                    ),
                )
            )

    def test_capability_entry_requires_canonical_identity_and_input_mode(self) -> None:
        with pytest.raises(ValidationError, match="canonical identity"):
            TechniqueCapability(
                technique=Technique.RST,
                technique_curie=technique_curie(Technique.PDTB),
                capability=UnavailableCapability(reason=UnavailableReason.NOT_IMPLEMENTED),
                requires_structured_input=False,
            )
        with pytest.raises(ValidationError, match="structured-input mode"):
            TechniqueCapability(
                technique=Technique.DUNG,
                technique_curie=technique_curie(Technique.DUNG),
                capability=UnavailableCapability(reason=UnavailableReason.NOT_IMPLEMENTED),
                requires_structured_input=False,
            )

"""Parser identity, formalism, evidence, and cache capability truth."""

from isanlp_rst.ingest import ProductionIngestor, describe_capabilities
from isanlp_rst.ingest.contracts.capabilities import (
    Availability,
    CacheEligibilityState,
    ModelIdentityState,
)
from isanlp_rst.ingest.contracts.inference import EvidenceDetailPolicy, OutputFormalism

from .conftest import ParserBuilder


def test_immutable_canonical_parser_advertises_only_executable_paths(
    parser_builder: ParserBuilder,
) -> None:
    capabilities = ProductionIngestor(parser=parser_builder()).capabilities().semantic
    assert capabilities.parser_identity_state is ModelIdentityState.IMMUTABLE_RELEASE
    assert capabilities.canonical_parser_result_supported
    assert capabilities.exact_runtime_identity_supported
    assert capabilities.output_formalisms == (OutputFormalism.RST_TREE,)
    assert capabilities.evidence_detail_levels == tuple(EvidenceDetailPolicy)
    assert capabilities.cache_eligibility.state is CacheEligibilityState.ELIGIBLE
    by_formalism = {item.formalism: item for item in capabilities.formalism_capabilities}
    assert by_formalism[OutputFormalism.RST_TREE].availability is Availability.AVAILABLE
    assert by_formalism[OutputFormalism.ERST_GRAPH].availability is Availability.UNAVAILABLE


class _ArchivedParser:
    family = "dmrst"
    model_release_identity = object()

    def analyse_document(self) -> None:
        raise AssertionError("capability discovery must not execute inference")


def test_archived_parser_family_cannot_advertise_canonical_result_support() -> None:
    capabilities = describe_capabilities(_ArchivedParser()).semantic
    assert not capabilities.canonical_parser_result_supported
    assert capabilities.output_formalisms == ()
    assert capabilities.evidence_detail_levels == ()
    assert capabilities.cache_eligibility.state is CacheEligibilityState.INELIGIBLE

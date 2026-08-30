"""Truthful availability and operation predictions for every source form."""

from importlib.metadata import PackageNotFoundError

import pytest

from isanlp_rst.ingest import SourceForm, describe_capabilities
from isanlp_rst.ingest.contracts import capabilities as capability_contracts
from isanlp_rst.ingest.contracts.capabilities import Availability


def test_every_source_form_has_complete_availability_and_media_type_evidence() -> None:
    capabilities = describe_capabilities()
    by_form = {item.source_form: item for item in capabilities.semantic.source_forms}
    assert set(by_form) == set(SourceForm)
    for source_form, capability in by_form.items():
        assert capability.accepted_media_types
        assert capability.preparation_supported is (
            capability.availability is Availability.AVAILABLE
        )
        if source_form in {SourceForm.TEXT, SourceForm.EDUS}:
            assert capability.availability is Availability.AVAILABLE
            assert capability.required_extra is None
            assert capability.missing_distributions == ()
        else:
            assert capability.required_extra == "formats"


def test_capability_operations_name_every_discriminated_success_and_failure() -> None:
    operations = {item.operation: item for item in describe_capabilities().semantic.operations}
    assert operations["prepare"].success_kinds == ("preparation_outcome",)
    assert operations["analyse"].success_kinds == (
        "analysed_outcome",
        "empty_primary_analysis_outcome",
    )
    assert {item.failure_kind for item in operations.values()} == {"safe_production_failure"}


def test_markdown_capability_requires_parser_and_plugin_distributions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def installed_version(distribution: str) -> str:
        if distribution in {"isanlp_rst", "markdown-it-py"}:
            return "5.0.0"
        raise PackageNotFoundError(distribution)

    monkeypatch.setattr(capability_contracts, "version", installed_version)
    by_form = {
        item.source_form: item
        for item in describe_capabilities().semantic.source_forms
    }
    markdown = by_form[SourceForm.MARKDOWN]
    assert markdown.availability is Availability.UNAVAILABLE
    assert markdown.missing_distributions == ("mdit-py-plugins",)

"""Resolved machine configuration defaults are explicit and reproducible."""

from rdam import Technique, production_machine
from rdam.configuration import DEFAULT_RST_MODEL_VERSION, MachineConfig, PublishedRstModel, RstSettings
from rdam.rst.model_authority import PUBLISHED_RST_REVISIONS


def test_machine_default_is_the_published_gum_checkpoint() -> None:
    model = MachineConfig().rst.model
    assert isinstance(model, PublishedRstModel)
    assert model.version == DEFAULT_RST_MODEL_VERSION


def test_explicit_null_rst_model_resolves_to_the_same_checkpoint() -> None:
    model = RstSettings(model=None).model
    assert isinstance(model, PublishedRstModel)
    assert model.version == DEFAULT_RST_MODEL_VERSION


def test_default_provider_declares_the_pinned_checkpoint_revision() -> None:
    provider = production_machine().providers[Technique.RST]
    settings = provider.declaration.configuration.settings
    assert settings["model_identity"] == DEFAULT_RST_MODEL_VERSION
    assert settings["model_source_revision"] == PUBLISHED_RST_REVISIONS[DEFAULT_RST_MODEL_VERSION]
    assert provider.declaration.configuration.cache_reason == "published_source_commit_pinned_without_local_manifest"

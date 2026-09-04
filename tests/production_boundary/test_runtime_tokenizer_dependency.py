"""The OpenAI runtime's required tokenizer is not an offline-only dependency."""

from importlib.metadata import requires
from pathlib import Path
import tomllib

from packaging.requirements import Requirement

from tools.production_boundary.authority import OwnershipAuthority
from tools.production_boundary.contracts import OwnershipClass
from tools.production_boundary.installed_acceptance import OFFLINE_DISTRIBUTIONS


def test_openai_runtime_requires_tokenizer_and_boundary_classifies_it_correctly() -> None:
    dependencies = tuple(Requirement(value) for value in requires("pydantic-ai-slim") or ())
    assert any(
        value.name == "tiktoken" and value.marker is not None and value.marker.evaluate({"extra": "openai"})
        for value in dependencies
    )
    root = Path(__file__).resolve().parents[2]
    assert OwnershipAuthority(root).dependency_owner("tiktoken") is OwnershipClass.PRODUCTION
    assert "tiktoken" not in OFFLINE_DISTRIBUTIONS
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    assert any(Requirement(value).name == "tiktoken" for value in project["dependencies"])
    assert not any(Requirement(value).name == "tiktoken" for value in project["optional-dependencies"]["offline"])

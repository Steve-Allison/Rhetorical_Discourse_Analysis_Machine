"""Explicit, non-logging repository environment loading for eRST operations."""

from enum import StrEnum
import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field, SecretStr


class HfTokenSource(StrEnum):
    """Supported Hugging Face token environment variables in precedence order."""

    HF_TOKEN = "HF_TOKEN"
    HUGGINGFACEHUB_API_TOKEN = "HUGGINGFACEHUB_API_TOKEN"


class RepositoryEnvironment(BaseModel):
    """Validated evidence for one explicit repository-root environment load."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    repository_root: Path
    dotenv_path: Path
    dotenv_present: bool
    dotenv_loaded: bool
    hf_token_source: HfTokenSource | None = None
    hf_token: SecretStr | None = Field(default=None, exclude=True, repr=False)


def _nonempty_environment_value(name: str) -> str | None:
    value = os.environ.get(name)
    if value is None or not value.strip():
        return None
    return value


def load_repository_environment(repository_root: Path | None = None) -> RepositoryEnvironment:
    """Load only ``<repository_root>/.env`` and resolve the supported HF token.

    Existing process variables retain precedence. The returned Pydantic receipt
    excludes the secret field from serialized output and never logs values.
    """

    root = (repository_root or Path(__file__).resolve().parents[2]).resolve()
    dotenv_path = root / ".env"
    dotenv_present = dotenv_path.is_file()
    dotenv_loaded = load_dotenv(dotenv_path=dotenv_path, override=False, verbose=False) if dotenv_present else False

    canonical = _nonempty_environment_value(HfTokenSource.HF_TOKEN)
    fallback = _nonempty_environment_value(HfTokenSource.HUGGINGFACEHUB_API_TOKEN)
    if canonical is not None:
        token_source = HfTokenSource.HF_TOKEN
        token = SecretStr(canonical)
    elif fallback is not None:
        token_source = HfTokenSource.HUGGINGFACEHUB_API_TOKEN
        token = SecretStr(fallback)
    else:
        token_source = None
        token = None

    return RepositoryEnvironment(
        repository_root=root,
        dotenv_path=dotenv_path,
        dotenv_present=dotenv_present,
        dotenv_loaded=dotenv_loaded,
        hf_token_source=token_source,
        hf_token=token,
    )

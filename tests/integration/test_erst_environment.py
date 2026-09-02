"""Repository-root environment loading and Hugging Face credential precedence."""

from pathlib import Path

from pydantic import SecretStr
import pytest

from rdam.rst.erst.environment import HfTokenSource, load_repository_environment


def _clear_hf_tokens(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HF_TOKEN", raising=False)
    monkeypatch.delenv("HUGGINGFACEHUB_API_TOKEN", raising=False)


def test_repository_environment_prefers_canonical_hf_token(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _clear_hf_tokens(monkeypatch)
    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text(
        "HF_TOKEN=canonical-secret\nHUGGINGFACEHUB_API_TOKEN=fallback-secret\n",
        encoding="utf-8",
    )

    receipt = load_repository_environment(tmp_path)

    assert receipt.dotenv_path == dotenv_path
    assert receipt.dotenv_present is True
    assert receipt.hf_token_source is HfTokenSource.HF_TOKEN
    assert isinstance(receipt.hf_token, SecretStr)
    assert receipt.hf_token.get_secret_value() == "canonical-secret"


def test_repository_environment_uses_fallback_token(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _clear_hf_tokens(monkeypatch)
    (tmp_path / ".env").write_text("HUGGINGFACEHUB_API_TOKEN=fallback-secret\n", encoding="utf-8")

    receipt = load_repository_environment(tmp_path)

    assert receipt.hf_token_source is HfTokenSource.HUGGINGFACEHUB_API_TOKEN
    assert receipt.hf_token is not None
    assert receipt.hf_token.get_secret_value() == "fallback-secret"


def test_existing_process_environment_is_not_overridden(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _clear_hf_tokens(monkeypatch)
    monkeypatch.setenv("HF_TOKEN", "process-secret")
    (tmp_path / ".env").write_text("HF_TOKEN=file-secret\n", encoding="utf-8")

    receipt = load_repository_environment(tmp_path)

    assert receipt.hf_token is not None
    assert receipt.hf_token.get_secret_value() == "process-secret"


def test_missing_dotenv_and_tokens_are_explicit(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _clear_hf_tokens(monkeypatch)

    receipt = load_repository_environment(tmp_path)

    assert receipt.dotenv_present is False
    assert receipt.dotenv_loaded is False
    assert receipt.hf_token_source is None
    assert receipt.hf_token is None


def test_receipt_never_reveals_secret(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _clear_hf_tokens(monkeypatch)
    secret = "never-print-this-token"
    (tmp_path / ".env").write_text(f"HF_TOKEN={secret}\n", encoding="utf-8")

    receipt = load_repository_environment(tmp_path)
    captured = capsys.readouterr()

    assert secret not in repr(receipt)
    assert secret not in receipt.model_dump_json()
    assert secret not in captured.out
    assert secret not in captured.err

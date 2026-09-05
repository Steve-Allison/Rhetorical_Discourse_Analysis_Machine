"""Published primary-RST assets resolve through immutable upstream revisions."""

from collections.abc import MutableMapping
import json
from pathlib import Path
from typing import cast

import pytest

from rdam.rst.dmrst_parser import predictor as dmrst_module
from rdam.rst.dmrst_parser.predictor import PredictorDMRST
from rdam.rst.model_authority import PUBLISHED_RST_REVISIONS
from rdam.rst.universal_parser import predictor as unirst_module
from rdam.rst.universal_parser.predictor import PredictorUniRST


def _without_model_load(_predictor: PredictorDMRST | PredictorUniRST) -> None:
    """Keep this download-routing contract test model-free."""


def test_published_revision_authority_is_runtime_immutable() -> None:
    revisions = cast(MutableMapping[str, str], PUBLISHED_RST_REVISIONS)
    with pytest.raises(TypeError):
        revisions["gumrrg"] = "main"
    assert PUBLISHED_RST_REVISIONS["gumrrg"] == "eb1d5745f3a18b8894ce72abad3c2a76442d1107"


def test_dmrst_downloads_every_checkpoint_member_from_the_pinned_commit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = tmp_path / "config.json"
    config.write_text("{}", encoding="utf-8")
    relation_table = tmp_path / "relation_table.txt"
    relation_table.write_text("span\n", encoding="utf-8")
    weights = tmp_path / "best_weights.pt"
    weights.write_bytes(b"fixture")
    files = {"config.json": config, "relation_table.txt": relation_table, "best_weights.pt": weights}
    calls: list[tuple[str, str]] = []

    def download(*, repo_id: str, filename: str, revision: str | None) -> str:
        calls.append((filename, str(revision)))
        assert repo_id == "tchewik/isanlp_rst_v3"
        return str(files[filename])

    monkeypatch.setattr(dmrst_module, "hf_hub_download", download)
    monkeypatch.setattr(PredictorDMRST, "_load_model", _without_model_load)
    PredictorDMRST(hf_model_name="tchewik/isanlp_rst_v3", hf_model_version="gumrrg", device="cpu")

    assert calls == [
        ("best_weights.pt", PUBLISHED_RST_REVISIONS["gumrrg"]),
        ("config.json", PUBLISHED_RST_REVISIONS["gumrrg"]),
        ("relation_table.txt", PUBLISHED_RST_REVISIONS["gumrrg"]),
    ]


def test_unirst_downloads_checkpoint_and_inventory_from_the_same_pinned_commit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = tmp_path / "config.json"
    config.write_text(json.dumps({"data": {"corpora": "['GUM']"}}), encoding="utf-8")
    relation_table = tmp_path / "relation_table_gum.txt"
    relation_table.write_text("span\n", encoding="utf-8")
    weights = tmp_path / "best_weights.pt"
    weights.write_bytes(b"fixture")
    files = {"config.json": config, "relation_table_gum.txt": relation_table, "best_weights.pt": weights}
    calls: list[tuple[str, str]] = []

    def download(*, repo_id: str, filename: str, revision: str | None) -> str:
        calls.append((filename, str(revision)))
        assert repo_id == "tchewik/isanlp_rst_v3"
        return str(files[filename])

    monkeypatch.setattr(unirst_module, "hf_hub_download", download)
    monkeypatch.setattr(PredictorUniRST, "_load_model", _without_model_load)
    PredictorUniRST(hf_model_name="tchewik/isanlp_rst_v3", hf_model_version="unirst", device="cpu")

    assert calls == [
        ("best_weights.pt", PUBLISHED_RST_REVISIONS["unirst"]),
        ("config.json", PUBLISHED_RST_REVISIONS["unirst"]),
        ("relation_table_gum.txt", PUBLISHED_RST_REVISIONS["unirst"]),
    ]

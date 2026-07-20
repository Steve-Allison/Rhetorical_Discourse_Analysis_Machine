"""Adversarial / inventory-load tests for UniRST pickle handling.

No HF downloads, no mocks. Exercises real ``_RestrictedUnpickler`` and
``_load_data_manager`` / ``_load_relation_table`` against on-disk files.
"""

from __future__ import annotations

import logging
import pickle
from pathlib import Path

import pytest

from isanlp_rst.universal_parser.data_manager import ParserInput
from isanlp_rst.universal_parser.predictor import (
    PredictorUniRST,
    _RestrictedUnpickler,
)


def _local_shell(model_dir: Path) -> PredictorUniRST:
    """Minimal local-mode instance — no ``__init__`` / no weight load."""
    pred = object.__new__(PredictorUniRST)
    pred.mode = "local"
    pred.model_dir = str(model_dir)
    pred.hf_model_name = None
    pred.hf_model_version = None
    pred.logger = logging.getLogger("test.unirst.pickle")
    PredictorUniRST._ensure_module_aliases()
    return pred


def _write_allowlisted_inventory_pickle(path: Path, labels: list[str]) -> None:
    """Pickle a ``ParserInput`` (isanlp_rst.*) carrying ``relation_table``."""
    obj = ParserInput()
    obj.relation_table = labels  # type: ignore[attr-defined]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as f:
        pickle.dump(obj, f, protocol=pickle.HIGHEST_PROTOCOL)


class _EvilReduce:
    """Classic pickle gadget — must be refused by the allow-list."""

    def __reduce__(self):
        return (eval, ("1+1",))


# --- RestrictedUnpickler ----------------------------------------------------


def test_restricted_unpickler_refuses_eval_gadget(tmp_path: Path) -> None:
    evil = tmp_path / "evil.pkl"
    with evil.open("wb") as f:
        pickle.dump(_EvilReduce(), f)

    with evil.open("rb") as f, pytest.raises(pickle.UnpicklingError, match="Refused"):
        _RestrictedUnpickler(f).load()


def test_restricted_unpickler_loads_isanlp_rst_parser_input(tmp_path: Path) -> None:
    path = tmp_path / "ok.pkl"
    _write_allowlisted_inventory_pickle(path, ["elaboration", "contrast"])
    with path.open("rb") as f:
        loaded = _RestrictedUnpickler(f).load()
    assert isinstance(loaded, ParserInput)
    assert loaded.relation_table == ["elaboration", "contrast"]  # type: ignore[attr-defined]


def test_restricted_unpickler_refuses_isanlp_rst_collect_gadget(tmp_path: Path) -> None:
    """REDUCE → data_manager.collect must not execute (prefix allow-list hole)."""

    class _CollectGadget:
        def __reduce__(self):
            from isanlp_rst.universal_parser import data_manager

            return (data_manager.collect, ())

    evil = tmp_path / "collect.pkl"
    with evil.open("wb") as f:
        pickle.dump(_CollectGadget(), f)

    with evil.open("rb") as f, pytest.raises(pickle.UnpicklingError, match="Refused"):
        _RestrictedUnpickler(f).load()


def test_restricted_unpickler_refuses_data_manager_class(tmp_path: Path) -> None:
    """DataManager is excluded so ATTR from_pickle gadgets cannot be built."""
    from isanlp_rst.universal_parser.data_manager import DataManager

    class _DmGadget:
        def __reduce__(self):
            return (DataManager, ("GUM",))

    evil = tmp_path / "dm.pkl"
    with evil.open("wb") as f:
        pickle.dump(_DmGadget(), f)

    with evil.open("rb") as f, pytest.raises(pickle.UnpicklingError, match="Refused"):
        _RestrictedUnpickler(f).load()


def test_restricted_unpickler_refuses_load_cached_gadget(tmp_path: Path) -> None:
    class _CacheGadget:
        def __reduce__(self):
            from isanlp_rst._rst_common._cache import load_cached

            return (load_cached, (tmp_path, "deadbeef"))

    evil = tmp_path / "cache.pkl"
    with evil.open("wb") as f:
        pickle.dump(_CacheGadget(), f)

    with evil.open("rb") as f, pytest.raises(pickle.UnpicklingError, match="Refused"):
        _RestrictedUnpickler(f).load()


# --- _load_data_manager / _load_relation_table ------------------------------


def test_load_data_manager_skips_refused_pickle_and_returns_none(
    tmp_path: Path,
) -> None:
    """A planted eval-gadget pickle must not load; loader returns None."""
    pickle_path = tmp_path / "data_manager_eng.rst.gum.pickle"
    with pickle_path.open("wb") as f:
        pickle.dump(_EvilReduce(), f)

    pred = _local_shell(tmp_path)
    assert pred._load_data_manager("eng.rst.gum") is None


def test_load_data_manager_reads_allowlisted_pickle_only_inventory(
    tmp_path: Path,
) -> None:
    """Pickle-only packaging (no relation_table_*.txt) still yields labels."""
    _write_allowlisted_inventory_pickle(
        tmp_path / "data_manager_eng.rst.gum.pickle",
        ["joint", "attribution"],
    )
    pred = _local_shell(tmp_path)
    dm = pred._load_data_manager("eng.rst.gum")
    assert dm is not None
    assert list(dm.relation_table) == ["joint", "attribution"]


def test_relation_table_txt_preferred_over_pickle_with_different_labels(
    tmp_path: Path,
) -> None:
    """When both exist, plain text wins — pickle must not override labels."""
    (tmp_path / "relation_table_eng.rst.gum.txt").write_text(
        "from_txt_a\nfrom_txt_b\n", encoding="utf-8"
    )
    _write_allowlisted_inventory_pickle(
        tmp_path / "data_manager_eng.rst.gum.pickle",
        ["from_pickle_SHOULD_NOT_WIN"],
    )
    pred = _local_shell(tmp_path)
    table = pred._load_relation_table("eng.rst.gum")
    assert table == ["from_txt_a", "from_txt_b"]
    # Capability preserved: pickle still loadable if text absent.
    (tmp_path / "relation_table_eng.rst.gum.txt").unlink()
    dm = pred._load_data_manager("eng.rst.gum")
    assert dm is not None
    assert list(dm.relation_table) == ["from_pickle_SHOULD_NOT_WIN"]


@pytest.mark.parametrize(
    "corpus,filename",
    [
        ("rst-dt-tr", "relation_table_rst-dt.txt"),
        ("gum10-tr", "relation_table_gum.txt"),
        ("gum10_tr", "relation_table_gum.txt"),
        ("eng.rst.gum", "relation_table_eng_rst_gum.txt"),
    ],
)
def test_relation_table_txt_uses_corpus_variants(
    tmp_path: Path, corpus: str, filename: str
) -> None:
    """Txt resolution must share ``_corpus_variants`` with pickle lookup."""
    (tmp_path / filename).write_text("joint\nelaboration\n", encoding="utf-8")
    pred = _local_shell(tmp_path)
    assert pred._load_relation_table(corpus) == ["joint", "elaboration"]

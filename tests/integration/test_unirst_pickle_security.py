"""Adversarial / inventory-load tests for UniRST pickle handling.

No HF downloads, no mocks. Exercises real ``RestrictedUnpickler`` and
inventory loaders against on-disk files. A successful pickle import yields
``list[str]`` labels only — never a live ``ParserInput`` / ``DataManager``.
"""

import logging
import pickle
from pathlib import Path

import pytest

from rdam.rst.model_loading.parser_input import ParserInput
from workbench.archive.legacy_2021.universal_parser.inventory import (
    RestrictedUnpickler,
    dump_relation_inventory,
    import_relation_table_from_legacy_pickle,
)
from workbench.archive.legacy_2021.universal_parser.predictor import PredictorUniRST


def _local_shell(model_dir: Path) -> PredictorUniRST:
    """Minimal local-mode instance — no ``__init__`` / no weight load."""
    pred = object.__new__(PredictorUniRST)
    pred.mode = "local"
    pred.model_dir = model_dir
    pred.hf_model_name = None
    pred.hf_model_version = None
    pred.logger = logging.getLogger("test.unirst.pickle")
    PredictorUniRST._ensure_module_aliases()
    return pred


def _write_allowlisted_inventory_pickle(path: Path, labels: list[str]) -> None:
    """Pickle a ``ParserInput`` (rdam.rst.*) carrying ``relation_table``."""
    obj = ParserInput()
    obj.relation_table = labels
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        pickle.dump(obj, handle, protocol=pickle.HIGHEST_PROTOCOL)


class _EvilReduce:
    """Classic pickle gadget — must be refused by the allow-list."""

    def __reduce__(self):
        return (eval, ("1+1",))


def test_restricted_unpickler_refuses_eval_gadget(tmp_path: Path) -> None:
    evil = tmp_path / "evil.pkl"
    with evil.open("wb") as handle:
        pickle.dump(_EvilReduce(), handle)

    with evil.open("rb") as handle, pytest.raises(pickle.UnpicklingError, match="Refused"):
        RestrictedUnpickler(handle).load()


def test_restricted_unpickler_loads_isanlp_rst_parser_input(tmp_path: Path) -> None:
    path = tmp_path / "ok.pkl"
    _write_allowlisted_inventory_pickle(path, ["elaboration", "contrast"])
    with path.open("rb") as handle:
        loaded = RestrictedUnpickler(handle).load()
    assert isinstance(loaded, ParserInput)
    assert loaded.relation_table == ["elaboration", "contrast"]


def test_restricted_unpickler_refuses_isanlp_rst_collect_gadget(tmp_path: Path) -> None:
    """REDUCE → data_manager.collect must not execute (prefix allow-list hole)."""

    class _CollectGadget:
        def __reduce__(self):
            from workbench.corpus.unirst import data_manager

            return (data_manager.collect, ())

    evil = tmp_path / "collect.pkl"
    with evil.open("wb") as handle:
        pickle.dump(_CollectGadget(), handle)

    with evil.open("rb") as handle, pytest.raises(pickle.UnpicklingError, match="Refused"):
        RestrictedUnpickler(handle).load()


def test_restricted_unpickler_refuses_data_manager_class(tmp_path: Path) -> None:
    """DataManager is excluded so ATTR from_pickle gadgets cannot be built."""
    from workbench.corpus.unirst.data_manager import DataManager

    class _DmGadget:
        def __reduce__(self):
            return (DataManager, ("GUM",))

    evil = tmp_path / "dm.pkl"
    with evil.open("wb") as handle:
        pickle.dump(_DmGadget(), handle)

    with evil.open("rb") as handle, pytest.raises(pickle.UnpicklingError, match="Refused"):
        RestrictedUnpickler(handle).load()


def test_legacy_pickle_import_skips_refused_pickle_and_returns_none(tmp_path: Path) -> None:
    """A planted eval-gadget pickle must not load; loader returns None."""
    pickle_path = tmp_path / "data_manager_eng.rst.gum.pickle"
    with pickle_path.open("wb") as handle:
        pickle.dump(_EvilReduce(), handle)

    pred = _local_shell(tmp_path)
    assert pred._load_legacy_pickle_inventory("eng.rst.gum") is None


def test_legacy_pickle_import_returns_labels_only(tmp_path: Path) -> None:
    """Pickle-only packaging (no relation_table_*.txt) still yields labels."""
    _write_allowlisted_inventory_pickle(
        tmp_path / "data_manager_eng.rst.gum.pickle",
        ["joint", "attribution"],
    )
    pred = _local_shell(tmp_path)
    labels = pred._load_legacy_pickle_inventory("eng.rst.gum")
    assert labels == ["joint", "attribution"]
    assert import_relation_table_from_legacy_pickle(tmp_path / "data_manager_eng.rst.gum.pickle") == [
        "joint",
        "attribution",
    ]


def test_relation_table_txt_preferred_over_pickle_with_different_labels(
    tmp_path: Path,
) -> None:
    """When both exist, plain text wins — pickle must not override labels."""
    (tmp_path / "relation_table_eng.rst.gum.txt").write_text("from_txt_a\nfrom_txt_b\n", encoding="utf-8")
    _write_allowlisted_inventory_pickle(
        tmp_path / "data_manager_eng.rst.gum.pickle",
        ["from_pickle_SHOULD_NOT_WIN"],
    )
    pred = _local_shell(tmp_path)
    table = pred._load_relation_table("eng.rst.gum")
    assert table == ["from_txt_a", "from_txt_b"]
    assert pred._load_inventory("eng.rst.gum") == ["from_txt_a", "from_txt_b"]
    (tmp_path / "relation_table_eng.rst.gum.txt").unlink()
    assert pred._load_inventory("eng.rst.gum") == ["from_pickle_SHOULD_NOT_WIN"]


def test_json_inventory_preferred_over_pickle(tmp_path: Path) -> None:
    dump_relation_inventory(
        tmp_path / "data_manager_eng.rst.gum.json",
        ["from_json_a", "from_json_b"],
        corpus_name="eng.rst.gum",
    )
    _write_allowlisted_inventory_pickle(
        tmp_path / "data_manager_eng.rst.gum.pickle",
        ["from_pickle_SHOULD_NOT_WIN"],
    )
    pred = _local_shell(tmp_path)
    assert pred._load_inventory("eng.rst.gum") == ["from_json_a", "from_json_b"]


def test_txt_preferred_over_json(tmp_path: Path) -> None:
    (tmp_path / "relation_table_eng.rst.gum.txt").write_text("from_txt\n", encoding="utf-8")
    dump_relation_inventory(
        tmp_path / "data_manager_eng.rst.gum.json",
        ["from_json"],
        corpus_name="eng.rst.gum",
    )
    pred = _local_shell(tmp_path)
    assert pred._load_inventory("eng.rst.gum") == ["from_txt"]


@pytest.mark.parametrize(
    "corpus,filename",
    [
        ("rst-dt-tr", "relation_table_rst-dt.txt"),
        ("gum10-tr", "relation_table_gum.txt"),
        ("gum10_tr", "relation_table_gum.txt"),
        ("eng.rst.gum", "relation_table_eng_rst_gum.txt"),
    ],
)
def test_relation_table_txt_uses_corpus_variants(tmp_path: Path, corpus: str, filename: str) -> None:
    """Txt resolution must share ``_corpus_variants`` with pickle lookup."""
    (tmp_path / filename).write_text("joint\nelaboration\n", encoding="utf-8")
    pred = _local_shell(tmp_path)
    assert pred._load_relation_table(corpus) == ["joint", "elaboration"]

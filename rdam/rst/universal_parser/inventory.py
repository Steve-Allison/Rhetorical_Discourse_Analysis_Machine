"""Relation-inventory I/O for UniRST.

Native format is JSON (or a plain ``relation_table_*.txt``). Elena-era
``data_manager_*.pickle`` files from HuggingFace are a **one-way import**:
we extract ``relation_table`` and discard the object. We never pickle.dump.
"""

import ast
import builtins
import collections
import json
import pickle
import pathlib
import sys
import types
from importlib import import_module
from pathlib import Path
from typing import cast

from rdam.rst.model_loading.parser_input import ParserInput

INVENTORY_FORMAT = "isanlp_rst_relation_inventory"
INVENTORY_VERSION = 1


class RestrictedUnpickler(pickle.Unpickler):
    """Unpickler that only reconstructs inventory leaf types + containers.

    Deliberately does **not** allow arbitrary ``rdam.rst.*`` callables:
    REDUCE gadgets targeting ``data_manager.collect``,
    ``DataManager.from_pickle``, or ``load_cached`` must be refused.
    ``DataManager`` itself is excluded so ATTR-based ``from_pickle`` gadgets
    cannot be assembled after loading the class.
    """

    _ALLOWED_BUILTINS = frozenset(
        {
            "list",
            "dict",
            "tuple",
            "set",
            "frozenset",
            "str",
            "int",
            "float",
            "bool",
            "bytes",
            "complex",
            "NoneType",
            "slice",
            "object",
        }
    )
    _ALLOWED_COLLECTIONS = frozenset({"defaultdict", "OrderedDict"})
    _ALLOWED_PATHLIB = frozenset({"Path", "PosixPath", "WindowsPath"})
    _ALLOWED_CLASSES = frozenset(
        {
            ("rdam.rst.model_loading.parser_input", "ParserInput"),
            ("isanlp_rst.model_loading.parser_input", "ParserInput"),
            ("isanlp_rst.universal_parser.data_manager", "ParserInput"),
            ("src.universal_parser.data_manager", "ParserInput"),
            ("isanlp_rst.dmrst_parser.data_manager", "ParserInput"),
            ("src.dmrst_parser.data_manager", "ParserInput"),
        }
    )

    def find_class(self, module: str, name: str) -> object:
        if module == "builtins" and name in self._ALLOWED_BUILTINS:
            if name == "NoneType":
                return type(None)
            return getattr(builtins, name)
        if module == "collections" and name in self._ALLOWED_COLLECTIONS:
            return getattr(collections, name)
        if module in ("pathlib", "pathlib._local") and name in self._ALLOWED_PATHLIB:
            return getattr(pathlib, name)

        if (module, name) in self._ALLOWED_CLASSES:
            return ParserInput

        raise pickle.UnpicklingError(f"Refused to unpickle {module}.{name} (not on allow-list).")


def relation_table_from_txt(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def relation_table_from_json_obj(payload: object) -> list[str]:
    if isinstance(payload, list):
        items = cast(list[object], payload)
        if all(isinstance(item, str) for item in items):
            return cast(list[str], items)
    if not isinstance(payload, dict):
        raise ValueError("relation inventory JSON must be an object or a string list")
    inventory = cast(dict[object, object], payload)
    table = inventory.get("relation_table")
    if not isinstance(table, list):
        raise ValueError("relation inventory JSON missing string list 'relation_table'")
    labels = cast(list[object], table)
    if not all(isinstance(item, str) for item in labels):
        raise ValueError("relation inventory JSON missing string list 'relation_table'")
    return [item.strip() for item in cast(list[str], labels) if item.strip()]


def dump_relation_inventory(path: Path, labels: list[str], *, corpus_name: str = "") -> None:
    payload = {
        "format": INVENTORY_FORMAT,
        "version": INVENTORY_VERSION,
        "corpus_name": corpus_name,
        "relation_table": labels,
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def load_relation_inventory_json(path: Path) -> list[str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return relation_table_from_json_obj(payload)


def import_relation_table_from_legacy_pickle(path: Path) -> list[str]:
    """One-way import: published HF pickles → ``relation_table`` labels only."""
    ensure_unirst_module_aliases()
    with path.open("rb") as handle:
        obj = RestrictedUnpickler(handle).load()
    table = getattr(obj, "relation_table", None)
    if table is None:
        raise pickle.UnpicklingError(f"{path} has no relation_table")
    return [str(item) for item in table]


def ensure_unirst_module_aliases() -> None:
    """Register Elena-era module paths so legacy pickles can unpickle ParserInput."""
    aliases = {
        "src.universal_parser.du_converter": "rdam.rst.utils.du_converter",
        "src.universal_parser.src.parser.data": "rdam.rst.universal_parser.src.parser.data",
        "src.universal_parser.src.parser.modules": "rdam.rst.universal_parser.src.parser.modules",
        "src.universal_parser.src.parser.segmenters": "rdam.rst.universal_parser.src.parser.segmenters",
        "src.universal_parser.src.parser.parsing_net": "rdam.rst.universal_parser.src.parser.parsing_net",
        "src.universal_parser.src.parser.parsing_net_bottom_up": "rdam.rst.universal_parser.src.parser.parsing_net_bottom_up",
        "src.universal_parser.src.parser.metrics": "rdam.rst.universal_parser.src.parser.metrics",
    }
    for alias, target in aliases.items():
        if alias in sys.modules:
            continue
        module = import_module(target)
        sys.modules[alias] = module
        parent_name, _, child_name = alias.rpartition(".")
        if parent_name:
            parent = _ensure_parent_module(parent_name)
            setattr(parent, child_name, module)


def _ensure_parent_module(name: str) -> types.ModuleType:
    if name in sys.modules:
        return sys.modules[name]
    module = types.ModuleType(name)
    sys.modules[name] = module
    parent_name, _, child_name = name.rpartition(".")
    if parent_name:
        parent = _ensure_parent_module(parent_name)
        setattr(parent, child_name, module)
    return module


def parse_corpora_config(corpora: object) -> list[str]:
    """``config['data']['corpora']`` is sometimes a Python-literal string."""
    if isinstance(corpora, str):
        parsed = ast.literal_eval(corpora)
        if not isinstance(parsed, list):
            raise ValueError("config data.corpora string must be a list literal")
        return [str(item) for item in cast(list[object], parsed)]
    if isinstance(corpora, list):
        return [str(item) for item in cast(list[object], corpora)]
    raise ValueError("config data.corpora must be a list or list-literal string")

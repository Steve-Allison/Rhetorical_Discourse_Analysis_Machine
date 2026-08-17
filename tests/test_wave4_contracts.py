"""Wave 4 — construct-path kwargs + formats-extra isolation."""

import json
import subprocess
import sys
import textwrap
from dataclasses import dataclass
from pathlib import Path

import pytest

from isanlp_rst.doclang import parse_doclang
from isanlp_rst.docling import parse_docling
from isanlp_rst.markdown import parse_markdown

FIXTURES = Path(__file__).resolve().parent / "fixtures"
DOCLANG = FIXTURES / "doclang" / "ok_comprehensive.dclg.xml"
MARKDOWN = FIXTURES / "markdown" / "minimal.md"


@dataclass
class _Node:
    start: int
    end: int
    left: _Node | None = None
    right: _Node | None = None
    relation: str = ""
    nuclearity: str = ""


class _CapturingParser:
    """Stand-in for ``Parser`` that records constructor kwargs."""

    last_kwargs: dict | None = None

    def __init__(self, **kwargs) -> None:
        type(self).last_kwargs = dict(kwargs)
        self.hf_model_name = kwargs.get("hf_model_name")
        self.hf_model_version = kwargs.get("hf_model_version")
        self.relinventory = kwargs.get("relinventory")

    def __call__(self, text: str) -> dict:
        return {"rst": [_Node(0, len(text))]}


def _write_one_para_docling(path: Path) -> Path:
    payload = {
        "schema_name": "DoclingDocument",
        "version": "1.10.0",
        "name": "one",
        "origin": {
            "mimetype": "text/plain",
            "binary_hash": 1,
            "filename": "one.txt",
        },
        "furniture": {
            "self_ref": "#/furniture",
            "children": [],
            "content_layer": "furniture",
            "name": "_root_",
            "label": "unspecified",
        },
        "body": {
            "self_ref": "#/body",
            "children": [{"$ref": "#/texts/0"}],
            "content_layer": "body",
            "name": "_root_",
            "label": "unspecified",
        },
        "texts": [
            {
                "self_ref": "#/texts/0",
                "parent": {"$ref": "#/body"},
                "children": [],
                "content_layer": "body",
                "label": "text",
                "prov": [],
                "orig": "Hello world.",
                "text": "Hello world.",
            }
        ],
        "tables": [],
        "pictures": [],
        "groups": [],
        "key_value_items": [],
        "form_items": [],
        "pages": {},
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


@pytest.mark.parametrize(
    "fmt",
    ["markdown", "doclang", "docling"],
)
def test_construct_path_forwards_device_dtype_hf(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, fmt: str
) -> None:
    """When ``parser is None``, entry points must forward device/dtype/hf kwargs."""
    _CapturingParser.last_kwargs = None
    monkeypatch.setattr("isanlp_rst.parser.Parser", _CapturingParser)

    if fmt == "markdown":
        parse_markdown(
            MARKDOWN,
            device="cpu",
            dtype="float32",
            hf_model_name="repo/x",
            hf_model_version="gumrrg",
        )
    elif fmt == "doclang":
        parse_doclang(
            DOCLANG,
            validate_xml=False,
            device="cpu",
            dtype="float32",
            hf_model_name="repo/x",
            hf_model_version="gumrrg",
        )
    else:
        path = _write_one_para_docling(tmp_path / "one.docling.json")
        parse_docling(
            path,
            device="cpu",
            dtype="float32",
            hf_model_name="repo/x",
            hf_model_version="gumrrg",
        )

    assert _CapturingParser.last_kwargs is not None
    kwargs = _CapturingParser.last_kwargs
    assert kwargs.get("device") == "cpu"
    assert kwargs.get("dtype") == "float32"
    assert kwargs.get("hf_model_name") == "repo/x"
    assert kwargs.get("hf_model_version") == "gumrrg"


def test_parser_imports_without_docling_core() -> None:
    """Core ``isanlp_rst.parser`` must not require the formats extra."""
    script = textwrap.dedent(
        """\
        import sys

        class _BlockDocling:
            def find_spec(self, fullname, path, target=None):
                if fullname == "docling_core" or fullname.startswith("docling_core."):
                    raise ModuleNotFoundError(fullname)
                return None

        sys.meta_path.insert(0, _BlockDocling())
        import isanlp_rst.parser as p
        assert p.Parser is not None
        print("OK")
        """
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "OK" in result.stdout

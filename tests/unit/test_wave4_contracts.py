"""The core parser remains isolated from optional source-format dependencies."""

import subprocess
import sys
import textwrap


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

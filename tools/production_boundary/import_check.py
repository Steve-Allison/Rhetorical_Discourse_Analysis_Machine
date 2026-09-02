"""Import-check the ``isanlp_rst`` distribution installed in the current environment.

Imports the public modules, exercises the façade's deterministic no-model failure, and
checks that no ``workbench`` member or import leaked into the installed distribution.
It never loads model weights and never touches a built wheel: in the pixi ``production``
environment the installed distribution is the *editable source*
(``[tool.pixi.feature.production.pypi-dependencies]`` in ``pyproject.toml``), so a green
result says nothing about ``dist/``. Wheel certification is ``production-clean-install``.
"""

import argparse
from importlib import import_module
from importlib.metadata import PackageNotFoundError, distribution
import json
from pathlib import Path
import sys


_PUBLIC_MODULES = (
    "isanlp_rst",
    "isanlp_rst.parser",
    "isanlp_rst.contracts",
    "isanlp_rst.erst",
    "isanlp_rst.model_loading.parser_input",
)
_FORMAT_MODULES = (
    "isanlp_rst.ingest",
    "isanlp_rst.doclang",
    "isanlp_rst.markdown",
)
_FORBIDDEN_PREFIXES = ("workbench", "workbench.research")


def _distribution_members() -> tuple[str, ...]:
    try:
        package = distribution("isanlp_rst")
    except PackageNotFoundError as exc:
        raise RuntimeError("isanlp_rst is not installed as a distribution") from exc
    return tuple(sorted(str(path) for path in package.files or ()))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--formats", action="store_true", help="also import canonical ingest and its private format helpers")
    parser.add_argument("--outside", type=Path, help="fail if isanlp_rst resolves beneath this source directory")
    args = parser.parse_args()

    for module_name in _PUBLIC_MODULES + (_FORMAT_MODULES if args.formats else ()):
        import_module(module_name)

    from isanlp_rst import Parser

    try:
        Parser()
    except ValueError as exc:
        if "hf_model_version" not in str(exc) and "model_dir" not in str(exc):
            raise AssertionError(f"unexpected Parser() failure: {exc}") from exc
    else:
        raise AssertionError("Parser() without a model identity must fail deterministically")

    package_file = Path(sys.modules["isanlp_rst"].__file__ or "").resolve()
    if args.outside is not None and package_file.is_relative_to(args.outside.resolve()):
        raise AssertionError(f"isanlp_rst leaked from source tree: {package_file}")

    members = _distribution_members()
    forbidden_members = tuple(
        member for member in members if member.split("/", 1)[0] in _FORBIDDEN_PREFIXES
    )
    forbidden_imports = tuple(
        module for module in sys.modules if module.split(".", 1)[0] in _FORBIDDEN_PREFIXES
    )
    if forbidden_members or forbidden_imports:
        raise AssertionError(
            f"offline boundary leak: members={forbidden_members}, imports={forbidden_imports}"
        )

    print(
        json.dumps(
            {
                "distribution_members": len(members),
                "canonical_ingest": args.formats,
                "editable_source": package_file.is_relative_to(Path.cwd().resolve()),
                "package_file": str(package_file),
                "valid": True,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

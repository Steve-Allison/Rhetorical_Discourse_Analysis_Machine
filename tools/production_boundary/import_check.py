"""Import-check the ``rdam`` distribution installed in the current environment.

Imports the public modules of every technique package and checks that no ``workbench``
member or import leaked into the installed distribution. It never constructs a provider,
loads model weights, or touches a built wheel: in the pixi ``production`` environment the
installed distribution is the
*editable source* (``[tool.pixi.feature.production.pypi-dependencies]`` in
``pyproject.toml``), so a green result says nothing about ``dist/``. Wheel certification
is ``production-clean-install``.
"""

import argparse
from importlib import import_module
from importlib.metadata import PackageNotFoundError, distribution
import json
from pathlib import Path
import sys

_PUBLIC_MODULES = (
    "rdam",
    "rdam.rst",
    "rdam.rst.parser",
    "rdam.rst.contracts",
    "rdam.rst.erst",
    "rdam.rst.model_loading.parser_input",
    "rdam.sdrt",
    "rdam.pdtb",
    "rdam.toulmin",
    "rdam.walton",
    "rdam.dung",
    "rdam.ibis",
    "rdam.machine",
    "rdam.composition",
    "rdam.ingest",
)
_FORMAT_MODULES = (
    "rdam.rst.doclang",
    "rdam.rst.markdown",
)
_FORBIDDEN_PREFIXES = ("workbench", "workbench.research")
_PACKAGE_NAME = "rdam"


def _distribution_members() -> tuple[str, ...]:
    try:
        package = distribution(_PACKAGE_NAME)
    except PackageNotFoundError as exc:
        raise RuntimeError(f"{_PACKAGE_NAME} is not installed as a distribution") from exc
    return tuple(sorted(str(path) for path in package.files or ()))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--formats", action="store_true", help="also import private format helpers")
    parser.add_argument("--outside", type=Path, help="fail if rdam resolves beneath this source directory")
    args = parser.parse_args()

    baseline_modules = frozenset(sys.modules)
    for module_name in _PUBLIC_MODULES + (_FORMAT_MODULES if args.formats else ()):
        import_module(module_name)

    package_file = Path(sys.modules["rdam"].__file__ or "").resolve()
    if args.outside is not None and package_file.is_relative_to(args.outside.resolve()):
        raise AssertionError(f"rdam leaked from source tree: {package_file}")

    members = _distribution_members()
    forbidden_members = tuple(
        member for member in members if member.split("/", 1)[0] in _FORBIDDEN_PREFIXES
    )
    forbidden_imports = tuple(
        module
        for module in sys.modules
        if module not in baseline_modules and module.split(".", 1)[0] in _FORBIDDEN_PREFIXES
    )
    if forbidden_members or forbidden_imports:
        raise AssertionError(
            f"offline boundary leak: members={forbidden_members}, imports={forbidden_imports}"
        )

    print(
        json.dumps(
            {
                "distribution_members": len(members),
                "canonical_ingest": "rdam.ingest" in sys.modules,
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

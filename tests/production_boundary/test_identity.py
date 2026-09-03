"""The release identity is derived once and rejects contradictory project metadata."""

from pathlib import Path

import pytest

from tools.production_boundary.identity import read_release_identity


def _write_project(
    root: Path,
    *,
    name: str = "rdam",
    version: str = "6.0.0",
    import_names: tuple[str, ...] = ("rdam",),
    packages: tuple[str, ...] = ("rdam",),
) -> None:
    imports = ", ".join(f'"{value}"' for value in import_names)
    wheel_packages = ", ".join(f'"{value}"' for value in packages)
    (root / "pyproject.toml").write_text(
        f'''[project]
name = "{name}"
version = "{version}"
import-names = [{imports}]

[tool.hatch.build.targets.wheel]
packages = [{wheel_packages}]
''',
        encoding="utf-8",
    )


def test_repository_release_identity_is_exactly_the_declared_rdam_root() -> None:
    identity = read_release_identity(Path.cwd())
    assert identity.distribution == "rdam"
    assert identity.version == "6.0.0"
    assert identity.package_dir == "rdam"
    assert identity.import_package == "rdam"


@pytest.mark.parametrize("version", ("not a version", "", "6..0"))
def test_invalid_project_version_is_rejected(tmp_path: Path, version: str) -> None:
    _write_project(tmp_path, version=version)
    with pytest.raises(RuntimeError, match="valid PEP 440"):
        read_release_identity(tmp_path)


@pytest.mark.parametrize("package_dir", ("../rdam", "/rdam", "rdam/../other", "."))
def test_unsafe_or_empty_wheel_package_path_is_rejected(
    tmp_path: Path,
    package_dir: str,
) -> None:
    _write_project(tmp_path, packages=(package_dir,))
    with pytest.raises(RuntimeError, match="safe relative path"):
        read_release_identity(tmp_path)


@pytest.mark.parametrize(
    "import_names",
    ((), ("other",), ("rdam", "other")),
)
def test_project_import_identity_must_exactly_match_the_wheel_package(
    tmp_path: Path,
    import_names: tuple[str, ...],
) -> None:
    _write_project(tmp_path, import_names=import_names)
    with pytest.raises(RuntimeError, match="exactly match"):
        read_release_identity(tmp_path)


def test_safe_src_layout_derives_the_import_package_from_the_final_component(
    tmp_path: Path,
) -> None:
    _write_project(tmp_path, packages=("src/rdam",))
    identity = read_release_identity(tmp_path)
    assert identity.package_dir == "src/rdam"
    assert identity.import_package == "rdam"

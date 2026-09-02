"""The release identity every production tool derives from ``pyproject.toml``.

Distribution name, version, and the wheel's package directory are declared once, in
``[project]`` and ``[tool.hatch.build.targets.wheel]``. Tools read them from here; none
restates a name or a version literal that could drift from the declaration.
"""

from dataclasses import dataclass
from pathlib import Path
import re
import tomllib

_FILENAME_NORMALIZER = re.compile(r"[-_.]+")


@dataclass(frozen=True, slots=True)
class ReleaseIdentity:
    distribution: str
    version: str
    package_dir: str

    @property
    def import_package(self) -> str:
        """The import name Hatchling ships: the final component of the package directory."""

        return Path(self.package_dir).name

    @property
    def filename_stem(self) -> str:
        """Distribution name as it appears in built filenames (PEP 427 / PEP 625 normalisation)."""

        return _FILENAME_NORMALIZER.sub("_", self.distribution).lower()

    @property
    def wheel_name(self) -> str:
        return f"{self.filename_stem}-{self.version}-py3-none-any.whl"

    @property
    def sdist_name(self) -> str:
        return f"{self.filename_stem}-{self.version}.tar.gz"

    @property
    def tag(self) -> str:
        return f"v{self.version}"

    def release_dir(self, root: Path) -> Path:
        return root / "dist" / self.version


def read_release_identity(root: Path) -> ReleaseIdentity:
    """Read the declared identity from the repository's ``pyproject.toml``."""

    pyproject = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    project = pyproject.get("project", {})
    name = project.get("name")
    version = project.get("version")
    packages = pyproject.get("tool", {}).get("hatch", {}).get("build", {}).get("targets", {}).get("wheel", {}).get("packages")
    if not isinstance(name, str) or not isinstance(version, str):
        raise RuntimeError("pyproject must declare a static project name and version")
    if not isinstance(packages, list) or len(packages) != 1 or not isinstance(packages[0], str):
        raise RuntimeError("pyproject must declare exactly one wheel package directory")
    return ReleaseIdentity(distribution=name, version=version, package_dir=packages[0])


__all__ = ["ReleaseIdentity", "read_release_identity"]

"""Single ownership authority for repository paths and dependencies."""

from collections.abc import Iterable
import os
from pathlib import Path, PurePosixPath

from tools.production_boundary.contracts import BoundaryViolation, DependencyRule, OwnershipClass, OwnershipRule, ViolationKind


_GENERATED_PARTS = frozenset({".git", ".pixi", ".pytest_cache", ".ruff_cache", ".mypy_cache", "__pycache__", "build", "dist", "graphify-out"})


class OwnershipClassificationError(ValueError):
    """A relevant path has zero or multiple ownership rules."""


class OwnershipAuthority:
    """Classify every relevant member without a second production allowlist."""

    def __init__(self, root: Path, *, rules: tuple[OwnershipRule, ...] | None = None) -> None:
        self.root = root.resolve()
        default_rules = (
            OwnershipRule(rule_id="production", prefix=PurePosixPath("isanlp_rst"), ownership=OwnershipClass.PRODUCTION, reason="installable RST analysis product", publishable=True),
            OwnershipRule(rule_id="offline", prefix=PurePosixPath("workbench"), ownership=OwnershipClass.OFFLINE, reason="corpus, training, evaluation, and promotion workbench"),
            OwnershipRule(rule_id="research", prefix=PurePosixPath("workbench.research"), ownership=OwnershipClass.OFFLINE, reason="offline research implementation"),
            OwnershipRule(rule_id="corpora", prefix=PurePosixPath("corpora"), ownership=OwnershipClass.OFFLINE, reason="training/evaluation corpora"),
            OwnershipRule(rule_id="experiments", prefix=PurePosixPath("experiments"), ownership=OwnershipClass.OFFLINE, reason="experiment outputs and configuration"),
            *(OwnershipRule(rule_id=f"repository-{name.lstrip('.').replace('_', '-')}", prefix=PurePosixPath(name), ownership=OwnershipClass.REPOSITORY, reason="repository control, documentation, tests, or tooling") for name in (".agents", ".claude", ".cursor", ".github", ".specify", "config", "docs", "examples", "scripts", "specs", "tests", "tools")),
        )
        self.rules = rules or default_rules
        self.production_dependencies = frozenset({
            "python", "playwright", "razdel", "lxml", "numpy", "transformers", "torch", "huggingface-hub", "tqdm", "pillow", "networkx", "packaging", "pydantic", "python-dotenv", "rfc8785", "safetensors", "doclang", "isanlp", "docling-core", "markdown-it-py", "mdit-py-plugins",
        })
        self.offline_dependencies = frozenset({"fire", "jsonnet", "nltk", "peft", "pytest", "pytest-cov", "ruff", "pyright", "tiktoken", "types-lxml", "build"})

    def relative(self, path: Path) -> PurePosixPath:
        return PurePosixPath(path.resolve().relative_to(self.root).as_posix())

    def matching_rules(self, path: Path | PurePosixPath | str) -> tuple[OwnershipRule, ...]:
        relative = path if isinstance(path, PurePosixPath) else PurePosixPath(path.as_posix() if isinstance(path, Path) else path)
        if relative.is_absolute():
            relative = PurePosixPath(Path(str(relative)).resolve().relative_to(self.root).as_posix())
        return tuple(rule for rule in self.rules if relative == rule.prefix or relative.is_relative_to(rule.prefix))

    def classify(self, path: Path | PurePosixPath | str) -> OwnershipClass:
        relative = path if isinstance(path, PurePosixPath) else PurePosixPath(path.as_posix() if isinstance(path, Path) else path)
        if relative.is_absolute():
            relative = PurePosixPath(Path(str(relative)).resolve().relative_to(self.root).as_posix())
        if any(part in _GENERATED_PARTS or part.endswith(".egg-info") for part in relative.parts) or relative.name == "pixi.lock":
            return OwnershipClass.GENERATED
        if len(relative.parts) == 1:
            return OwnershipClass.REPOSITORY
        matches = self.matching_rules(relative)
        if len(matches) != 1:
            rule_ids = tuple(rule.rule_id for rule in matches)
            raise OwnershipClassificationError(f"path {relative} matched {len(matches)} ownership rules: {rule_ids}")
        return matches[0].ownership

    def iter_relevant_files(self) -> Iterable[Path]:
        for directory, names, filenames in os.walk(self.root, topdown=True):
            names[:] = [name for name in names if name not in _GENERATED_PARTS and not name.endswith(".egg-info")]
            base = Path(directory)
            for filename in filenames:
                path = base / filename
                relative = self.relative(path)
                if not any(part in _GENERATED_PARTS for part in relative.parts):
                    yield path

    def dependency_owner(self, distribution: str) -> OwnershipClass:
        normalized = distribution.casefold().replace("_", "-")
        if normalized in self.production_dependencies:
            return OwnershipClass.PRODUCTION
        if normalized in self.offline_dependencies:
            return OwnershipClass.OFFLINE
        return OwnershipClass.REPOSITORY

    def dependency_rules(self) -> tuple[DependencyRule, ...]:
        production = tuple(DependencyRule(distribution=name, ownership=OwnershipClass.PRODUCTION, reason="declared production runtime capability") for name in sorted(self.production_dependencies))
        offline = tuple(DependencyRule(distribution=name, ownership=OwnershipClass.OFFLINE, reason="offline or repository-only tooling") for name in sorted(self.offline_dependencies))
        return production + offline


def validate_ownership(authority: OwnershipAuthority) -> tuple[BoundaryViolation, ...]:
    """Return causal failures for every relevant path without exactly one rule."""

    violations: list[BoundaryViolation] = []
    for path in authority.iter_relevant_files():
        relative = authority.relative(path)
        matches = authority.matching_rules(relative)
        if len(relative.parts) == 1 or len(matches) == 1:
            continue
        kind = ViolationKind.UNMATCHED_OWNERSHIP if not matches else ViolationKind.AMBIGUOUS_OWNERSHIP
        violations.append(
            BoundaryViolation(
                kind=kind,
                root="ownership",
                path=(relative.as_posix(),),
                detail=f"matched rules: {[rule.rule_id for rule in matches]}",
            )
        )
    return tuple(violations)

"""Loader for immutable Central_Configs ontology lockfile."""

from collections.abc import Mapping
from dataclasses import dataclass
from functools import cache
import hashlib
from importlib import resources
from pathlib import Path
from types import MappingProxyType
from typing import Any

import yaml

# The lock is a package resource, shipped in the wheel beside this module. It was once
# resolved through a repository path (config/ontology/), which no installed copy of the
# package ever had; the feature-010 relocation surfaced that and moved it here.
LOCK_FILE_PATH = Path(str(resources.files("rdam.rst.ontology").joinpath("central.lock.yaml")))


@dataclass(frozen=True, slots=True)
class ModelClassMapping:
    """Mapping definition for a single model class index."""

    label: str
    nuclearity: str
    concept: str


@dataclass(frozen=True, slots=True)
class OntologyLockData:
    """Loaded and validated ontology data."""

    release_version: str
    release_status: str
    sha256_digest: str
    coarse_concepts: tuple[str, ...]
    rst_dt_fine_to_coarse: Mapping[str, str]
    gum_fine_to_coarse: Mapping[str, str]
    dmrst_gum_model_27: Mapping[int, ModelClassMapping]
    dmrst_rstdt_model_42: Mapping[int, ModelClassMapping]

    def __post_init__(self) -> None:
        object.__setattr__(self, "rst_dt_fine_to_coarse", MappingProxyType(dict(self.rst_dt_fine_to_coarse)))
        object.__setattr__(self, "gum_fine_to_coarse", MappingProxyType(dict(self.gum_fine_to_coarse)))
        object.__setattr__(self, "dmrst_gum_model_27", MappingProxyType(dict(self.dmrst_gum_model_27)))
        object.__setattr__(self, "dmrst_rstdt_model_42", MappingProxyType(dict(self.dmrst_rstdt_model_42)))


@cache
def load_ontology_lock(path: Path | None = None) -> OntologyLockData:
    """Load and parse the ontology lockfile, caching the immutable structure."""
    lock_path = path or LOCK_FILE_PATH
    if not lock_path.is_file():
        raise FileNotFoundError(f"Ontology lockfile not found at {lock_path}")

    raw_bytes = lock_path.read_bytes()
    computed_digest = hashlib.sha256(raw_bytes).hexdigest()

    raw_data: dict[str, Any] = yaml.safe_load(raw_bytes.decode("utf-8"))

    coarse_concepts = tuple(raw_data.get("coarse_concepts", []))
    rst_dt_fine = {str(k).lower(): str(v) for k, v in raw_data.get("rst_dt_fine_to_coarse", {}).items()}
    gum_fine = {str(k).lower(): str(v) for k, v in raw_data.get("gum_fine_to_coarse", {}).items()}

    dmrst_gum_27 = {
        int(k): ModelClassMapping(
            label=str(v["label"]),
            nuclearity=str(v["nuclearity"]),
            concept=str(v["concept"]),
        )
        for k, v in raw_data.get("dmrst_gum_model_27", {}).items()
    }

    dmrst_rstdt_42 = {
        int(k): ModelClassMapping(
            label=str(v["label"]),
            nuclearity=str(v["nuclearity"]),
            concept=str(v["concept"]),
        )
        for k, v in raw_data.get("dmrst_rstdt_model_42", {}).items()
    }

    return OntologyLockData(
        release_version=str(raw_data.get("release_version", "unknown")),
        release_status=str(raw_data.get("release_status", "unknown")),
        sha256_digest=computed_digest,
        coarse_concepts=coarse_concepts,
        rst_dt_fine_to_coarse=rst_dt_fine,
        gum_fine_to_coarse=gum_fine,
        dmrst_gum_model_27=dmrst_gum_27,
        dmrst_rstdt_model_42=dmrst_rstdt_42,
    )

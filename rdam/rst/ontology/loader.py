"""Load local label projections without claiming a Central_Configs release."""

from collections.abc import Mapping
from dataclasses import dataclass
from functools import cache
import hashlib
from importlib import resources
from pathlib import Path
from types import MappingProxyType
from typing import Literal, Self

import yaml
from pydantic import BaseModel, ConfigDict, model_validator

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


class _ClassEntry(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    label: str
    nuclearity: Literal["NS", "SN", "NN"]
    concept: str


class _LocalInventory(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    schema_version: Literal["1.0.0"]
    authority: Literal["local_inventory"]
    release_version: None
    release_status: Literal["unverified"]
    coarse_concepts: list[str]
    rst_dt_fine_to_coarse: dict[str, str]
    gum_fine_to_coarse: dict[str, str]
    dmrst_gum_model_27: dict[int, _ClassEntry]
    dmrst_rstdt_model_42: dict[int, _ClassEntry]

    @model_validator(mode="after")
    def consistent_inventory(self) -> Self:
        concepts = set(self.coarse_concepts)
        if not concepts or len(concepts) != len(self.coarse_concepts) or any(not value.strip() for value in concepts):
            raise ValueError("coarse concepts must be nonempty and unique")
        for mapping in (self.rst_dt_fine_to_coarse, self.gum_fine_to_coarse):
            if not mapping or any(not key.strip() or not value.strip() for key, value in mapping.items()):
                raise ValueError("label mappings must contain nonempty labels")
            if len({key.lower() for key in mapping}) != len(mapping):
                raise ValueError("label normalization would merge distinct mapping keys")
        if not set(self.rst_dt_fine_to_coarse.values()) <= concepts:
            raise ValueError("RST-DT mapping names an unknown coarse concept")
        for table in (self.dmrst_gum_model_27, self.dmrst_rstdt_model_42):
            if not table or set(table) != set(range(len(table))):
                raise ValueError("model class indices must be contiguous from zero")
            if any(not entry.label.strip() or entry.concept not in concepts for entry in table.values()):
                raise ValueError("model class mapping has an empty label or unknown concept")
        gum_categories = {entry.label for entry in self.dmrst_gum_model_27.values()}
        if not set(self.gum_fine_to_coarse.values()) <= gum_categories:
            raise ValueError("GUM mapping names an unknown model category")
        return self


@dataclass(frozen=True, slots=True)
class OntologyLockData:
    """Local inventory bytes and projections; canonical release provenance is absent."""

    authority: Literal["local_inventory"]
    release_version: None
    release_status: Literal["unverified"]
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
    """Validate local inventory data and identify the exact bytes loaded."""
    lock_path = path or LOCK_FILE_PATH
    if not lock_path.is_file():
        raise FileNotFoundError(f"Ontology lockfile not found at {lock_path}")

    raw_bytes = lock_path.read_bytes()
    computed_digest = hashlib.sha256(raw_bytes).hexdigest()

    inventory = _LocalInventory.model_validate(yaml.safe_load(raw_bytes.decode("utf-8")))

    coarse_concepts = tuple(inventory.coarse_concepts)
    rst_dt_fine = {key.lower(): value for key, value in inventory.rst_dt_fine_to_coarse.items()}
    gum_fine = {key.lower(): value for key, value in inventory.gum_fine_to_coarse.items()}

    dmrst_gum_27 = {
        k: ModelClassMapping(
            label=v.label,
            nuclearity=v.nuclearity,
            concept=v.concept,
        )
        for k, v in inventory.dmrst_gum_model_27.items()
    }

    dmrst_rstdt_42 = {
        k: ModelClassMapping(
            label=v.label,
            nuclearity=v.nuclearity,
            concept=v.concept,
        )
        for k, v in inventory.dmrst_rstdt_model_42.items()
    }

    return OntologyLockData(
        authority=inventory.authority,
        release_version=inventory.release_version,
        release_status=inventory.release_status,
        sha256_digest=computed_digest,
        coarse_concepts=coarse_concepts,
        rst_dt_fine_to_coarse=rst_dt_fine,
        gum_fine_to_coarse=gum_fine,
        dmrst_gum_model_27=dmrst_gum_27,
        dmrst_rstdt_model_42=dmrst_rstdt_42,
    )

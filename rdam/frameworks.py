"""Canonical framework identities, referenced from Central_Configs and never redefined.

The eight identities live in Central's ``coe:artifact/narrative/analytical_frameworks_taxonomy``.
Verified 2026-09-02 at Central_Configs ``ontology/data/domains/narrative/analytical_frameworks.yaml``
lines 34-113 (commit ``46056cd``): concept ids are
``coe:concept/analytical_frameworks_taxonomy/discourse_structure_framework/{rst,erst,pdtb,sdrt}``
and ``coe:concept/analytical_frameworks_taxonomy/argumentation_framework/{toulmin,walton,dung,ibis}``,
each with ``in_scheme`` naming the taxonomy and one ``broader`` parent concept.

This module ships a *projection* of them — ``resources/framework-identities.json``, generated
by ``tools/ontology/project_framework_identities.py`` from the vendored distribution under
``ontology/vendor/central-configs/`` and checked against it by test — so that an installed
``rdam`` resolves identities without a repository checkout, as Central's consumer contract
prescribes ("generate or author that projection inside the consumer").

Seven of the eight are production technique boundaries. The ``erst`` identity remains
for saved records and workbench evaluation; production providers do not execute it.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from functools import cache
from importlib import resources
import json
from types import MappingProxyType
from typing import Final, Literal, cast

from rdam._strict import Sha256Identity, StrictModel, sha256_bytes

FRAMEWORK_SCHEME: Final = "coe:artifact/narrative/analytical_frameworks_taxonomy"
_CONCEPT_ROOT: Final = "coe:concept/analytical_frameworks_taxonomy"


class Technique(StrEnum):
    """The framework identities the machine knows, keyed by their short name in Central."""

    RST = "rst"
    ERST = "erst"
    PDTB = "pdtb"
    SDRT = "sdrt"
    TOULMIN = "toulmin"
    WALTON = "walton"
    DUNG = "dung"
    IBIS = "ibis"


BOUNDARY_TECHNIQUES: Final[tuple[Technique, ...]] = (
    Technique.RST,
    Technique.PDTB,
    Technique.SDRT,
    Technique.TOULMIN,
    Technique.WALTON,
    Technique.DUNG,
    Technique.IBIS,
)
"""The seven technique boundaries of FR-002, in the spec's order. ``erst`` is retained for saved records and workbench evaluation."""

STRUCTURED_INPUT_TECHNIQUES: Final[frozenset[Technique]] = frozenset({Technique.DUNG, Technique.IBIS})
"""Techniques that analyse a supplied structure, not raw text (FR-016, FR-017)."""


@dataclass(frozen=True, slots=True)
class FrameworkIdentity:
    """One framework concept exactly as registered in Central."""

    technique: Technique
    curie: str
    label: str
    broader: str
    scheme: str


class FrameworkResolutionError(LookupError):
    """A framework identity is absent from, or inconsistent with, the packaged projection."""


class FrameworkAuthority(StrictModel):
    """Exact authority source and generated projection used for framework identities.

    This describes framework registration, not native relation equivalence.
    Source dates are not substituted for release versions.
    """

    authority: Literal["Central_Configs"] = "Central_Configs"
    scheme: str
    source: str
    source_identity: Sha256Identity
    projection_identity: Sha256Identity


@cache
def framework_authority() -> FrameworkAuthority:
    """Identify the installed projection without loading the sibling repository."""
    raw = resources.files("rdam").joinpath("resources/framework-identities.json").read_bytes()
    payload = json.loads(raw)
    if payload.get("scheme") != FRAMEWORK_SCHEME:
        raise FrameworkResolutionError("framework projection names the wrong scheme")
    return FrameworkAuthority(
        scheme=payload["scheme"],
        source=payload["source"],
        source_identity=Sha256Identity(hex_digest=payload["source_sha256"]),
        projection_identity=Sha256Identity(hex_digest=sha256_bytes(raw)),
    )


@cache
def framework_identities() -> Mapping[Technique, FrameworkIdentity]:
    """Load the packaged projection once; every identity must match Central's id pattern."""

    payload = json.loads(
        resources.files("rdam").joinpath("resources/framework-identities.json").read_text(encoding="utf-8")
    )
    if payload.get("scheme") != FRAMEWORK_SCHEME:
        raise FrameworkResolutionError("framework projection names the wrong scheme")
    concepts = payload.get("concepts")
    if not isinstance(concepts, dict):
        raise FrameworkResolutionError("framework projection has no concepts mapping")
    concept_map = cast(dict[object, object], concepts)
    if set(concept_map) != {technique.value for technique in Technique}:
        raise FrameworkResolutionError("framework projection does not match the registered techniques")
    resolved: dict[Technique, FrameworkIdentity] = {}
    for technique in Technique:
        entry = concept_map.get(technique.value)
        if not isinstance(entry, dict):
            raise FrameworkResolutionError(f"framework projection lacks {technique.value!r}")
        concept = cast(dict[object, object], entry)
        if any(not isinstance(concept.get(field), str) or not str(concept[field]).strip()
               for field in ("id", "label", "broader", "in_scheme")):
            raise FrameworkResolutionError(f"framework identity for {technique.value!r} has invalid text fields")
        curie = cast(str, concept["id"])
        broader = cast(str, concept["broader"])
        if not curie.startswith(f"{_CONCEPT_ROOT}/") or not curie.endswith(f"/{technique.value}"):
            raise FrameworkResolutionError(
                f"framework identity for {technique.value!r} does not follow Central's concept id pattern: {curie}"
            )
        if concept.get("in_scheme") != FRAMEWORK_SCHEME:
            raise FrameworkResolutionError(f"framework identity for {technique.value!r} is outside the scheme")
        if curie.rpartition("/")[0] != broader or broader == _CONCEPT_ROOT:
            raise FrameworkResolutionError(f"framework identity for {technique.value!r} has an inconsistent parent")
        resolved[technique] = FrameworkIdentity(
            technique=technique,
            curie=curie,
            label=cast(str, concept["label"]),
            broader=broader,
            scheme=cast(str, concept["in_scheme"]),
        )
    return MappingProxyType(resolved)


def technique_curie(technique: Technique) -> str:
    """The canonical ``coe:`` identifier for a technique."""

    return framework_identities()[technique].curie


__all__ = [
    "BOUNDARY_TECHNIQUES",
    "FRAMEWORK_SCHEME",
    "STRUCTURED_INPUT_TECHNIQUES",
    "FrameworkAuthority",
    "FrameworkIdentity",
    "FrameworkResolutionError",
    "Technique",
    "framework_authority",
    "framework_identities",
    "technique_curie",
]

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

Seven of the eight are technique boundaries. ``erst`` is not a boundary: the RST provider
serves it as a declared formalism (006 data-model §Formalism).
"""

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from functools import cache
from importlib import resources
import json
from typing import Final

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
"""The seven technique boundaries of FR-002, in the spec's order. ``erst`` is a formalism."""

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
    resolved: dict[Technique, FrameworkIdentity] = {}
    for technique in Technique:
        entry = concepts.get(technique.value)
        if not isinstance(entry, dict):
            raise FrameworkResolutionError(f"framework projection lacks {technique.value!r}")
        curie = str(entry["id"])
        if not curie.startswith(f"{_CONCEPT_ROOT}/") or not curie.endswith(f"/{technique.value}"):
            raise FrameworkResolutionError(
                f"framework identity for {technique.value!r} does not follow Central's concept id pattern: {curie}"
            )
        if entry.get("in_scheme") != FRAMEWORK_SCHEME:
            raise FrameworkResolutionError(f"framework identity for {technique.value!r} is outside the scheme")
        resolved[technique] = FrameworkIdentity(
            technique=technique,
            curie=curie,
            label=str(entry["label"]),
            broader=str(entry["broader"]),
            scheme=str(entry["in_scheme"]),
        )
    return resolved


def technique_curie(technique: Technique) -> str:
    """The canonical ``coe:`` identifier for a technique."""

    return framework_identities()[technique].curie


__all__ = [
    "BOUNDARY_TECHNIQUES",
    "FRAMEWORK_SCHEME",
    "STRUCTURED_INPUT_TECHNIQUES",
    "FrameworkIdentity",
    "FrameworkResolutionError",
    "Technique",
    "framework_identities",
    "technique_curie",
]

"""Explicit GUM coarse evaluation projection, separate from ontology semantics.

The GUM training path in workbench/corpus/dmrst/data_manager.py reduces a
hyphenated relation to its family, retaining same-unit. Resolve exact inventory
members before family projection so compound inventory labels remain intact.
This projection never rewrites nuclearity to imitate training-data repairs.
"""

from collections.abc import Collection, Sequence
from types import MappingProxyType
from collections.abc import Mapping

from rdam.rst.contracts.enums import NuclearityPatternEnum


def gum_coarse_projection(
    gold_relations: Collection[str], joint_inventory: Sequence[str],
    *, native_aliases: Mapping[str, str] | None = None,
) -> Mapping[str, str]:
    """Resolve header-declared gold labels into an explicitly supplied inventory.

    Unknown families fail rather than passing through as apparent coarse labels.
    Inventory labels themselves map identically, allowing one scorer to project
    both sides without modifying either native analysis.
    """
    families: set[str] = set()
    classes: set[str] = set()
    for joint in joint_inventory:
        relation, separator, nuclearity = joint.strip().rpartition("_")
        if not separator or not relation or nuclearity not in NuclearityPatternEnum:
            raise ValueError(f"Invalid joint relation/nuclearity class: {joint!r}")
        normalized = f"{relation.casefold()}_{nuclearity}"
        if normalized in classes:
            raise ValueError(f"Duplicate joint class: {joint!r}")
        classes.add(normalized)
        families.add(relation.casefold())
    if not families:
        raise ValueError("Evaluation requires a non-empty model label inventory")
    aliases = dict(native_aliases or {})
    if not aliases.keys() <= families:
        raise ValueError("Evaluation alias names a label absent from the native inventory")
    projection = {family: aliases.get(family, family) for family in families}
    families = set(projection.values())
    projection.update({family: family for family in families})
    for raw in gold_relations:
        label = raw.strip().casefold()
        if label in families:
            projection[label] = label
            continue
        family, separator, subtype = label.partition("-")
        if not separator or not subtype or family not in families:
            raise ValueError(f"Gold relation has no supported GUM coarse family: {raw!r}")
        projection[label] = family
    return MappingProxyType(projection)

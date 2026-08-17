"""Nuclearity-based ref split, format-agnostic."""


def split_refs_by_nuclearity(
    left_refs: tuple[str, ...],
    right_refs: tuple[str, ...],
    nuclearity: str,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Return ``(nucleus_refs, satellite_refs)`` based on ``nuclearity``.

    ``"NS"`` puts left into nucleus; ``"SN"`` puts right into nucleus.
    Anything else (``"NN"``, ``""``, or an unrecognised label) treats both
    children as nuclei with empty satellites.
    """
    if nuclearity == "NS":
        return left_refs, right_refs
    if nuclearity == "SN":
        return right_refs, left_refs
    return left_refs + right_refs, ()

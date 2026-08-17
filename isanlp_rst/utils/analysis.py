"""Analytical helpers for parsed RST trees.

These functions operate on ``isanlp.annotation_rst.DiscourseUnit`` trees
(the structure returned by :class:`isanlp_rst.parser.Parser`) but do not
import that class — they rely on duck-typed attributes (``left``, ``right``,
``relation``, ``nuclearity``, ``entropy``, ``start``, ``end``, ``text``).
This keeps them usable on trees loaded from ``.rs3`` files via the viewer
as well as trees produced by this parser.

Three helpers are exposed:

* :func:`find_cdu` — locate the Central Discourse Unit per Mann & Thompson.
* :func:`relation_category` — classify a relation label as subject-matter,
  presentational, or unknown (Mann & Thompson 1988 taxonomy).
* :func:`tree_stats` — structural diagnostics over the tree.
"""

from collections import Counter
from typing import Any, Literal

__all__ = ["find_cdu", "relation_category", "tree_stats"]

type RelationCategory = Literal["subject_matter", "presentational", "unknown"]


# Mann & Thompson 1988 + SFU online reference. Borderline cases (Restatement,
# Summary, Evaluation, Comparison) are placed per the original 1988 paper;
# later inventories sometimes move them — adjust here if your downstream
# analysis treats them as presentational.
_SUBJECT_MATTER: frozenset[str] = frozenset(
    {
        "elaboration",
        "circumstance",
        "cause",
        "volitional-cause",
        "non-volitional-cause",
        "result",
        "volitional-result",
        "non-volitional-result",
        "purpose",
        "condition",
        "otherwise",
        "interpretation",
        "means",
        "solutionhood",
        "sequence",
        "contrast",
        "joint",
        "list",
        "same-unit",
        "restatement",
        "summary",
        "evaluation",
        "comparison",
    }
)

_PRESENTATIONAL: frozenset[str] = frozenset(
    {
        "motivation",
        "antithesis",
        "background",
        "enablement",
        "evidence",
        "justify",
        "concession",
        "preparation",
    }
)


def _is_leaf(node: Any) -> bool:
    return getattr(node, "left", None) is None and getattr(node, "right", None) is None


def find_cdu(tree: Any, *, force_leaf: bool = False) -> Any:
    """Locate the Central Discourse Unit (CDU) of an RST tree.

    Descends from the root following the nucleus pointer at each step.

    Default behaviour (``force_leaf=False``) is theoretically faithful to
    Mann & Thompson: at a multinuclear (``NN``) node both children are
    equally central, so the multinuclear node itself is returned. The
    result may therefore be an internal node rather than a leaf.

    With ``force_leaf=True``, multinuclear nodes are resolved by descending
    into the left child — the standard Marcu-style head-promotion shortcut.
    Use this when downstream code requires a single EDU (e.g. summarisation
    or salient-unit retrieval).

    Parameters
    ----------
    tree:
        Root ``DiscourseUnit`` of an RST analysis.
    force_leaf:
        If True, never stop at a multinuclear node — pick the left child.

    Returns
    -------
    The ``DiscourseUnit`` identified as the CDU.

    Raises
    ------
    ValueError
        If ``tree`` is None.
    """
    if tree is None:
        raise ValueError("tree must be a DiscourseUnit, not None")

    node = tree
    while True:
        if _is_leaf(node):
            return node

        nuc = getattr(node, "nuclearity", None)
        left = getattr(node, "left", None)
        right = getattr(node, "right", None)

        if nuc == "NS":
            node = left
        elif nuc == "SN":
            node = right
        elif nuc == "NN":
            if force_leaf:
                node = left
            else:
                return node
        else:
            # Unknown / missing nuclearity — can't safely descend.
            return node


def relation_category(label: str, inventory: str | None = None) -> RelationCategory:
    """Classify an RST relation label as subject-matter or presentational.

    Follows Mann & Thompson's 1988 taxonomy: subject-matter relations
    link informational content (Elaboration, Cause, Sequence, …);
    presentational relations are intended to influence the reader's
    beliefs or attitudes (Motivation, Evidence, Antithesis, …).

    Matching is case-insensitive and tolerant of underscores vs hyphens.
    Compound labels like ``elaboration-additional`` or
    ``Cause-Result`` are normalised by trying the full label, then the
    leading component, then the trailing component (handles
    ``non-volitional-cause`` etc.).

    Parameters
    ----------
    label:
        The relation label produced by the parser.
    inventory:
        Reserved for per-inventory overrides (e.g. when a corpus uses a
        label this taxonomy does not list). Currently ignored; accept for
        API stability.

    Returns
    -------
    ``"subject_matter"``, ``"presentational"``, or ``"unknown"``.
    """
    if not isinstance(label, str) or not label:
        return "unknown"

    raw = label.lower().replace("_", "-").strip()

    if raw in _SUBJECT_MATTER:
        return "subject_matter"
    if raw in _PRESENTATIONAL:
        return "presentational"

    parts = raw.split("-")
    head, tail = parts[0], parts[-1]

    if head in _SUBJECT_MATTER or tail in _SUBJECT_MATTER:
        return "subject_matter"
    if head in _PRESENTATIONAL or tail in _PRESENTATIONAL:
        return "presentational"

    return "unknown"


def tree_stats(tree: Any) -> dict[str, Any]:
    """Compute structural diagnostics for an RST tree.

    Returned dict keys:

    ``depth``
        Maximum distance from the root to any leaf (root depth = 0).
    ``n_leaves``
        Number of EDU leaves.
    ``n_internal``
        Number of internal (non-leaf) nodes.
    ``nuclearity_counts``
        Tally of ``N`` and ``S`` characters across all internal-node
        nuclearity strings (``NN`` contributes two ``N``s, ``NS`` and
        ``SN`` contribute one of each).
    ``nuc_sat_ratio``
        ``N`` count divided by ``S`` count, or ``inf`` when there are
        no satellites.
    ``relation_counts``
        Counter of relation labels on internal nodes.
    ``relation_categories``
        Counter of subject-matter / presentational / unknown across
        internal nodes — useful for spotting rhetorical-vs-informational
        balance.
    ``mean_entropy``
        Arithmetic mean of internal-node ``entropy`` fields. ``None`` if
        the tree carries no entropy information.

    Parameters
    ----------
    tree:
        Root ``DiscourseUnit`` of the analysis.

    Returns
    -------
    Dict of diagnostics. Safe on a single-leaf tree (returns
    ``n_leaves=1`` and zeroed counters).

    Raises
    ------
    ValueError
        If ``tree`` is None.
    """
    if tree is None:
        raise ValueError("tree must be a DiscourseUnit, not None")

    depth = 0
    n_leaves = 0
    n_internal = 0
    nuclearity_chars: Counter[str] = Counter()
    relation_counts: Counter[str] = Counter()
    relation_categories: Counter[str] = Counter()
    entropies: list[float] = []

    stack: list[tuple[Any, int]] = [(tree, 0)]
    while stack:
        node, d = stack.pop()
        if d > depth:
            depth = d

        if _is_leaf(node):
            n_leaves += 1
            continue

        n_internal += 1

        nuc = getattr(node, "nuclearity", None)
        if isinstance(nuc, str):
            nuclearity_chars.update(ch for ch in nuc if ch in ("N", "S"))

        rel = getattr(node, "relation", None)
        if isinstance(rel, str) and rel:
            relation_counts[rel] += 1
            relation_categories[relation_category(rel)] += 1

        ent = getattr(node, "entropy", None)
        if isinstance(ent, (int, float)):
            entropies.append(float(ent))

        left = getattr(node, "left", None)
        right = getattr(node, "right", None)
        if right is not None:
            stack.append((right, d + 1))
        if left is not None:
            stack.append((left, d + 1))

    n_count = nuclearity_chars.get("N", 0)
    s_count = nuclearity_chars.get("S", 0)
    nuc_sat_ratio: float = (n_count / s_count) if s_count else float("inf")
    mean_entropy: float | None = sum(entropies) / len(entropies) if entropies else None

    return {
        "depth": depth,
        "n_leaves": n_leaves,
        "n_internal": n_internal,
        "nuclearity_counts": dict(nuclearity_chars),
        "nuc_sat_ratio": nuc_sat_ratio,
        "relation_counts": dict(relation_counts),
        "relation_categories": dict(relation_categories),
        "mean_entropy": mean_entropy,
    }

"""Detect structural boundaries in a markdown harvest.

Boundaries are derived from the ordered main-harvest spans plus the
per-table harvests. The mapper later intersects each boundary's
``block_refs`` with each RST relation's block_refs to produce
``boundary_memberships``.

Boundary kinds:

- ``section-N`` — opened at each ``heading`` span; ``level`` ∈ {1..6}.
  ``blockquote_heading`` spans are quoted content, not document
  structure — they never open a section. Pre-heading content lives in
  a leading ``document`` boundary; when no headings exist at all, a
  single ``document`` boundary covers everything.
- ``table-T`` — one per table harvest; ``block_refs`` is
  ``(#/tables/T, <cell block_refs…>)``. The synthetic ``#/tables/T``
  marker carries no ``HarvestSpan`` so it cannot land in relation refs.
  Cells live in the table boundary only — they are not part of the
  document tree (two-level analysis), so they belong to no section.
- ``code_block-N`` — one per ``code_block`` span.
- ``document`` — fallback when no headings exist, or pre-heading bucket
  when content precedes the first heading.
"""

from .schema import Boundary, HarvestSpan, TableHarvest


def detect_boundaries(
    spans: tuple[HarvestSpan, ...],
    table_harvests: tuple[TableHarvest, ...] = (),
) -> tuple[Boundary, ...]:
    """Detect all boundaries in the main ``spans`` + ``table_harvests``."""
    boundaries: list[Boundary] = []

    # Section detection — first bucket is the pre-heading "document" bucket.
    buckets: list[tuple[str | None, int | None, list[str]]] = [(None, None, [])]
    for sp in spans:
        if sp.kind == "heading":
            buckets.append((sp.text or None, sp.level, [sp.block_ref]))
        else:
            buckets[-1][2].append(sp.block_ref)

    document_refs = buckets[0][2]
    if document_refs:
        boundaries.append(
            Boundary(
                id="document",
                kind="document",
                label=None,
                parent_block_ref=None,
                block_refs=tuple(document_refs),
            )
        )
    for i, (label, level, refs) in enumerate(buckets[1:]):
        boundaries.append(
            Boundary(
                id=f"section-{i}",
                kind="section",
                label=label,
                parent_block_ref=None,
                block_refs=tuple(refs),
                level=level,
            )
        )

    # Tables — one boundary per harvest, marker first then cell refs.
    for th in table_harvests:
        boundaries.append(
            Boundary(
                id=f"table-{th.table_idx}",
                kind="table",
                label=None,
                parent_block_ref=None,
                block_refs=(th.marker_ref, *(s.block_ref for s in th.spans)),
            )
        )

    # Code blocks — one per ``code_block`` span in document order.
    code_idx = 0
    for sp in spans:
        if sp.kind == "code_block":
            boundaries.append(
                Boundary(
                    id=f"code_block-{code_idx}",
                    kind="code_block",
                    label=None,
                    parent_block_ref=None,
                    block_refs=(sp.block_ref,),
                )
            )
            code_idx += 1

    return tuple(boundaries)


__all__ = ["detect_boundaries"]

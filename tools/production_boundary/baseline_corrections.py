"""Narrow proofs for the two owner-approved Feature 017 correctness repairs.

These are comparison-only rules, not compatibility code. No production harvesting
or table-construction function is called: the immutable source, historical inventory
and the complete before/after values must establish the correction independently.
"""

from collections.abc import Iterator
from copy import deepcopy
from typing import Any
from xml.etree import ElementTree

from rdam.ingest.contracts.source import OriginClassification, SourceArtifact, SourceForm
from rdam.ingest.identity import semantic_sha256

type JsonPath = tuple[str, ...]


class BaselineVerificationError(ValueError):
    """The current record does not satisfy an independently checked source invariant."""


def _objects(value: Any, path: JsonPath = ()) -> Iterator[tuple[JsonPath, dict[str, Any]]]:
    if isinstance(value, dict):
        yield path, value
        for key, child in value.items():
            yield from _objects(child, (*path, key))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _objects(child, (*path, str(index)))


def source_identity_correction_paths(
    baseline: dict[str, Any], actual: dict[str, Any], source: SourceArtifact,
) -> frozenset[JsonPath]:
    """Prove the URI-to-local origin repair and exact, otherwise unchanged references."""

    if source.origin_classification is not OriginClassification.LOCAL_FILE or not source.declared_origin:
        return frozenset()
    fields = source.model_dump(mode="json", exclude={"source_id", "raw_bytes", "edus"})
    corrected_id = semantic_sha256(fields)
    previous_id = semantic_sha256({**fields, "origin_classification": OriginClassification.URI})
    if corrected_id != source.source_id:
        raise ValueError("comparison source has an invalid identity")
    expected = source.summary().model_dump(mode="json")
    previous = {**expected, "source_id": previous_id}
    old_objects = dict(_objects(baseline))
    new_objects = dict(_objects(actual))
    summary_paths = (("semantic", "source"), ("semantic", "prepared_document", "source"))
    if baseline.get("kind") != "preparation_outcome" or actual.get("kind") != "preparation_outcome":
        return frozenset()
    if any(old_objects.get(path) != previous or new_objects.get(path) != expected for path in summary_paths):
        return frozenset()
    paths = {(*path, "source_id") for path in summary_paths}
    for path, before in old_objects.items():
        if len(path) < 2 or path[-2] not in {"anchors", "source_anchors"} or not path[-1].isdigit():
            continue
        after = new_objects.get(path)
        if before.get("artifact_identity") == previous_id and after == {**before, "artifact_identity": corrected_id}:
            paths.add((*path, "artifact_identity"))
    return frozenset(paths)


def rebind_verified_identities(
    baseline: dict[str, Any], actual: dict[str, Any], paths: frozenset[JsonPath],
) -> dict[str, Any]:
    """Normalize only proven identity leaves on a copy for the separate table proof."""

    normalized = deepcopy(baseline)
    old_objects = dict(_objects(normalized))
    new_objects = dict(_objects(actual))
    for path in paths:
        old_objects[path[:-1]][path[-1]] = new_objects[path[:-1]][path[-1]]
    return normalized


# OTSL cell markers in DocLang spec.md at 6d3b3d3c195d1f63333c5c5fcba8da17937a33bd.
# nl moves to the next row; srow begins a section-row header cell.
_CELL_TOKENS = frozenset({"fcel", "ecel", "ched", "rhed", "corn", "srow", "lcel", "ucel", "xcel"})
_CONTINUATIONS = frozenset({"lcel", "ucel", "xcel"})


def _xml_table_evidence(
    payload: bytes, *, historical: bool = False,
) -> tuple[dict[str, tuple[int, int, str]], dict[str, str | None]]:
    """Read marker coordinates directly from XML, independently of RDAM adapters."""

    coordinates: dict[str, tuple[int, int, str]] = {}
    section_headers: dict[str, str | None] = {}
    tokens = _CELL_TOKENS - {"srow"} if historical else _CELL_TOKENS

    def walk(element: ElementTree.Element, path: str) -> None:
        counts: dict[str, int] = {}
        row = column = 0
        for index, child in enumerate(element):
            tag = child.tag.rsplit("}", 1)[-1]
            counts[tag] = counts.get(tag, 0) + 1
            child_path = f"{path}/{tag}[{counts[tag]}]"
            if element.tag.rsplit("}", 1)[-1] == "table":
                if tag in tokens:
                    coordinates[child_path] = (row, column, tag)
                    column += 1
                elif tag == "nl":
                    row += 1
                    column = 0
                if tag == "srow":
                    pieces = [child.tail or ""]
                    for following in list(element)[index + 1:]:
                        if following.tag.rsplit("}", 1)[-1] in _CELL_TOKENS | {"nl"}:
                            break
                        pieces.extend(("".join(following.itertext()), following.tail or ""))
                    section_headers[child_path] = "".join(pieces).strip() or None
            walk(child, child_path)

    root = ElementTree.fromstring(payload)
    walk(root, f"/{root.tag.rsplit('}', 1)[-1]}[1]")
    return coordinates, section_headers


def _table_from_inventory(
    children: list[dict[str, Any]], coordinates: dict[str, tuple[int, int, str]], *, historical: bool,
) -> dict[str, Any]:
    """Reconstruct the precise historical defect or the source-anchored correction.

    Historical records assigned unanchored wrappers (child index, 0), allowing
    collisions. Only that exact before representation qualifies, not an arbitrary
    old table. Corrected geometry comes directly from XML marker coordinates.
    Text and links come from the unchanged, retained historical inventory.
    """

    occupied: dict[tuple[int, int], tuple[dict[str, Any], str]] = {}
    links: dict[str, list[str]] = {}
    current: str | None = None
    for index, child in enumerate(children):
        cell_id = child["item_id"]
        coordinate = coordinates.get(cell_id)
        if coordinate is None and not historical:
            if current is not None and child["representation"].get("text") is not None:
                links[current].append(cell_id)
            continue
        row, column, token = coordinate if coordinate is not None else (index, 0, "fcel")
        occupied[row, column] = (child, token)
        current = cell_id
        links[current] = list(child["child_ids"])
    cells: list[dict[str, Any]] = []
    for (row, column), (child, token) in sorted(occupied.items()):
        if token in _CONTINUATIONS:
            continue
        attributes = dict(child["provider_attributes"])
        width = int(attributes.get("column_span", attributes.get("col_span", "1")))
        height = int(attributes.get("row_span", "1"))
        while occupied.get((row, column + width), ({}, ""))[1] in {"lcel", "xcel"}:
            width += 1
        while occupied.get((row + height, column), ({}, ""))[1] in {"ucel", "xcel"}:
            height += 1
        cells.append({
            "cell_id": child["item_id"], "row": row, "column": column,
            "row_span": height, "column_span": width,
            "text": child["representation"].get("text"),
            "header": token in {"ched", "rhed", "corn", "srow"}
            or attributes.get("column_header") == "true" or attributes.get("row_header") == "true",
            "linked_item_ids": list(dict.fromkeys(links[child["item_id"]])),
        })
    return {"kind": "table", "cells": cells}


def _verify_table_coordinates(
    children: list[dict[str, Any]], coordinates: dict[str, tuple[int, int, str]], table_id: str,
) -> None:
    observed: dict[str, tuple[int, int, str]] = {}
    for child in children:
        for anchor in child["anchors"]:
            if anchor["kind"] == "table_coordinate":
                native = coordinates.get(child["item_id"])
                if native is None or (anchor["row"], anchor["column"]) != native[:2]:
                    raise BaselineVerificationError(f"table coordinate disagrees with source XML: {child['item_id']}")
                if child["item_id"] in observed:
                    raise BaselineVerificationError(f"duplicate table coordinate: {child['item_id']}")
                observed[child["item_id"]] = native
    expected = {path: coord for path, coord in coordinates.items() if path.rsplit("/", 1)[0] == table_id}
    if observed != expected:
        raise BaselineVerificationError(f"inventory does not cover the source table markers: {table_id}")


def verify_preparation_source(actual: dict[str, Any], source: SourceArtifact) -> None:
    """Reject wrong current output even when it repeats an unchanged historical bug."""

    if actual.get("kind") != "preparation_outcome":
        return
    objects = dict(_objects(actual))
    expected_source = source.summary().model_dump(mode="json")
    for path in (("semantic", "source"), ("semantic", "prepared_document", "source")):
        if objects.get(path) != expected_source:
            raise BaselineVerificationError(f"current source summary does not match the materialized source: {'/'.join(path)}")
    for path, anchor in objects.items():
        if len(path) >= 2 and path[-2] in {"anchors", "source_anchors"} and path[-1].isdigit():
            if anchor.get("artifact_identity") != source.source_id:
                raise BaselineVerificationError(f"current anchor is bound to the wrong source: {'/'.join(path)}")
    if source.source_form is not SourceForm.DOCLANG_XML or source.raw_bytes is None:
        return
    coordinates, section_headers = _xml_table_evidence(source.raw_bytes)
    inventory = actual["semantic"]["inventory"]
    for item in inventory:
        if item["item_id"] in section_headers and item["representation"].get("text") != section_headers[item["item_id"]]:
            raise BaselineVerificationError(f"section-row header text disagrees with source XML: {item['item_id']}")
        if item["classification"] != "table":
            continue
        children = [child for child in inventory if child["parent_id"] == item["item_id"] and child["classification"] == "table_cell"]
        _verify_table_coordinates(children, coordinates, item["item_id"])
        if item["representation"] != _table_from_inventory(children, coordinates, historical=False):
            raise BaselineVerificationError(f"current table representation does not match source-anchored cells: {item['item_id']}")


def doclang_table_correction_prefixes(
    baseline: dict[str, Any], actual: dict[str, Any], source: SourceArtifact,
) -> frozenset[JsonPath]:
    """Accept only exact wrapper-removal corrections with unchanged inventory evidence.

    The baseline passed here has only independently verified source IDs rebound.
    Missing/changed inventory, source bytes, cell text, spans, headers or links never
    qualify. Other changed fields remain visible to the ordinary comparator.
    """

    if source.source_form is not SourceForm.DOCLANG_XML or source.raw_bytes is None:
        return frozenset()
    if baseline.get("kind") != "preparation_outcome" or actual.get("kind") != "preparation_outcome":
        return frozenset()
    before = baseline["semantic"]
    after = actual["semantic"]
    expected_source = source.summary().model_dump(mode="json")
    if before.get("source") != expected_source or after.get("source") != expected_source:
        return frozenset()
    historical_inventory = before.get("inventory", [])
    old_inventory = deepcopy(historical_inventory)
    new_inventory = after.get("inventory", [])
    if len(old_inventory) != len(new_inventory):
        return frozenset()
    coordinates, section_headers = _xml_table_evidence(source.raw_bytes)
    historical_coordinates, _ = _xml_table_evidence(source.raw_bytes, historical=True)
    prefixes: set[JsonPath] = set()
    for index, (old, new) in enumerate(zip(old_inventory, new_inventory, strict=True)):
        cell_id = old["item_id"]
        if cell_id not in section_headers or old == new:
            continue
        if old["representation"] != {
            "kind": "structure", "structure_type": "table_cell", "label": None, "child_ids": [],
        }:
            return frozenset()
        text = section_headers[cell_id]
        representation = old["representation"] if text is None else {
            "kind": "text", "text": text, "language": None, "semantic_role": "table_cell", "attributes": [],
        }
        row, column, _ = coordinates[cell_id]
        anchors = [*old["anchors"], {
            "kind": "table_coordinate", "artifact_identity": source.source_id, "row": row, "column": column,
        }]
        if new != {**old, "representation": representation, "anchors": anchors}:
            return frozenset()
        old.update(representation=representation, anchors=anchors)
        prefixes.update((
            ("semantic", "inventory", str(index), "representation"),
            ("semantic", "inventory", str(index), "anchors"),
        ))

    def evidence(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {key: value for key, value in item.items() if key != "representation" or item["classification"] != "table"}
            for item in items
        ]

    if evidence(old_inventory) != evidence(new_inventory):
        return frozenset()
    for index, (old, new) in enumerate(zip(old_inventory, new_inventory, strict=True)):
        if old["classification"] != "table":
            continue
        children = [item for item in old_inventory if item["parent_id"] == old["item_id"] and item["classification"] == "table_cell"]
        # Every recorded coordinate must agree with the source XML, and every
        # marker in this table must be present in the historical inventory.
        _verify_table_coordinates(children, coordinates, old["item_id"])
        historical_children = [item for item in historical_inventory if item["parent_id"] == old["item_id"] and item["classification"] == "table_cell"]
        if old["representation"] == _table_from_inventory(historical_children, historical_coordinates, historical=True) and (
            new["representation"] == _table_from_inventory(children, coordinates, historical=False)
        ):
            prefixes.add(("semantic", "inventory", str(index), "representation"))
    return frozenset(prefixes)

"""Select exact evidence from concept exports or CSM retrieval cards; no ranking."""
import argparse
from collections.abc import Iterator
import json
from pathlib import Path
from typing import Any

from rdam.concepts.serialization import MentionExport, load_result, mention_records
from rdam.contracts import AggregateAnalysis, MachinePreparation, ResultOutcome
from rdam.ingest.contracts.preparation import ContentInventory, PreparationWarning
from rdam.serialization import decode_object, load


def records(path: Path) -> Iterator[tuple[MentionExport, str, str | None]]:
    """Consume closed shared exports, or the additive field owned by CSM."""
    payload = path.read_bytes()
    try:
        single = decode_object(payload)
    except json.JSONDecodeError:
        documents = [decode_object(line) for line in payload.splitlines() if line.strip()]
    else:
        documents = [single]
    for document in documents:
        contract = document.get("contract")
        if contract == "rdam.concept_links":
            for record in mention_records(load_result(json.dumps(document))):
                yield record, "pending", None
        elif contract == "rdam.concept_mention":
            yield MentionExport.model_validate_json(json.dumps(document)), "pending", None
        elif document.get("schema_version") in {"5.2", "5.3"} and isinstance(document.get("slug"), str):
            # CSM validates the whole card. This independent reader consumes only
            # its additive mention field; historical absence means no evidence.
            for reviewed in document.get("concept_mentions", []):
                record = MentionExport.model_validate_json(json.dumps(reviewed["evidence"]))
                status, target = reviewed["match"], reviewed.get("canonical_identifier")
                if status not in {"exact", "close", "unmapped"}:
                    raise ValueError("invalid CSM review status")
                identifiers = {item.resource.identifier for item in record.mention.candidates}
                if (status == "unmapped" and target is not None) or (status != "unmapped" and target not in identifiers):
                    raise ValueError("CSM review target differs from exported candidates")
                yield record, status, target
        else:
            raise ValueError("unsupported concept export or retrieval card")


def native_locations(record: MentionExport, analysis: AggregateAnalysis) -> list[dict[str, Any]]:
    """Join shared inventory items and original anchors, never inferred semantics."""
    analysis = AggregateAnalysis.model_validate(analysis.model_dump())
    preparation = analysis.preparation
    if not isinstance(preparation, MachinePreparation):
        raise ValueError("join requires current shared preparation evidence")
    semantic = preparation.preparation
    inventory = ContentInventory(source=semantic.source, source_contract=semantic.source_contract,
        items=semantic.inventory, empty_submitted_content=PreparationWarning.EMPTY_SUBMITTED_CONTENT in semantic.warnings)
    if (inventory.source != record.source or inventory.semantic_digest != record.inventory_identity
            or inventory.source_contract != record.source_adapter):
        raise ValueError("analysis and mention do not share source and inventory identity")
    locations: list[dict[str, Any]] = []
    for outcome in analysis.outcomes:
        if not isinstance(outcome, ResultOutcome):
            continue
        for alignment in outcome.result.source_alignment:
            if (record.mention.item_id in alignment.contributing_item_ids
                    and any(anchor in alignment.source_anchors for anchor in record.surface.anchors)):
                locations.append({"technique": outcome.result.technique.value,
                    "payload_path": alignment.payload_path, "native_quote": alignment.quote,
                    "native_relationship": alignment.relationship, "join": "shared_inventory_item",
                    "source_anchors": [anchor.model_dump(mode="json") for anchor in alignment.source_anchors]})
    return locations


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("identifier")
    parser.add_argument("--analysis", type=Path)
    args = parser.parse_args()
    analysis = load(args.analysis.read_bytes()) if args.analysis else None
    if analysis is not None and not isinstance(analysis, AggregateAnalysis):
        raise ValueError("--analysis requires a current aggregate")
    for record, status, target in records(args.input):
        candidates = {item.resource.identifier for item in record.mention.candidates}
        if (status == "pending" and args.identifier not in candidates) or (status != "pending" and target != args.identifier):
            continue
        print(json.dumps({"identifier": args.identifier, "quote": record.mention.quote, "status": status,
            "lexical_resolution": record.mention.resolution, "source": record.source.model_dump(mode="json"),
            "item_id": record.mention.item_id, "field_pointer": record.mention.field_pointer,
            "range": [record.mention.start, record.mention.end],
            "anchors": [anchor.model_dump(mode="json") for anchor in record.surface.anchors],
            "matching_reasons": [reason.model_dump(mode="json") for candidate in record.mention.candidates
                                 if candidate.resource.identifier == args.identifier for reason in candidate.reasons],
            "native_locations": native_locations(record, analysis) if analysis else []}, ensure_ascii=False))


if __name__ == "__main__":
    main()

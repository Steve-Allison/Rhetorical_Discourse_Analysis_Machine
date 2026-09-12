"""Freeze shared inventory surfaces and measure direct lexical matching."""
import hashlib
import json
from pathlib import Path
import resource
from time import perf_counter

from rdam.concepts import ConceptIndex, link_inventory
from rdam.ingest.contracts.preparation import ContentInventory
from rdam.ingest.contracts.source import SourceArtifact
from rdam.ingest.prepare import prepare_source


def main() -> None:
    root = Path(__file__).parent
    gold_bytes = (root / "gold.json").read_bytes()
    if hashlib.sha256(gold_bytes).hexdigest() != (root / "gold.sha256").read_text().strip():
        raise ValueError("gold annotations changed after freezing")
    gold = json.loads(gold_bytes)
    index = ConceptIndex.load()
    passages = []
    for passage in gold["passages"]:
        inventory = ContentInventory.from_preparation(prepare_source(
            SourceArtifact.from_text(passage["text"], source_name=passage["id"])))
        start = perf_counter()
        result = link_inventory(inventory, index)
        elapsed = perf_counter() - start
        if len(result.surfaces) != 1 or result.surfaces[0].text != passage["text"]:
            raise ValueError("evaluation text must be the exact shared surface")
        passages.append({**passage, "inventory": inventory.model_dump(mode="json"),
                         "baseline": result.model_dump(mode="json"), "seconds": elapsed})
    (root / "prepared.json").write_text(json.dumps({"gold_sha256": hashlib.sha256(gold_bytes).hexdigest(),
        "ontology": index.identity.model_dump(mode="json"), "peak_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "passages": passages}, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    main()

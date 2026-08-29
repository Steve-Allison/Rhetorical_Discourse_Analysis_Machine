"""Derive the raw eRST relation inventory from the official GUM train partition."""

import argparse
from collections import Counter
from pathlib import Path

from isanlp_rst.contracts.erst import CorpusPartition, PrivateCorpusVerificationReceipt
from workbench.corpus.erst.corpus import load_gum_corpus_authority
from workbench.corpus.erst.relations import build_raw_relation_inventory
from isanlp_rst.erst.rs4 import RS4Reader


def main() -> None:
    """Persist a text-free train-derived raw relation inventory."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-root", type=Path, required=True)
    parser.add_argument("--corpus-receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    authority = load_gum_corpus_authority(args.corpus_root)
    corpus_receipt = PrivateCorpusVerificationReceipt.model_validate_json(
        args.corpus_receipt.read_text(encoding="utf-8")
    )
    if corpus_receipt.corpus_revision != authority.corpus_revision:
        raise ValueError("private corpus receipt revision does not match split authority")
    train_ids = tuple(
        entry.document_id for entry in authority.entries if entry.partition == CorpusPartition.TRAIN
    )
    counts: Counter[str] = Counter()
    for document_id in train_ids:
        rs4_document = RS4Reader.read_file(
            args.corpus_root / "rst" / "rstweb" / f"{document_id}.rs4"
        )
        counts.update(edge.relname for edge in rs4_document.secedges)
    inventory = build_raw_relation_inventory(
        counts,
        corpus_revision=authority.corpus_revision,
        source_fingerprint=corpus_receipt.corpus_root_fingerprint,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(inventory.model_dump_json(indent=2), encoding="utf-8")
    print(
        f"raw_relations={len(inventory.labels)} train_edges={inventory.edge_count} "
        f"inventory_sha256={inventory.inventory_sha256} output={args.output.name}"
    )


if __name__ == "__main__":
    main()

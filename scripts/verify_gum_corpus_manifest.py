"""Verify a private pinned GUM checkout without serializing corpus text."""

import argparse
import hashlib
from pathlib import Path

from isanlp_rst.contracts.erst import (
    CandidateIdentityProbe,
    CorpusPartition,
    CorpusSourceIdentity,
    PrivateCorpusVerificationReceipt,
)
from isanlp_rst.erst.candidates import SecondaryEdgeCandidate, generate_secondary_edge_candidates
from isanlp_rst.erst.converter import rs4_to_document_and_analysis
from offline_workbench.corpus.erst.corpus import load_gum_corpus_authority
from isanlp_rst.erst.rs4 import RS4Reader
from offline_workbench.corpus.erst.sampling import candidate_identity_sha256


def _root_fingerprint(revision: str, sources: tuple[CorpusSourceIdentity, ...]) -> str:
    digest = hashlib.sha256(revision.encode())
    for source in sources:
        digest.update(b"\0")
        digest.update(source.source_path.encode())
        digest.update(b"\0")
        digest.update(source.source_sha256.encode())
    return digest.hexdigest()


def _generate_candidates(source_bytes: bytes, document_id: str) -> tuple[SecondaryEdgeCandidate, ...]:
    rs4_document = RS4Reader.read_string(source_bytes.decode("utf-8"))
    document, analysis = rs4_to_document_and_analysis(rs4_document, document_id=document_id)
    return generate_secondary_edge_candidates(document, analysis)


def verify_private_gum_corpus(corpus_root: Path | str) -> PrivateCorpusVerificationReceipt:
    """Verify exact source coverage, disjoint hashes, and candidate determinism probes."""

    root = Path(corpus_root)
    authority = load_gum_corpus_authority(root)
    rst_root = root / "rst" / "rstweb"
    source_paths = tuple(sorted(rst_root.glob("*.rs4")))
    expected_ids = {entry.document_id for entry in authority.entries}
    observed_ids = {source.stem for source in source_paths}
    if observed_ids != expected_ids:
        raise ValueError(
            "private GUM source IDs do not match authority: "
            f"missing={len(expected_ids - observed_ids)}, unexpected={len(observed_ids - expected_ids)}"
        )
    authority_by_id = {entry.document_id: entry for entry in authority.entries}
    sources: list[CorpusSourceIdentity] = []
    source_bytes_by_id: dict[str, bytes] = {}
    for source_path in source_paths:
        if source_path.is_symlink():
            raise ValueError("private GUM source verification rejects symbolic links")
        source_bytes = source_path.read_bytes()
        source_bytes_by_id[source_path.stem] = source_bytes
        authority_entry = authority_by_id[source_path.stem]
        sources.append(
            CorpusSourceIdentity(
                document_id=source_path.stem,
                source_path=source_path.relative_to(root).as_posix(),
                source_sha256=hashlib.sha256(source_bytes).hexdigest(),
                partition=authority_entry.partition,
                license_class=authority_entry.license_class,
            )
        )
    source_tuple = tuple(sources)

    probes: list[CandidateIdentityProbe] = []
    for partition in CorpusPartition:
        probe_source = min(
            (source for source in source_tuple if source.partition == partition),
            key=lambda source: source.document_id,
        )
        source_bytes = source_bytes_by_id[probe_source.document_id]

        first = _generate_candidates(source_bytes, probe_source.document_id)
        second = _generate_candidates(source_bytes, probe_source.document_id)
        first_hash = candidate_identity_sha256(first)
        if first_hash != candidate_identity_sha256(second):
            raise RuntimeError("candidate identities changed across identical private-corpus inputs")
        probes.append(
            CandidateIdentityProbe(
                document_id=probe_source.document_id,
                partition=partition,
                candidate_count=len(first),
                candidate_identity_sha256=first_hash,
            )
        )

    return PrivateCorpusVerificationReceipt(
        corpus_revision=authority.corpus_revision,
        authority_sha256=authority.authority_sha256,
        corpus_root_fingerprint=_root_fingerprint(authority.corpus_revision, source_tuple),
        sources=source_tuple,
        partition_counts={
            partition: sum(source.partition == partition for source in source_tuple)
            for partition in CorpusPartition
        },
        candidate_probes=tuple(probes),
        succeeded=True,
    )


def main() -> None:
    """Write the private, text-free verification receipt to an explicit local path."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    receipt = verify_private_gum_corpus(args.corpus_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(receipt.model_dump_json(indent=2), encoding="utf-8")
    print(
        f"verified_sources={len(receipt.sources)} "
        f"receipt_sha256={receipt.receipt_sha256} output={args.output.name}"
    )


if __name__ == "__main__":
    main()

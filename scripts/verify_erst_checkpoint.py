"""Fail-closed clean-process verifier for an eRST completion bundle."""

import argparse
from pathlib import Path

from isanlp_rst.contracts import (
    ErstCheckpointVerificationReceipt,
    analysis_from_json,
)
from isanlp_rst.erst.checkpoint import load_erst_checkpoint_bundle


def verify_checkpoint(
    checkpoint: Path | str,
    *,
    device: str = "cpu",
) -> ErstCheckpointVerificationReceipt:
    """Strict-reload a bundle, run its test vector, and emit a typed receipt."""

    loaded = load_erst_checkpoint_bundle(checkpoint, device=device, verify_test_vector=True)
    expected = analysis_from_json(loaded.test_vector.expected_analysis_json)
    raw_relations = tuple(sorted({edge.relation_raw for edge in expected.secondary_edges}))
    return ErstCheckpointVerificationReceipt(
        manifest_sha256=loaded.manifest.manifest_sha256,
        device=str(loaded.scorer.dev),
        signal_count=len(expected.signals),
        secondary_edge_count=len(expected.secondary_edges),
        raw_relations=raw_relations,
        verified=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkpoint", type=Path)
    parser.add_argument("--device", default="cpu", choices=("cpu", "mps", "cuda"))
    args = parser.parse_args()
    receipt = verify_checkpoint(args.checkpoint, device=args.device)
    print(receipt.model_dump_json())


if __name__ == "__main__":
    main()

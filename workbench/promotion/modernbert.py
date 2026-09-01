"""Promotion tool for Pure Transformer ModernBERT discourse parser releases."""

import argparse
import hashlib
from pathlib import Path, PurePosixPath

from isanlp_rst.model_authority import MODERNBERT_BASE_MODEL_ID, MODERNBERT_BASE_REVISION
from isanlp_rst.model_loading.release import (
    MODEL_RELEASE_MANIFEST,
)
from workbench.promotion.promote import (
    promote_model_release,
    write_candidate_manifest,
)

EVIDENCE_UNAVAILABLE_REASON = "no training_receipt.json in the candidate and no evaluation evidence supplied"


def prepare_and_promote_modernbert(
    candidate_dir: Path,
    store_dir: Path,
    release_id: str | None = None,
    evaluation_evidence: str | None = None,
) -> Path:
    """Validate, manifest, and atomically promote a trained ModernBERT candidate."""
    candidate_dir = candidate_dir.resolve()
    if not candidate_dir.is_dir():
        raise FileNotFoundError(f"Candidate directory does not exist: {candidate_dir}")

    # Verify required candidate files exist
    config_path = candidate_dir / "config.json"
    weights_path = candidate_dir / "model.safetensors"
    inventory_path = candidate_dir / "relation_inventory.json"

    if not config_path.is_file():
        raise FileNotFoundError(f"Missing config.json in {candidate_dir}")
    if not weights_path.is_file():
        raise FileNotFoundError(f"Missing model.safetensors in {candidate_dir}")
    if not inventory_path.is_file():
        raise FileNotFoundError(f"Missing relation_inventory.json in {candidate_dir}")

    # Build roles dictionary
    roles: dict[PurePosixPath, str] = {
        PurePosixPath("config.json"): "encoder_config",
        PurePosixPath("model.safetensors"): "parser_state",
        PurePosixPath("relation_inventory.json"): "relation_inventory",
    }

    # Add tokenizer files
    for tok_file in candidate_dir.glob("tokenizer*"):
        if tok_file.is_file():
            roles[PurePosixPath(tok_file.name)] = "tokenizer"
    for tok_file in candidate_dir.glob("special_tokens_map.json"):
        if tok_file.is_file():
            roles[PurePosixPath(tok_file.name)] = "tokenizer"

    # Derive deterministic release ID if not provided
    if not release_id:
        weights_hash = hashlib.sha256(weights_path.read_bytes()).hexdigest()[:12]
        release_id = f"modernbert-v1-{weights_hash}"

    # The manifest is derived from the candidate's bytes; regenerate rather than keep a
    # stale one that would fail the inventory check.
    manifest_path = candidate_dir / MODEL_RELEASE_MANIFEST
    if manifest_path.exists():
        manifest_path.unlink()

    # Evaluation evidence is the training receipt verbatim, or an explicit statement that
    # none was supplied. It is never a fabricated verification claim: a release without
    # evidence declares `evaluation_unavailable_reason`, which the manifest contract
    # requires in exactly that case (isanlp_rst.model_loading.release).
    receipt_file = candidate_dir / "training_receipt.json"
    evaluation_unavailable_reason: str | None = None
    if evaluation_evidence is None:
        if receipt_file.is_file():
            evaluation_evidence = receipt_file.read_text(encoding="utf-8")
        else:
            evaluation_unavailable_reason = EVIDENCE_UNAVAILABLE_REASON
    if receipt_file.is_file():
        # The receipt is not a runtime member of a ModernBERT release (release.py restricts
        # roles), so it cannot stay inside the candidate — but it is the only structured
        # quality record, so it is preserved beside the candidate, never deleted.
        receipt_file.replace(candidate_dir.with_name(f"{candidate_dir.name}.training_receipt.json"))

    write_candidate_manifest(
        candidate=candidate_dir,
        release_id=release_id,
        model_task="rst_tree_parsing",
        architecture="PureTransformerParsingNet",
        runtime_contract="isanlp_rst.parser/modernbert-v1",
        compatibility_range=">=5.0.0,<6.0.0",
        source_model_identity=MODERNBERT_BASE_MODEL_ID,
        source_revision=MODERNBERT_BASE_REVISION,
        licence="Apache-2.0",
        use_restrictions=(),
        roles=roles,
        evaluation_evidence=evaluation_evidence,
        evaluation_unavailable_reason=evaluation_unavailable_reason,
    )

    receipt = promote_model_release(
        candidate=candidate_dir,
        store=store_dir,
    )
    return Path(receipt.release_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Promote ModernBERT parser candidate to local store")
    parser.add_argument("--candidate-dir", type=Path, default=Path("models/modernbert_v1"))
    parser.add_argument(
        "--store-dir",
        type=Path,
        default=Path.home() / ".cache/isanlp_rst/model-releases",
    )
    parser.add_argument("--release-id", default=None)
    args = parser.parse_args()

    promoted = prepare_and_promote_modernbert(
        candidate_dir=args.candidate_dir,
        store_dir=args.store_dir,
        release_id=args.release_id,
    )
    print(f"Successfully promoted release to: {promoted}")


if __name__ == "__main__":
    main()

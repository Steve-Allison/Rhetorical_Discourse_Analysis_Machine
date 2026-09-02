"""Promotion tool for Pure Transformer ModernBERT discourse parser releases.

A candidate enters the immutable model store only through a ``PromotionDecision`` whose
outcome is ``promote`` or ``replace`` (006 promotion-evidence contract). The decision is
the release's evaluation evidence: its canonical JSON is written into the manifest's
``evaluation_evidence`` and published beside the release as ``<release_id>.promotion.json``
so the production adapter can read it without importing the workbench.
"""

import argparse
import hashlib
from pathlib import Path, PurePosixPath

from workbench.training.modern.authority import MODERNBERT_BASE_MODEL_ID, MODERNBERT_BASE_REVISION
from rdam.rst.model_loading.release import MODEL_RELEASE_MANIFEST
from rdam.frameworks import Technique
from rdam.promotion import PromotionDecision, PromotionOutcome, load_decision, serialize_decision
from workbench.promotion.decision import publish_decision, record_decision
from workbench.promotion.promote import promote_model_release, write_candidate_manifest

_ADMITTING_OUTCOMES = frozenset({PromotionOutcome.PROMOTE, PromotionOutcome.REPLACE})


def prepare_and_promote_modernbert(
    candidate_dir: Path,
    store_dir: Path,
    decision: PromotionDecision,
    release_id: str | None = None,
) -> Path:
    """Validate, manifest, and atomically promote a trained ModernBERT candidate under its decision."""

    candidate_dir = candidate_dir.resolve()
    if not candidate_dir.is_dir():
        raise FileNotFoundError(f"Candidate directory does not exist: {candidate_dir}")

    config_path = candidate_dir / "config.json"
    weights_path = candidate_dir / "model.safetensors"
    inventory_path = candidate_dir / "relation_inventory.json"
    if not config_path.is_file():
        raise FileNotFoundError(f"Missing config.json in {candidate_dir}")
    if not weights_path.is_file():
        raise FileNotFoundError(f"Missing model.safetensors in {candidate_dir}")
    if not inventory_path.is_file():
        raise FileNotFoundError(f"Missing relation_inventory.json in {candidate_dir}")

    weights_sha256 = hashlib.sha256(weights_path.read_bytes()).hexdigest()
    if decision.candidate.technique is not Technique.RST:
        raise ValueError(f"decision is for {decision.candidate.technique.value}, not the RST boundary")
    if decision.outcome not in _ADMITTING_OUTCOMES:
        raise ValueError(f"decision outcome is {decision.outcome.value!r}; only promote or replace admit a candidate")
    if decision.candidate.artifact_identity.hex_digest != weights_sha256:
        raise ValueError("decision names a different artifact than the candidate's model.safetensors")
    if not release_id:
        release_id = f"modernbert-v1-{weights_sha256[:12]}"
    if decision.candidate.candidate_id != release_id:
        raise ValueError(f"decision candidate_id {decision.candidate.candidate_id!r} must equal the release id {release_id!r}")

    roles: dict[PurePosixPath, str] = {
        PurePosixPath("config.json"): "encoder_config",
        PurePosixPath("model.safetensors"): "parser_state",
        PurePosixPath("relation_inventory.json"): "relation_inventory",
    }
    for tok_file in candidate_dir.glob("tokenizer*"):
        if tok_file.is_file():
            roles[PurePosixPath(tok_file.name)] = "tokenizer"
    for tok_file in candidate_dir.glob("special_tokens_map.json"):
        if tok_file.is_file():
            roles[PurePosixPath(tok_file.name)] = "tokenizer"

    # The manifest is derived from the candidate's bytes; regenerate rather than keep a
    # stale one that would fail the inventory check.
    manifest_path = candidate_dir / MODEL_RELEASE_MANIFEST
    if manifest_path.exists():
        manifest_path.unlink()

    # A training receipt is not a runtime member of a ModernBERT release (release.py
    # restricts roles) and is the structured record the decision's provenance cites, so it
    # is preserved beside the candidate, never deleted.
    receipt_file = candidate_dir / "training_receipt.json"
    if receipt_file.is_file():
        receipt_file.replace(candidate_dir.with_name(f"{candidate_dir.name}.training_receipt.json"))

    write_candidate_manifest(
        candidate=candidate_dir,
        release_id=release_id,
        model_task="rst_tree_parsing",
        architecture="PureTransformerParsingNet",
        runtime_contract="isanlp_rst.parser/modernbert-v1",
        compatibility_range=">=5.0.0,<7.0.0",
        source_model_identity=MODERNBERT_BASE_MODEL_ID,
        source_revision=MODERNBERT_BASE_REVISION,
        licence=decision.licensing.licence,
        use_restrictions=() if decision.licensing.permits_intended_use else (decision.licensing.decision_note,),
        roles=roles,
        evaluation_evidence=serialize_decision(decision).decode("utf-8"),
    )

    receipt = promote_model_release(candidate=candidate_dir, store=store_dir)
    record_decision(decision)
    publish_decision(decision, Path(store_dir))
    return Path(receipt.release_path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--candidate-dir", type=Path, default=Path("workbench/experiments/modernbert_v1"))
    parser.add_argument("--store-dir", type=Path, default=Path("workbench/experiments/model-releases"))
    parser.add_argument("--decision", type=Path, required=True, help="PromotionDecision JSON with outcome promote or replace")
    parser.add_argument("--release-id", default=None)
    args = parser.parse_args()
    promoted = prepare_and_promote_modernbert(
        candidate_dir=args.candidate_dir,
        store_dir=args.store_dir,
        decision=load_decision(args.decision.read_bytes()),
        release_id=args.release_id,
    )
    print(f"Successfully promoted release to: {promoted}")


if __name__ == "__main__":
    main()

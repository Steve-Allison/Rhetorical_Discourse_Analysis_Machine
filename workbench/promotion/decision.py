"""Record and publish PromotionDecisions — the workbench side of the promotion system.

The decision *contract* is ``rdam.promotion`` (production, so a promoted artifact's
sidecar can be read without the workbench). This module owns the workbench ledger of
decisions under ``workbench/promotions/<technique>/`` (append-only, one canonical JSON
file per decision) and publishes a decision beside a model-store release as
``<store>/<release_id>.promotion.json`` so the production adapter can see it.

Run: ``pixi run promotion-record --file <decision.json> [--publish-to <store>]``
"""

import argparse
from collections.abc import Iterator
from pathlib import Path

from rdam.frameworks import Technique
from rdam.promotion import PromotionDecision, load_decision, serialize_decision, sidecar_path

PROMOTIONS_ROOT = Path("workbench/promotions")


def decision_path(root: Path, decision: PromotionDecision) -> Path:
    return Path(root) / decision.candidate.technique.value / f"{decision.decision_id}.json"


def record_decision(decision: PromotionDecision, root: Path = PROMOTIONS_ROOT) -> Path:
    """Append a decision to the ledger. Re-recording identical bytes is a no-op; a different record under the same id is refused."""

    path = decision_path(root, decision)
    payload = serialize_decision(decision) + b"\n"
    if path.exists():
        if path.read_bytes() == payload:
            return path
        raise FileExistsError(f"decision {decision.decision_id!r} already recorded with different content: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_bytes(payload)
    temporary.replace(path)
    return path


def iter_decisions(root: Path = PROMOTIONS_ROOT, technique: Technique | None = None) -> Iterator[PromotionDecision]:
    """Every recorded decision, oldest first."""

    base = Path(root)
    directories = [base / technique.value] if technique is not None else sorted(path for path in base.iterdir() if path.is_dir()) if base.is_dir() else []
    decisions = [load_decision(path.read_bytes()) for directory in directories if directory.is_dir() for path in sorted(directory.glob("*.json"))]
    yield from sorted(decisions, key=lambda item: item.decided_at)


def latest_decision(candidate_id: str, root: Path = PROMOTIONS_ROOT, technique: Technique | None = None) -> PromotionDecision | None:
    """The most recent decision about one candidate."""

    matching = [item for item in iter_decisions(root, technique) if item.candidate.candidate_id == candidate_id]
    return matching[-1] if matching else None


def publish_decision(decision: PromotionDecision, store: Path) -> Path:
    """Place the decision beside its release in the model store, replacing an older sidecar."""

    path = sidecar_path(Path(store), decision.candidate.candidate_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_bytes(serialize_decision(decision) + b"\n")
    temporary.replace(path)
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--file", type=Path, required=True, help="a PromotionDecision as JSON")
    parser.add_argument("--root", type=Path, default=PROMOTIONS_ROOT)
    parser.add_argument("--publish-to", type=Path, help="model store to publish the decision sidecar into")
    args = parser.parse_args()
    decision = load_decision(args.file.read_bytes())
    recorded = record_decision(decision, args.root)
    print(f"recorded {decision.outcome.value} for {decision.candidate.candidate_id}: {recorded}")
    for verdict in decision.verdicts():
        status = "admissible" if verdict.admissible else "deficient: " + "; ".join(verdict.deficiencies)
        print(f"  {verdict.evidence_class.value}: {status}")
    if args.publish_to is not None:
        print(f"published: {publish_decision(decision, args.publish_to)}")
    return 0


__all__ = ["PROMOTIONS_ROOT", "decision_path", "iter_decisions", "latest_decision", "publish_decision", "record_decision"]


if __name__ == "__main__":
    raise SystemExit(main())

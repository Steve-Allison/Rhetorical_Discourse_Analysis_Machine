"""Resolve or fail closed on the exact published eRST baseline authorities."""

import argparse
from datetime import date
import hashlib
from pathlib import Path
import re
import subprocess

from isanlp_rst.contracts.erst import CorpusLicenseClass, CorpusPartition
from isanlp_rst.contracts.research import (
    AuthoritySearchEvidence,
    BaselineAuthorityBlocker,
    BaselineCorpusSource,
    ErstBaselineAuthorityReceipt,
    ModelRevisionAuthority,
    ResearchArtifact,
)

GUM_V9_TAG = "V9.2.0"
GUM_V9_REVISION = "3b0ab7d11911be1695e4dacadb28a7a1df230bdb"
GUM_V9_TREE = "a97dcf9cbed8cefdd260e4226145a6f9cf0ecc4f"
PAPER_SHA256 = "f04807264324631d1ad79aade3529215afc7729cf874ef311edf5094ab52a6da"
BASELINE_CODE_REVISION = "c56e9f68cd1e2f0a9a9e3e524692b60e17830183"
BASELINE_CODE_SHA256 = "d1f1f3be391c17f1bc2aa59cc339fcfba26e68ed7500c6d44c0b84e6257a1a1e"
ELECTRA_REVISION = "1ae76a97c7e84a4e640876a07453fccd636f0667"

_PARTITION_HEADING = re.compile(r"^##\s+(train|dev|test)\s*$")
_DOCUMENT_BULLET = re.compile(r"^\s*\*\s+(GUM_[a-z0-9]+_[a-z0-9]+)\s*$")
_CC_BY_GENRES = frozenset({"academic", "interview", "news"})
_CC_BY_SA_GENRES = frozenset({"bio", "voyage"})
_NON_COMMERCIAL_GENRES = frozenset({"fiction", "reddit", "whow"})


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _git_value(root: Path, argument: str) -> str:
    completed = subprocess.run(
        ("git", "-C", str(root), "rev-parse", argument),
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return completed.stdout.strip()


def _license_class(document_id: str) -> CorpusLicenseClass:
    genre = document_id.split("_", maxsplit=2)[1]
    if genre in _CC_BY_GENRES:
        return CorpusLicenseClass.CC_BY
    if genre in _CC_BY_SA_GENRES:
        return CorpusLicenseClass.CC_BY_SA
    if genre in _NON_COMMERCIAL_GENRES:
        return CorpusLicenseClass.NON_COMMERCIAL
    return CorpusLicenseClass.RESTRICTED


def _partition_ids(splits_text: str) -> dict[str, CorpusPartition]:
    current: CorpusPartition | None = None
    assignments: dict[str, CorpusPartition] = {}
    for line in splits_text.splitlines():
        if match := _PARTITION_HEADING.fullmatch(line):
            current = CorpusPartition(match.group(1))
            continue
        if match := _DOCUMENT_BULLET.fullmatch(line):
            if current is None:
                raise ValueError("GUM V9 splits name a document before a partition heading")
            document_id = match.group(1)
            if document_id in assignments:
                raise ValueError(f"duplicate GUM V9 split assignment: {document_id}")
            assignments[document_id] = current
    return assignments


def resolve_authority(
    gum_v9_root: Path,
    baseline_code_path: Path,
    *,
    assessed_on: date,
) -> ErstBaselineAuthorityReceipt:
    """Build a complete text-free receipt and refuse to infer the missing scorer."""

    revision = _git_value(gum_v9_root, "HEAD")
    tree = _git_value(gum_v9_root, "HEAD^{tree}")
    if revision != GUM_V9_REVISION or tree != GUM_V9_TREE:
        raise ValueError("corpus checkout is not the immutable GUM V9.2.0 tag")

    splits_path = gum_v9_root / "splits.md"
    license_path = gum_v9_root / "LICENSE.txt"
    splits_text = splits_path.read_text(encoding="utf-8")
    license_text = license_path.read_text(encoding="utf-8")
    required_license_markers = (
        "All annotations are licensed under the Creative Commons Attribution (CC-BY) version 4.0",
        "reddit: Data available from reddit for non-commercial use only",
        "WikiHow:    http://creativecommons.org/licenses/by-nc-sa/3.0/",
        "Fiction:    http://creativecommons.org/licenses/by-nc-sa/3.0/",
    )
    if any(marker not in license_text for marker in required_license_markers):
        raise ValueError("GUM V9 licence inventory is missing a required mixed-licence marker")

    assignments = _partition_ids(splits_text)
    source_root = gum_v9_root / "rst" / "rstweb"
    source_paths = tuple(sorted(source_root.glob("*.rs4")))
    source_ids = {source.stem for source in source_paths}
    if source_ids != set(assignments):
        raise ValueError("GUM V9 RS4 sources do not exactly match the official split authority")
    sources = tuple(
        BaselineCorpusSource(
            document_id=source.stem,
            source_path=source.relative_to(gum_v9_root).as_posix(),
            source_sha256=_sha256(source),
            partition=assignments[source.stem],
            license_class=_license_class(source.stem),
        )
        for source in source_paths
    )

    baseline_code_sha256 = _sha256(baseline_code_path)
    if baseline_code_sha256 != BASELINE_CODE_SHA256:
        raise ValueError("baseline code does not match the immutable released conn2edge.py")

    checked_surfaces = (
        ("https://aclanthology.org/2025.cl-1.3/", "paper PDF and metadata", "release claim but no artifact URL"),
        ("https://submissions.cljournal.org/index.php/cljournal/article/view/2573", "all public OJS galleys", "paper galleys only; no supplement"),
        ("https://gucorpling.org/erst/", "complete eRST project page", "guidelines and corpus browser; no scorer"),
        ("https://github.com/amir-zeldes/gum", "all branches, releases, and complete repository tree", "baseline code found; no official graph scorer or checkpoint"),
        ("https://github.com/amir-zeldes/rst2dep", "complete repository tree", "no official eRST graph scorer"),
        ("https://github.com/amir-zeldes/rstWeb", "complete repository tree", "no official eRST graph scorer"),
        ("https://github.com/amir-zeldes/RSTParser", "complete repository tree", "no official eRST graph scorer"),
        ("https://github.com/t-aoyam/gum", "all public author-fork branches", "fork predates eRST release"),
        ("https://github.com/lgessler/gum", "all public author-fork branches", "fork predates eRST release"),
    )

    return ErstBaselineAuthorityReceipt(
        assessed_on=assessed_on,
        paper=ResearchArtifact(
            name="eRST: A Signaled Graph Theory of Discourse Relations and Organization",
            url="https://aclanthology.org/2025.cl-1.3.pdf",
            sha256=PAPER_SHA256,
            license="CC-BY-4.0",
        ),
        baseline_code=ResearchArtifact(
            name="GUM conn2edge.py initial public release",
            url=(
                "https://github.com/amir-zeldes/gum/blob/"
                f"{BASELINE_CODE_REVISION}/_build/utils/conn2edge.py"
            ),
            revision=BASELINE_CODE_REVISION,
            sha256=baseline_code_sha256,
            license="not stated for code by repository licence inventory",
        ),
        baseline_model=ModelRevisionAuthority(
            model_id="google/electra-base-discriminator",
            revision=ELECTRA_REVISION,
            license="Apache-2.0",
        ),
        corpus_revision=revision,
        corpus_tree=tree,
        splits_sha256=_sha256(splits_path),
        license_inventory_sha256=_sha256(license_path),
        sources=sources,
        partition_counts={
            partition: sum(source.partition == partition for source in sources)
            for partition in (CorpusPartition.TRAIN, CorpusPartition.DEV, CorpusPartition.TEST)
        },
        official_scorer=None,
        scorer_parity_receipt_sha256=None,
        released_checkpoint=None,
        released_environment_pins=(),
        searched_surfaces=tuple(
            AuthoritySearchEvidence(
                surface_url=url,
                checked_resource=resource,
                result=result,
                checked_on=assessed_on,
            )
            for url, resource, result in checked_surfaces
        ),
        discrepancies=(
            "The paper claims a released scorer, but no scorer artifact or artifact URL is present on any inspected public release surface.",
            "The released baseline script evaluates set equality rather than the paper's Span, direction, Relation, and Full graph metrics.",
            "The released repository does not contain the referenced association checkpoint or generated train/dev/test tables.",
            "The released environment does not declare Flair or immutable PyTorch, Transformers, Flair, and model revisions.",
            "The GUM repository licence inventory governs corpus text and annotations but states no licence for conn2edge.py.",
        ),
        blockers=(
            BaselineAuthorityBlocker.OFFICIAL_SCORER_UNAVAILABLE,
            BaselineAuthorityBlocker.SCORER_PARITY_UNVERIFIED,
        ),
        ready_for_reproduction=False,
    )


def main() -> None:
    """Write the authority receipt; unresolved status is a successful diagnostic result."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gum-v9-root", type=Path, required=True)
    parser.add_argument("--baseline-code", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--assessed-on", type=date.fromisoformat, required=True)
    args = parser.parse_args()

    receipt = resolve_authority(
        args.gum_v9_root,
        args.baseline_code,
        assessed_on=args.assessed_on,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(receipt.model_dump_json(indent=2) + "\n", encoding="utf-8")
    print(
        f"ready_for_reproduction={str(receipt.ready_for_reproduction).lower()} "
        f"sources={len(receipt.sources)} receipt_sha256={receipt.receipt_sha256}"
    )


if __name__ == "__main__":
    main()

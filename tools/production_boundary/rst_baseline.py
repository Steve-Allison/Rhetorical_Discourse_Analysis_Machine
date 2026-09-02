"""Capture and compare the RST public-contract baseline across migration.

006 rst-preservation contract §Equivalence procedure: before migration, persist the
serialized contract outputs for representative inputs across all six declared source
forms; after migration, recapture with identical commands and compare. Semantic digests
exclude execution evidence (ids, durations, device), so equality of digests is equality
of meaning; the full serialized records are kept beside them as the auditable artifact.

    pixi run rst-baseline capture --output specs/010-repository-migration/evidence/baseline
    pixi run rst-baseline compare --baseline specs/010-repository-migration/evidence/baseline
"""

import argparse
import json
from pathlib import Path
import tempfile

from isanlp_rst import Parser
from isanlp_rst.ingest import (
    ProductionIngestor,
    SourceArtifact,
    SourceForm,
    describe_capabilities,
    serialize_contract,
)
from tools.production_boundary.installed_acceptance import _archive_bytes

TEXT = "Because it rained, the match stopped. The crowd left. Nobody complained, though some had travelled far."
EDUS = ("Because it rained, the match stopped.", "The crowd left.", "Nobody complained,", "though some had travelled far.")
DOCLANG_ARCHIVE_DOCUMENT = b"<doclang><text>Baseline archive acceptance.</text></doclang>"
FIXTURES = {
    SourceForm.MARKDOWN: Path("tests/fixtures/markdown/minimal.md"),
    SourceForm.DOCLING_JSON: Path("tests/fixtures/docling/markdown.docling.json"),
    SourceForm.DOCLANG_XML: Path("tests/fixtures/doclang/ok_comprehensive.dclg"),
}


def _artifacts() -> dict[str, SourceArtifact]:
    artifacts: dict[str, SourceArtifact] = {
        SourceForm.TEXT.value: SourceArtifact.from_text(TEXT, source_name="baseline.txt"),
        SourceForm.EDUS.value: SourceArtifact.from_edus(EDUS, source_name="baseline.edus"),
        SourceForm.DOCLANG_ARCHIVE.value: SourceArtifact.from_bytes(
            _archive_bytes(DOCLANG_ARCHIVE_DOCUMENT),
            source_form=SourceForm.DOCLANG_ARCHIVE,
            source_name="baseline.dclx",
            media_type="application/vnd.doclang.archive+zip",
        ),
    }
    for form, path in FIXTURES.items():
        artifacts[form.value] = SourceArtifact.from_path(path, source_form=form)
    return artifacts


def _digest(record: object) -> str:
    digest = getattr(record, "semantic_digest", None)
    hex_digest = getattr(digest, "hex_digest", None)
    if not isinstance(hex_digest, str):
        raise ValueError("record has no semantic digest")
    return hex_digest


def capture(output: Path, *, store: Path | None, release_id: str | None, device: str) -> dict[str, str]:
    """Write one serialized record per operation and return their semantic digests."""

    output.mkdir(parents=True, exist_ok=True)
    digests: dict[str, str] = {}
    capabilities = describe_capabilities()
    (output / "capabilities.json").write_bytes(serialize_contract(capabilities))
    digests["capabilities"] = _digest(capabilities)
    ingestor = ProductionIngestor()
    for name, artifact in _artifacts().items():
        prepared = ingestor.prepare(artifact)
        (output / f"prepare-{name}.json").write_bytes(serialize_contract(prepared))
        digests[f"prepare-{name}"] = _digest(prepared)
    if store is not None and release_id is not None:
        parser = Parser.from_model_release(store, release_id, family="modernbert", device=device)
        analysing = ProductionIngestor(parser=parser)
        for name in (SourceForm.TEXT.value, SourceForm.EDUS.value):
            outcome = analysing.analyse(_artifacts()[name])
            (output / f"analyse-{name}.json").write_bytes(serialize_contract(outcome))
            digests[f"analyse-{name}"] = _digest(outcome)
    (output / "digests.json").write_text(json.dumps(digests, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return digests


def compare(baseline: Path, *, store: Path | None, release_id: str | None, device: str) -> dict[str, tuple[str, str]]:
    """Recapture into a scratch directory and return every digest that differs from the baseline."""

    expected = json.loads((baseline / "digests.json").read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory(prefix="rst-baseline-compare-") as scratch:
        actual = capture(Path(scratch), store=store, release_id=release_id, device=device)
    names = sorted(set(expected) | set(actual))
    return {name: (expected.get(name, "<absent>"), actual.get(name, "<absent>")) for name in names if expected.get(name) != actual.get(name)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("mode", choices=("capture", "compare"))
    parser.add_argument("--output", type=Path, help="capture: directory to write")
    parser.add_argument("--baseline", type=Path, help="compare: directory written by capture")
    parser.add_argument("--store", type=Path, default=Path("models/model-releases"))
    parser.add_argument("--release-id", default="modernbert-v1-a52b70fbc1a3")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--no-analysis", action="store_true", help="preparation and capabilities only; no model load")
    args = parser.parse_args()
    store = None if args.no_analysis else args.store
    release_id = None if args.no_analysis else args.release_id
    if args.mode == "capture":
        if args.output is None:
            raise SystemExit("capture requires --output")
        digests = capture(args.output, store=store, release_id=release_id, device=args.device)
        print(json.dumps(digests, indent=2, sort_keys=True))
        return 0
    if args.baseline is None:
        raise SystemExit("compare requires --baseline")
    differences = compare(args.baseline, store=store, release_id=release_id, device=args.device)
    if differences:
        print(json.dumps({"equivalent": False, "differences": differences}, indent=2, sort_keys=True))
        return 1
    print(json.dumps({"equivalent": True, "baseline": str(args.baseline)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Capture and compare the RST public-contract baseline across migration.

006 rst-preservation contract §Equivalence procedure: before migration, persist the
serialized contract outputs for representative inputs across all six declared source
forms; after migration, recapture with identical commands and compare. Semantic digests
exclude execution evidence (ids, durations, device), so equality of digests is equality
of meaning; the full serialized records are kept beside them as the auditable artifact.

When a digest differs, the two records are diffed field by field and every difference is
classified before a verdict is given:

* ``execution`` — execution evidence (ids, durations, timings, clock, git revision); never semantic.
* ``package_identity`` — the package's own version, and its name where a record names
  the package as the validator of a built-in source form.
* ``package_source_identity`` — digests and sizes of the package's *own source files*
  recorded as packaged-component identities, and the digests derived from them. These
  change whenever the package's source bytes change, as they do in a rename.
* ``derived_digest`` — a digest computed from other fields of the same record.
* ``analytical`` — everything else: prepared text, segments, inventory, nodes, edges,
  anchors, validation. Any analytical difference fails the comparison.

A release that renames or re-versions the distribution cannot be byte-identical in the
first three classes; it is still required to be identical in the last.

    pixi run rst-baseline capture --output specs/010-repository-migration/evidence/baseline
    pixi run rst-baseline compare --baseline specs/010-repository-migration/evidence/baseline
"""

import argparse
from dataclasses import asdict, dataclass
from enum import StrEnum
import json
from pathlib import Path
import tempfile
from typing import Any

from packaging.version import InvalidVersion, Version

from rdam.rst import Parser
from rdam.rst._version import PACKAGE_NAME
from rdam.rst.ingest import (
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
# Fields whose value is the package's own version wherever they occur in a record.
_PACKAGE_VERSION_FIELDS = frozenset({"package_version", "software_version"})
# Fields that hold a value computed from the git checkout or the clock, never from the analysis.
_PROVENANCE_CLOCK_FIELDS = frozenset({"source_revision", "timestamp"})
# Containers whose ``hex_digest`` child is computed from sibling fields of the same record.
_DERIVED_DIGEST_CONTAINERS = frozenset(
    {
        "semantic_digest",
        "schema_identity",
        "cache_request_identity",
        "preparation_identity",
        "declared_identity",
        "manifest_identity",
        "producing_component_identity",
    }
)
# Packaged deterministic components record the package's own source files as their identity
# (Verified 2026-09-02 at rdam/rst/ingest/parser_result.py:_packaged_component — role
# ``provider_code``, release id ``<package>-<version>``).
_PACKAGED_COMPONENT_ROLE = "provider_code"
_PACKAGED_COMPONENT_ARCHITECTURE = "packaged_deterministic_component"
# Wall-clock measurements the analysis records about itself; never part of its meaning.
_TIMING_CONTAINER = "timing"

type JsonPath = tuple[str, ...]


class DifferenceClass(StrEnum):
    EXECUTION = "execution"
    PACKAGE_IDENTITY = "package_identity"
    PACKAGE_SOURCE_IDENTITY = "package_source_identity"
    DERIVED_DIGEST = "derived_digest"
    ANALYTICAL = "analytical"


@dataclass(frozen=True, slots=True)
class Difference:
    path: str
    baseline: Any
    actual: Any
    classification: DifferenceClass


@dataclass(frozen=True, slots=True)
class RecordComparison:
    baseline_digest: str
    actual_digest: str
    differences: tuple[Difference, ...]

    @property
    def analytically_equivalent(self) -> bool:
        return not any(item.classification is DifferenceClass.ANALYTICAL for item in self.differences)


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


def _flatten(value: Any, path: JsonPath = ()) -> dict[JsonPath, Any]:
    """Every leaf of a JSON value keyed by its path; lists also record their length."""

    if isinstance(value, dict):
        flat: dict[JsonPath, Any] = {}
        for key, item in value.items():
            flat.update(_flatten(item, (*path, str(key))))
        return flat
    if isinstance(value, list):
        flat = {(*path, "$length"): len(value)}
        for index, item in enumerate(value):
            flat.update(_flatten(item, (*path, str(index))))
        return flat
    return {path: value}


def _is_version(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        Version(value)
    except InvalidVersion:
        return False
    return True


def _package_source_digests(flat: dict[JsonPath, Any]) -> frozenset[str]:
    """Every digest that identifies the package's own source files, or a component built from them."""

    digests: set[str] = set()
    for path, value in flat.items():
        if path[-1] == "role" and value == _PACKAGED_COMPONENT_ROLE:
            file_container = path[:-1]
            identity = flat.get((*file_container, "identity", "hex_digest"))
            if isinstance(identity, str):
                digests.add(identity)
            component = file_container[:-2]  # .../files/<n> -> the component identity
            for key in ("manifest_identity",):
                manifest = flat.get((*component, key, "hex_digest"))
                if isinstance(manifest, str):
                    digests.add(manifest)
    return frozenset(digests)


def _is_package_source_path(path: JsonPath, flat: dict[JsonPath, Any]) -> bool:
    """A size or file identity that belongs to a packaged (provider_code) component file."""

    if path[-1] == "size_bytes":
        return flat.get((*path[:-1], "role")) == _PACKAGED_COMPONENT_ROLE
    if path[-2:] == ("identity", "hex_digest"):
        return flat.get((*path[:-2], "role")) == _PACKAGED_COMPONENT_ROLE
    if path[-1] == "release_id":
        # The release id of a packaged deterministic component is ``<package>-<version>``,
        # so it changes with either; the component's architecture marks it on both sides.
        return flat.get((*path[:-1], "architecture")) == _PACKAGED_COMPONENT_ARCHITECTURE
    return False


def classify(path: JsonPath, baseline: dict[JsonPath, Any], actual: dict[JsonPath, Any]) -> DifferenceClass:
    """Name what kind of difference one path carries between the two records."""

    if "execution" in path or _TIMING_CONTAINER in path:
        return DifferenceClass.EXECUTION
    leaf = path[-1]
    if leaf in _PROVENANCE_CLOCK_FIELDS:
        return DifferenceClass.EXECUTION
    if leaf in _PACKAGE_VERSION_FIELDS and _is_version(baseline.get(path)) and _is_version(actual.get(path)):
        return DifferenceClass.PACKAGE_IDENTITY
    if leaf in {"validator_distribution", "validator_version", "upstream_format", "upstream_version"}:
        # The same validator at a different version would be dependency drift; a validator
        # that is a *different* distribution in the two records is the package renamed.
        name_key = "validator_distribution" if leaf.startswith("validator") else "upstream_format"
        name_path = (*path[:-1], name_key)
        if baseline.get(name_path) != actual.get(name_path) and actual.get(name_path) == PACKAGE_NAME:
            return DifferenceClass.PACKAGE_IDENTITY
        return DifferenceClass.ANALYTICAL
    if _is_package_source_path(path, actual) and _is_package_source_path(path, baseline):
        return DifferenceClass.PACKAGE_SOURCE_IDENTITY
    if leaf == "hex_digest":
        before, after = baseline.get(path), actual.get(path)
        if before in _package_source_digests(baseline) and after in _package_source_digests(actual):
            return DifferenceClass.PACKAGE_SOURCE_IDENTITY
        if len(path) >= 2 and path[-2] in _DERIVED_DIGEST_CONTAINERS:
            return DifferenceClass.DERIVED_DIGEST
    return DifferenceClass.ANALYTICAL


def diff_records(baseline_payload: bytes, actual_payload: bytes) -> tuple[Difference, ...]:
    """Every field-level difference between two serialized records, classified."""

    baseline = _flatten(json.loads(baseline_payload))
    actual = _flatten(json.loads(actual_payload))
    differences: list[Difference] = []
    for path in sorted(set(baseline) | set(actual)):
        before = baseline.get(path, "<absent>")
        after = actual.get(path, "<absent>")
        if before == after:
            continue
        differences.append(
            Difference(
                path="/".join(path),
                baseline=before,
                actual=after,
                classification=classify(path, baseline, actual),
            )
        )
    return tuple(differences)


def compare(baseline: Path, *, store: Path | None, release_id: str | None, device: str) -> dict[str, RecordComparison]:
    """Recapture into a scratch directory and compare every record whose digest differs from the baseline."""

    expected = json.loads((baseline / "digests.json").read_text(encoding="utf-8"))
    comparisons: dict[str, RecordComparison] = {}
    with tempfile.TemporaryDirectory(prefix="rst-baseline-compare-") as scratch:
        scratch_path = Path(scratch)
        actual = capture(scratch_path, store=store, release_id=release_id, device=device)
        for name in sorted(set(expected) | set(actual)):
            if expected.get(name) == actual.get(name):
                continue
            baseline_file = baseline / f"{name}.json"
            actual_file = scratch_path / f"{name}.json"
            if not baseline_file.is_file() or not actual_file.is_file():
                comparisons[name] = RecordComparison(
                    baseline_digest=expected.get(name, "<absent>"),
                    actual_digest=actual.get(name, "<absent>"),
                    differences=(
                        Difference(
                            path="<record>",
                            baseline=baseline_file.is_file(),
                            actual=actual_file.is_file(),
                            classification=DifferenceClass.ANALYTICAL,
                        ),
                    ),
                )
                continue
            comparisons[name] = RecordComparison(
                baseline_digest=expected[name],
                actual_digest=actual[name],
                differences=diff_records(baseline_file.read_bytes(), actual_file.read_bytes()),
            )
    return comparisons


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
    comparisons = compare(args.baseline, store=store, release_id=release_id, device=args.device)
    analytically_equivalent = all(item.analytically_equivalent for item in comparisons.values())
    counts: dict[str, int] = {}
    for item in comparisons.values():
        for difference in item.differences:
            counts[difference.classification.value] = counts.get(difference.classification.value, 0) + 1
    report = {
        "baseline": str(args.baseline),
        "equivalent": not comparisons,
        "analytically_equivalent": analytically_equivalent,
        "difference_counts_by_class": dict(sorted(counts.items())),
        "analytical_differences": {
            name: [asdict(d) for d in item.differences if d.classification is DifferenceClass.ANALYTICAL]
            for name, item in comparisons.items()
            if not item.analytically_equivalent
        },
        "comparisons": {name: asdict(item) for name, item in comparisons.items()},
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if analytically_equivalent else 1


if __name__ == "__main__":
    raise SystemExit(main())

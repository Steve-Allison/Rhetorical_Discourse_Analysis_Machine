"""Capture and compare the RST public-contract baseline across migration.

006 rst-preservation contract §Equivalence procedure: before migration, persist the
serialized contract outputs for representative inputs across all six declared source
forms; after migration, recapture with identical commands and compare. Semantic digests
exclude execution evidence (ids, durations, device), so equality of digests is equality
of meaning; the full serialized records are kept beside them as the auditable artifact.

Every pair of records is diffed field by field, even when stored digests match, and
every difference is classified before a verdict is given:

* ``execution`` — execution evidence (ids, durations, timings, clock, git revision); never semantic.
* ``package_identity`` — the package's own version, and its name where a record names
  the package as the validator of a built-in source form.
* ``package_source_identity`` — digests and sizes of the package's *own source files*
  recorded as packaged-component identities, and the digests derived from them. These
  change whenever the package's source bytes change, as they do in a rename.
* ``derived_digest`` — a digest computed from other fields of the same record.
* ``contract_field_rename`` — the owner-approved Feature 017 rename of
  ``analysis_plan.parser_capacity`` to ``analysis_plan.capacity``, only when the
  complete capacity value is identical and neither record contains both names.
* ``source_identity_correction`` and ``doclang_table_correction`` — the separately
  proven, owner-approved Feature 017 repairs. These change analytical records and
  are not called equivalent; acceptance requires zero unexplained regressions.
* ``analytical`` — everything else: prepared text, segments, inventory, nodes, edges,
  anchors, validation. Any analytical difference fails the comparison.

A release that renames or re-versions the distribution cannot be byte-identical in the
first three classes; it is still required to be identical in the last.

    pixi run rst-baseline capture --output BASELINE --store MODEL_STORE --release-id RELEASE_ID
    pixi run rst-baseline compare --baseline BASELINE --store MODEL_STORE --release-id RELEASE_ID
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
from rdam.ingest import (
    ProductionIngestor,
    SourceArtifact,
    SourceForm,
    describe_capabilities,
    serialize_contract,
)
from tools.production_boundary.installed_acceptance import _archive_bytes
from tools.production_boundary.baseline_corrections import (
    BaselineVerificationError,
    doclang_table_correction_prefixes,
    rebind_verified_identities,
    source_identity_correction_paths,
    verify_preparation_source,
)

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
    CONTRACT_FIELD_RENAME = "contract_field_rename"
    SOURCE_IDENTITY_CORRECTION = "source_identity_correction"
    DOCLANG_TABLE_CORRECTION = "doclang_table_correction"
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
        return not any(item.classification in {
            DifferenceClass.ANALYTICAL,
            DifferenceClass.SOURCE_IDENTITY_CORRECTION,
            DifferenceClass.DOCLANG_TABLE_CORRECTION,
        } for item in self.differences)

    @property
    def no_unexplained_regressions(self) -> bool:
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
        parser = Parser.from_model_release(store, release_id, device=device)
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
        if not value:
            return {path: {}}
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
        if path and path[-1] == "role" and value == _PACKAGED_COMPONENT_ROLE:
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

    if not path:
        return DifferenceClass.ANALYTICAL
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
        if path == ("semantic", "request", "analysis_plan_identity", "hex_digest"):
            plan_path = ("semantic", "preparation", "semantic", "analysis_plan", "semantic_digest", "hex_digest")
            if (
                isinstance(before, str) and isinstance(after, str)
                and before == baseline.get(plan_path) and after == actual.get(plan_path)
            ):
                return DifferenceClass.DERIVED_DIGEST
        if before in _package_source_digests(baseline) and after in _package_source_digests(actual):
            return DifferenceClass.PACKAGE_SOURCE_IDENTITY
        if len(path) >= 2 and path[-2] in _DERIVED_DIGEST_CONTAINERS:
            return DifferenceClass.DERIVED_DIGEST
    return DifferenceClass.ANALYTICAL


def diff_records(
    baseline_payload: bytes, actual_payload: bytes, *, source: SourceArtifact | None = None,
) -> tuple[Difference, ...]:
    """Every field-level difference between two serialized records, classified."""

    baseline_record = json.loads(baseline_payload)
    actual_record = json.loads(actual_payload)
    if source is not None:
        verify_preparation_source(actual_record, source)
    identities = frozenset() if source is None else source_identity_correction_paths(baseline_record, actual_record, source)
    tables = frozenset() if source is None else doclang_table_correction_prefixes(
        rebind_verified_identities(baseline_record, actual_record, identities), actual_record, source,
    )
    baseline = _flatten(baseline_record)
    actual = _flatten(actual_record)
    renamed = _capacity_rename_paths(baseline, actual)
    differences: list[Difference] = []
    for path in sorted(set(baseline) | set(actual)):
        before = baseline.get(path, "<absent>")
        after = actual.get(path, "<absent>")
        if path in baseline and path in actual and type(before) is type(after) and before == after:
            continue
        differences.append(
            Difference(
                path="/".join(path),
                baseline=before,
                actual=after,
                classification=(
                    DifferenceClass.SOURCE_IDENTITY_CORRECTION if path in identities else
                    DifferenceClass.DOCLANG_TABLE_CORRECTION if any(path[:len(prefix)] == prefix for prefix in tables) else
                    DifferenceClass.CONTRACT_FIELD_RENAME
                    if path in renamed else classify(path, baseline, actual)
                ),
            )
        )
    return tuple(differences)


def _capacity_rename_paths(
    baseline: dict[JsonPath, Any], actual: dict[JsonPath, Any],
) -> frozenset[JsonPath]:
    """Recognize exactly the approved rename; changed capacity values still fail."""

    containers = {
        path[:index + 1]
        for path in baseline
        for index, part in enumerate(path[:-1])
        if part == "analysis_plan" and path[index + 1] == "parser_capacity"
    }
    renamed: set[JsonPath] = set()
    for container in containers:
        old_prefix = (*container, "parser_capacity")
        new_prefix = (*container, "capacity")
        length = len(old_prefix)
        before = {path[length:]: value for path, value in baseline.items() if path[:length] == old_prefix}
        after = {path[length:]: value for path, value in actual.items() if path[:length] == new_prefix}
        if not before or before != after:
            continue
        if any(path[:length] == new_prefix for path in baseline):
            continue
        if any(path[:length] == old_prefix for path in actual):
            continue
        renamed.update((*old_prefix, *suffix) for suffix in before)
        renamed.update((*new_prefix, *suffix) for suffix in after)
    return frozenset(renamed)


def compare(baseline: Path, *, store: Path | None, release_id: str | None, device: str) -> dict[str, RecordComparison]:
    """Compare complete records; a recorded digest never substitutes for checking their contents."""

    expected = json.loads((baseline / "digests.json").read_text(encoding="utf-8"))
    comparisons: dict[str, RecordComparison] = {}
    sources = {f"prepare-{name}": source for name, source in _artifacts().items()}
    with tempfile.TemporaryDirectory(prefix="rst-baseline-compare-") as scratch:
        scratch_path = Path(scratch)
        actual = capture(scratch_path, store=store, release_id=release_id, device=device)
        for name in sorted(set(expected) | set(actual)):
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
            differences = diff_records(baseline_file.read_bytes(), actual_file.read_bytes(), source=sources.get(name))
            if not differences and expected[name] == actual[name]:
                continue
            comparisons[name] = RecordComparison(
                baseline_digest=expected[name],
                actual_digest=actual[name],
                differences=differences,
            )
    return comparisons


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("mode", choices=("capture", "compare"))
    parser.add_argument("--output", type=Path, help="capture: directory to write")
    parser.add_argument("--baseline", type=Path, help="compare: directory written by capture")
    parser.add_argument("--store", type=Path, default=Path("models/model-releases"))
    parser.add_argument("--release-id", help="explicit immutable parser release to capture or compare")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--no-analysis", action="store_true", help="preparation and capabilities only; no model load")
    args = parser.parse_args()
    if not args.no_analysis and args.release_id is None:
        parser.error("--release-id is required unless --no-analysis is specified")
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
    try:
        comparisons = compare(args.baseline, store=store, release_id=release_id, device=args.device)
    except BaselineVerificationError as exc:
        print(json.dumps({"no_unexplained_regressions": False, "verification_failure": str(exc)}, indent=2))
        return 1
    analytically_equivalent = all(item.analytically_equivalent for item in comparisons.values())
    no_unexplained_regressions = all(item.no_unexplained_regressions for item in comparisons.values())
    counts: dict[str, int] = {}
    for item in comparisons.values():
        for difference in item.differences:
            counts[difference.classification.value] = counts.get(difference.classification.value, 0) + 1
    report = {
        "baseline": str(args.baseline),
        "equivalent": not comparisons,
        "analytically_equivalent": analytically_equivalent,
        "no_unexplained_regressions": no_unexplained_regressions,
        "difference_counts_by_class": dict(sorted(counts.items())),
        "analytical_differences": {
            name: [asdict(d) for d in item.differences if d.classification is DifferenceClass.ANALYTICAL]
            for name, item in comparisons.items()
            if not item.no_unexplained_regressions
        },
        "comparisons": {name: asdict(item) for name, item in comparisons.items()},
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if no_unexplained_regressions else 1


if __name__ == "__main__":
    raise SystemExit(main())

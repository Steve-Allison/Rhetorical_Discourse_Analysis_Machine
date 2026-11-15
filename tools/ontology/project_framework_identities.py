"""Project RDAM's framework identities from ontology/data/rdam-providers.yaml and Central_Configs v5.0.0.

Central_Configs consumer contract (../Central_Configs/AGENTS.md, verified 2026-11-15):
reference immutable ``coe:Cxxxxx`` identifiers from ``../Central_Configs/dist/build/central.sqlite``,
never copy YAML snapshots, and package deterministic JSON projections inside the wheel so
runtime ``rdam`` has zero sibling-checkout dependency.

Run: ``pixi run project-framework-identities``
"""

import argparse
import hashlib
import json
from pathlib import Path
import re
import sqlite3
from typing import Any, Final, cast

import yaml

SCHEME: Final = "https://steve-allison.github.io/Central_Configs/v5/schema/coe"
EXPECTED_CENTRAL_VERSION: Final = "5.0.0"
COE_CURIE_RE: Final = re.compile(r"^coe:C[0-9]{5}$")

TECHNIQUES: Final[tuple[str, ...]] = (
    "rst",
    "erst",
    "centering",
    "pdtb",
    "sdrt",
    "speech_acts",
    "classical_rhetoric",
    "argument_mining",
    "toulmin",
    "walton",
    "pragma_dialectics",
    "ibis",
    "aspic",
    "dung",
)

RDAM_FORMALISM_LABELS: Final[dict[str, str]] = {
    "erst": "Enhanced Rhetorical Structure Theory (eRST)",
    "centering": "Centering Theory & Entity Grid",
    "speech_acts": "Searle & Vanderveken Speech Act Theory",
    "argument_mining": "Inference Anchoring Theory (IAT) Argument Mining",
    "pragma_dialectics": "Pragma-Dialectical Theory of Argumentation",
    "aspic": "ASPIC+ Structured Argumentation",
}

PROVIDERS_PATH: Final = Path("ontology/data/rdam-providers.yaml")
CENTRAL_ROOT: Final = Path("../Central_Configs")
PROJECTION: Final = Path("rdam/resources/framework-identities.json")


def _load_central_resources(central_root: Path) -> dict[str, dict[str, str]]:
    schema_path = central_root / "schema" / "coe.linkml.yaml"
    sqlite_path = central_root / "dist" / "build" / "central.sqlite"
    if not schema_path.is_file():
        raise FileNotFoundError(f"Central_Configs schema not found: {schema_path}")
    if not sqlite_path.is_file():
        raise FileNotFoundError(f"Central_Configs SQLite store not found: {sqlite_path}")

    schema_doc = yaml.safe_load(schema_path.read_text(encoding="utf-8"))
    if not isinstance(schema_doc, dict):
        raise ValueError("Central_Configs schema root must be a mapping")
    typed_schema = cast(dict[str, Any], schema_doc)
    if typed_schema.get("id") != SCHEME:
        raise ValueError(f"Expected Central_Configs schema id {SCHEME!r}, got {typed_schema.get('id')!r}")
    if str(typed_schema.get("version")) != EXPECTED_CENTRAL_VERSION:
        raise ValueError(
            f"Expected Central_Configs version {EXPECTED_CENTRAL_VERSION!r}, got {typed_schema.get('version')!r}"
        )

    uri = f"file:{sqlite_path.resolve().as_posix()}?mode=ro"
    with sqlite3.connect(uri, uri=True) as conn:
        rows = conn.execute(
            "SELECT id, collection_name, pref_label, status FROM resources ORDER BY id"
        ).fetchall()

    resources_by_id: dict[str, dict[str, str]] = {}
    for curie, collection_name, pref_label, status in rows:
        if not isinstance(curie, str) or not COE_CURIE_RE.match(curie):
            raise ValueError(f"Invalid Central_Configs CURIE in SQLite store: {curie!r}")
        resources_by_id[curie] = {
            "id": curie,
            "collection_name": str(collection_name),
            "pref_label": str(pref_label),
            "status": str(status),
        }
    return resources_by_id


def _validate_central_curie(curie: str, resources_by_id: dict[str, dict[str, str]]) -> dict[str, str]:
    if not COE_CURIE_RE.match(curie):
        raise ValueError(f"Central_Configs binding must match ^coe:C[0-9]{{5}}$: {curie!r}")
    resource = resources_by_id.get(curie)
    if resource is None:
        raise ValueError(f"Unresolved Central_Configs CURIE: {curie!r}")
    if resource["status"] != "active":
        raise ValueError(f"Central_Configs CURIE {curie!r} is not active (status={resource['status']!r})")
    return resource


def project(
    providers_path: Path = PROVIDERS_PATH,
    central_root: Path = CENTRAL_ROOT,
) -> dict[str, Any]:
    """Build the deterministic framework identity projection from rdam-providers.yaml + central.sqlite."""

    providers_bytes = providers_path.read_bytes()
    document = yaml.safe_load(providers_bytes.decode("utf-8"))
    if not isinstance(document, dict):
        raise ValueError("ProviderBindings document must be a YAML mapping")
    typed_doc = cast(dict[str, Any], document)
    if typed_doc.get("scheme") != SCHEME:
        raise ValueError(f"Expected scheme {SCHEME!r} in {providers_path}; got {typed_doc.get('scheme')!r}")

    raw_bindings: object = typed_doc.get("bindings")
    if not isinstance(raw_bindings, list):
        raise ValueError(f"{providers_path} must contain a bindings list")

    resources_by_id = _load_central_resources(central_root)

    extracted: dict[str, dict[str, Any]] = {}
    referenced_central_rows: dict[str, dict[str, str]] = {}

    for raw_item in cast(list[object], raw_bindings):
        if not isinstance(raw_item, dict):
            raise ValueError("Each provider binding must be a mapping")
        item = cast(dict[str, Any], raw_item)
        boundary = str(item.get("boundary", ""))
        if not boundary or boundary in extracted:
            raise ValueError(f"Invalid or duplicate boundary in {providers_path}: {boundary!r}")
        extracted[boundary] = item

        formalisms: object = item.get("formalisms") or []
        if not isinstance(formalisms, list):
            raise ValueError(f"formalisms on {boundary!r} must be a list")
        for raw_form in cast(list[object], formalisms):
            if not isinstance(raw_form, dict):
                raise ValueError("Each formalism binding must be a mapping")
            form = cast(dict[str, Any], raw_form)
            formalism_id = str(form.get("formalism_id", ""))
            if formalism_id == "rst_tree":
                if form.get("authority") != item.get("authority") or form.get("framework") != item.get("framework"):
                    raise ValueError("rst_tree formalism binding must agree with the rst boundary binding")
            elif formalism_id == "erst_graph":
                if "erst" in extracted:
                    raise ValueError("Duplicate erst formalism binding")
                extracted["erst"] = form
            else:
                raise ValueError(f"Unexpected formalism_id in {providers_path}: {formalism_id!r}")

    if set(extracted) != set(TECHNIQUES):
        missing = sorted(set(TECHNIQUES) - set(extracted))
        extra = sorted(set(extracted) - set(TECHNIQUES))
        raise ValueError(f"Technique coverage mismatch: missing={missing}, extra={extra}")

    concepts: dict[str, dict[str, Any]] = {}
    curie_to_techniques: dict[str, list[str]] = {}
    native_to_curie: dict[str, str] = {}

    for technique in TECHNIQUES:
        entry = extracted[technique]
        authority = entry.get("authority")
        framework_id = entry.get("framework")
        if not isinstance(authority, str) or authority not in {"central_configs", "rdam"}:
            raise ValueError(f"Technique {technique!r} has invalid authority: {authority!r}")
        if not isinstance(framework_id, str) or not framework_id.strip():
            raise ValueError(f"Technique {technique!r} lacks a framework identifier")

        raw_central_concepts: object = entry.get("central_concepts") or []
        if not isinstance(raw_central_concepts, list):
            raise ValueError(f"Technique {technique!r} central_concepts must be a list")
        central_concepts = [str(cid) for cid in cast(list[object], raw_central_concepts)]
        if len(set(central_concepts)) != len(central_concepts):
            raise ValueError(f"Technique {technique!r} contains duplicate central_concepts")

        if authority == "central_configs":
            primary = _validate_central_curie(framework_id, resources_by_id)
            referenced_central_rows[framework_id] = primary
            if not central_concepts:
                central_concepts = [framework_id]
            if framework_id not in central_concepts:
                raise ValueError(
                    f"Technique {technique!r} primary framework {framework_id!r} must be listed in central_concepts"
                )
            for cid in central_concepts:
                referenced_central_rows[cid] = _validate_central_curie(cid, resources_by_id)
            broader = f"{SCHEME}#{primary['collection_name']}"
            label = primary["pref_label"]
        else:
            expected_id = f"rdmachine:framework/{technique}"
            if framework_id != expected_id:
                raise ValueError(f"rdam-owned technique {technique!r} must bind {expected_id!r}, got {framework_id!r}")
            if central_concepts:
                raise ValueError(f"rdam-owned technique {technique!r} cannot declare central_concepts")
            label_candidate = RDAM_FORMALISM_LABELS.get(technique)
            if label_candidate is None:
                raise ValueError(f"No RDAM formalism label declared for {technique!r}")
            broader = "rdmachine:framework"
            label = label_candidate

        concepts[technique] = {
            "authority": authority,
            "broader": broader,
            "central_concepts": central_concepts,
            "id": framework_id,
            "in_scheme": SCHEME,
            "label": label,
        }
        native_to_curie[technique] = framework_id
        curie_to_techniques.setdefault(framework_id, []).append(technique)

    digest_material = json.dumps(
        {
            "central_version": EXPECTED_CENTRAL_VERSION,
            "providers_sha256": hashlib.sha256(providers_bytes).hexdigest(),
            "referenced_central_resources": [
                referenced_central_rows[cid] for cid in sorted(referenced_central_rows)
            ],
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")

    return {
        "central_version": EXPECTED_CENTRAL_VERSION,
        "concepts": concepts,
        "curie_to_techniques": {cid: sorted(techs) for cid, techs in sorted(curie_to_techniques.items())},
        "native_to_curie": native_to_curie,
        "scheme": SCHEME,
        "source": PROVIDERS_PATH.as_posix(),
        "source_sha256": hashlib.sha256(digest_material).hexdigest(),
    }


def render(projection: dict[str, Any]) -> str:
    return json.dumps(projection, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--providers", type=Path, default=PROVIDERS_PATH)
    parser.add_argument("--central-root", type=Path, default=CENTRAL_ROOT)
    parser.add_argument("--output", type=Path, default=PROJECTION)
    parser.add_argument("--check", action="store_true", help="fail if the committed projection differs")
    args = parser.parse_args()

    rendered = render(project(args.providers, args.central_root))
    if args.check:
        current = args.output.read_text(encoding="utf-8") if args.output.is_file() else ""
        if current != rendered:
            print(f"projection is stale: regenerate with `pixi run project-framework-identities` ({args.providers})")
            return 1
        print(f"projection matches {args.providers} and {args.central_root}")
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")
    print(f"wrote {args.output} from {args.providers} and {args.central_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

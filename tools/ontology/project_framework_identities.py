"""Project Central's analytical-frameworks taxonomy into the ``rdam`` package resource.

Central's consumer contract: reference ``coe:`` identifiers, never redefine them, and
generate any runtime projection inside the consumer. This tool reads the vendored
``ontology/vendor/central-configs/domains/narrative/analytical_frameworks.yaml`` and
writes ``machine/rdam/resources/framework-identities.json`` — id, label, broader, and
scheme for each of the eight framework concepts the machine binds to. A test asserts the
committed projection equals a fresh projection of the vendored file, so drift fails.

Run: ``pixi run project-framework-identities``
"""

import argparse
import json
from pathlib import Path
from typing import Any

import yaml

SCHEME = "coe:artifact/narrative/analytical_frameworks_taxonomy"
TECHNIQUES = ("rst", "erst", "pdtb", "sdrt", "toulmin", "walton", "dung", "ibis")
VENDORED_TAXONOMY = Path("ontology/vendor/central-configs/domains/narrative/analytical_frameworks.yaml")
PROJECTION = Path("machine/rdam/resources/framework-identities.json")


def project(taxonomy_path: Path) -> dict[str, Any]:
    """Build the projection from the vendored taxonomy, failing on any missing concept."""

    document = yaml.safe_load(taxonomy_path.read_text(encoding="utf-8"))
    taxonomies = [item for item in document["taxonomies"] if item["id"] == SCHEME]
    if len(taxonomies) != 1:
        raise ValueError(f"expected exactly one {SCHEME} in {taxonomy_path}; found {len(taxonomies)}")
    concepts_by_id = {concept["id"]: concept for concept in taxonomies[0]["concepts"]}
    concepts: dict[str, dict[str, str]] = {}
    for technique in TECHNIQUES:
        matches = [concept for concept_id, concept in concepts_by_id.items() if concept_id.endswith(f"/{technique}")]
        if len(matches) != 1:
            raise ValueError(f"expected exactly one concept ending in /{technique}; found {len(matches)}")
        concept = matches[0]
        broader = concept.get("broader", [])
        if len(broader) != 1:
            raise ValueError(f"{concept['id']} must have exactly one broader concept; found {len(broader)}")
        concepts[technique] = {
            "id": concept["id"],
            "label": concept["label"],
            "broader": broader[0],
            "in_scheme": concept["in_scheme"],
        }
    return {
        "scheme": SCHEME,
        # Always the fixed vendored location, never the argument path, so the committed
        # projection is byte-stable wherever it is regenerated.
        "source": VENDORED_TAXONOMY.as_posix(),
        "last_updated": str(taxonomies[0]["last_updated"]),
        "concepts": concepts,
    }


def render(projection: dict[str, Any]) -> str:
    return json.dumps(projection, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--taxonomy", type=Path, default=VENDORED_TAXONOMY)
    parser.add_argument("--output", type=Path, default=PROJECTION)
    parser.add_argument("--check", action="store_true", help="fail if the committed projection differs")
    args = parser.parse_args()
    rendered = render(project(args.taxonomy))
    if args.check:
        current = args.output.read_text(encoding="utf-8") if args.output.is_file() else ""
        if current != rendered:
            print(f"projection is stale: regenerate with the tool (source {args.taxonomy})")
            return 1
        print(f"projection matches {args.taxonomy}")
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")
    print(f"wrote {args.output} from {args.taxonomy}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

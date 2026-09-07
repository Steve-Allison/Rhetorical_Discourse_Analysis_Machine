"""Project Central's discourse taxonomy without inventing native crosswalks.

Run with ``pixi run python -m tools.ontology.project_discourse_concepts``.
The packaged concepts retain their complete authoritative definitions and parents.
"""

import argparse
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

import yaml

SOURCE = Path("ontology/vendor/central-configs/domains/narrative/discourse_argumentation.yaml")
OUTPUT = Path("rdam/resources/discourse-concepts.json")
VOCABULARY_OUTPUT = Path("rdam/resources/technique-concepts.json")
VOCABULARY_SOURCES = (
    SOURCE.with_name("discourse_techniques.yaml"),
    SOURCE.with_name("argumentation_schemes.yaml"),
    SOURCE.with_name("story_frameworks.yaml"),
)


def project(source: Path, taxonomy_id: str | None = None) -> dict[str, Any]:
    raw = source.read_bytes()
    document = yaml.safe_load(raw)
    if document["_meta"]["authority"] != "Central_Configs":
        raise ValueError("Discourse concepts require Central_Configs authority")
    taxonomies = document["taxonomies"]
    if taxonomy_id is not None:
        taxonomies = [item for item in taxonomies if item["id"] == taxonomy_id]
    if len(taxonomies) != 1:
        raise ValueError("Expected one discourse taxonomy")
    taxonomy = taxonomies[0]
    concepts: dict[str, Any] = {}
    for concept in taxonomy["concepts"]:
        identifier = concept["id"]
        if identifier in concepts:
            raise ValueError("Duplicate discourse concept identity")
        if concept["in_scheme"] != taxonomy["id"]:
            raise ValueError("Discourse concept belongs to a foreign scheme")
        concepts[identifier] = concept
    for identifier, concept in concepts.items():
        for parent in concept.get("broader", []):
            if parent == identifier or parent not in concepts:
                raise ValueError("Unresolved or self-referencing discourse parent")
        visited: set[str] = set()
        pending = list(concept.get("broader", []))
        while pending:
            parent = pending.pop()
            if parent == identifier:
                raise ValueError("Cyclic discourse hierarchy")
            if parent not in visited:
                visited.add(parent)
                if parent not in concepts:
                    raise ValueError("Unresolved discourse ancestor")
                pending.extend(concepts[parent].get("broader", []))
    if any(identifier not in concepts for identifier in taxonomy["top_concepts"]):
        raise ValueError("Unresolved discourse top concept")
    return {
        "authority": document["_meta"]["authority"],
        "source": (SOURCE if taxonomy_id is None else source).as_posix(), "source_sha256": sha256(raw).hexdigest(),
        "scheme": taxonomy["id"], "description": taxonomy["description"],
        "last_updated": str(taxonomy["last_updated"]), "concepts": concepts,
    }


def project_vocabularies() -> dict[str, Any]:
    vocabularies: dict[str, Any] = {}
    for source in VOCABULARY_SOURCES:
        document = yaml.safe_load(source.read_bytes())
        for taxonomy in document["taxonomies"]:
            identifier = taxonomy["id"]
            if source.name == "story_frameworks.yaml" and identifier != "coe:artifact/narrative/descriptive_rst_taxonomy":
                continue
            if identifier in vocabularies:
                raise ValueError("Duplicate vocabulary scheme identity")
            vocabularies[identifier] = project(source, identifier)
    return vocabularies


def render(projection: dict[str, Any]) -> str:
    return json.dumps(projection, sort_keys=True, ensure_ascii=False, indent=2) + "\n"


def preserve_snapshot(raw: bytes, root: Path) -> None:
    """Keep exact identified authority bytes before replacing a projection."""
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{sha256(raw).hexdigest()}.json"
    if path.exists() and path.read_bytes() != raw:
        raise ValueError(f"Archived ontology snapshot is corrupt: {path}")
    path.write_bytes(raw)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if not args.check:
        from rdam.ontology import walton_profile_snapshot

        identity, raw = walton_profile_snapshot()
        root = OUTPUT.parent / "walton-profiles"
        root.mkdir(parents=True, exist_ok=True)
        path = root / f"{identity}.json"
        if path.exists() and path.read_bytes() != raw:
            raise ValueError("Archived Walton profile is corrupt")
        path.write_bytes(raw)
    for output, projection in ((OUTPUT, project(SOURCE)), (VOCABULARY_OUTPUT, project_vocabularies())):
        expected = render(projection)
        if args.check:
            if not output.is_file() or output.read_text(encoding="utf-8") != expected:
                raise ValueError(f"Discourse concept projection is stale: {output}")
            print(f"Projection matches its authority: {output}")
        else:
            if output.is_file():
                preserve_snapshot(output.read_bytes(), output.parent / "ontology-snapshots")
            preserve_snapshot(expected.encode("utf-8"), output.parent / "ontology-snapshots")
            output.write_text(expected, encoding="utf-8")
            print(f"Wrote {output}")


if __name__ == "__main__":
    main()

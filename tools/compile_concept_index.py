"""Build-only compiler: project Central_Configs v5.0.0 LinkableProperNoun surface rules from central.sqlite."""

import argparse
import json
from pathlib import Path
import sqlite3
from typing import Any, cast

import yaml

from rdam.concepts.index import IndexProjection, LexicalEntry, SemanticResource


def _mapping(value: object) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("expected a string-keyed mapping")
    if any(not isinstance(key, str) for key in cast(dict[object, object], value)):
        raise ValueError("expected a string-keyed mapping")
    return cast(dict[str, Any], value)


def _string_tuple(raw_json: object, field_name: str) -> tuple[str, ...]:
    if not isinstance(raw_json, str):
        raise ValueError(f"{field_name} must be a JSON string array")
    parsed: object = json.loads(raw_json)
    if not isinstance(parsed, list) or any(not isinstance(item, str) for item in cast(list[object], parsed)):
        raise ValueError(f"{field_name} must decode to a list of strings")
    return tuple(cast(list[str], parsed))


def _allowed_proper_noun_collections(root: Path) -> tuple[str, str, frozenset[str]]:
    schema_path = (root / "schema/coe.linkml.yaml").resolve()
    if not schema_path.is_file():
        raise FileNotFoundError(f"Central_Configs v5 schema not found: {schema_path}")
    root_schema = _mapping(yaml.safe_load(schema_path.read_bytes()))
    distribution_id = str(root_schema["id"])
    version = str(root_schema["version"])

    classes: dict[str, dict[str, Any]] = {}
    slots: dict[str, dict[str, Any]] = {}
    loaded: set[Path] = set()

    def _load_schema(path: Path) -> None:
        resolved = path.resolve()
        if resolved in loaded:
            return
        if not resolved.is_relative_to(root):
            raise ValueError(f"schema import escapes distribution root: {path}")
        if not resolved.is_file():
            raise FileNotFoundError(f"imported LinkML module not found: {resolved}")
        loaded.add(resolved)
        doc = _mapping(yaml.safe_load(resolved.read_bytes()))
        for imported in doc.get("imports", []):
            if imported == "linkml:types":
                continue
            _load_schema(resolved.parent / f"{imported}.yaml")
        for cls_name, cls_def in _mapping(doc.get("classes", {})).items():
            classes[cls_name] = _mapping(cls_def)
        for slot_name, slot_def in _mapping(doc.get("slots", {})).items():
            slots[slot_name] = _mapping(slot_def)

    _load_schema(schema_path)

    def _mixes_in_proper_noun(cls_name: str) -> bool:
        current: str | None = cls_name
        while current is not None and current in classes:
            cls_def = classes[current]
            mixins = cls_def.get("mixins", [])
            if isinstance(mixins, list) and "LinkableProperNoun" in mixins:
                return True
            parent = cls_def.get("is_a")
            current = parent if isinstance(parent, str) else None
        return False

    module_slots = classes["KnowledgeModule"].get("slots", [])
    allowed = frozenset(
        slot_name
        for slot_name in module_slots
        if isinstance(slot_name, str)
        and slot_name in slots
        and isinstance(slots[slot_name].get("range"), str)
        and _mixes_in_proper_noun(str(slots[slot_name]["range"]))
    )
    if not allowed:
        raise ValueError("schema declared zero LinkableProperNoun collections")
    return distribution_id, version, allowed


def compile_distribution(root: Path) -> IndexProjection:
    """Compile LinkableProperNoun resources and SurfaceMatchRules from Central_Configs v5.0.0."""
    root = root.resolve()
    distribution_id, version, allowed_collections = _allowed_proper_noun_collections(root)
    db_path = (root / "dist/build/central.sqlite").resolve()
    if not db_path.is_file():
        raise FileNotFoundError(f"Central_Configs SQLite store not found: {db_path}")

    placeholders = ", ".join("?" for _ in sorted(allowed_collections))
    sorted_allowed = tuple(sorted(allowed_collections))

    with sqlite3.connect(f"file:{db_path}?mode=ro", uri=True) as conn:
        conn.row_factory = sqlite3.Row
        disallowed = conn.execute(
            f"SELECT DISTINCT collection_name FROM match_lexicon WHERE collection_name NOT IN ({placeholders})",
            sorted_allowed,
        ).fetchall()
        if disallowed:
            names = [str(row["collection_name"]) for row in disallowed]
            raise ValueError(f"Rule 6 firewall violation: non-LinkableProperNoun collection in match_lexicon: {names}")

        resource_rows = conn.execute(
            f"SELECT id, collection_name, pref_label, definition, status "
            f"FROM resources WHERE collection_name IN ({placeholders}) ORDER BY id",
            sorted_allowed,
        ).fetchall()
        lexicon_rows = conn.execute(
            "SELECT curie, pref_label, collection_name, surface, match_policy, case_sensitive, "
            "anchor_window_tokens, requires_llm_disambiguation, context_anchors_json, negative_phrases_json "
            "FROM match_lexicon ORDER BY curie, surface, match_policy"
        ).fetchall()

    resources = tuple(
        SemanticResource.model_validate(
            {
                "curie": row["id"],
                "pref_label": row["pref_label"],
                "definition": row["definition"],
                "collection_name": row["collection_name"],
                "status": row["status"],
            }
        )
        for row in resource_rows
    )
    entries = tuple(
        LexicalEntry.model_validate(
            {
                "curie": row["curie"],
                "pref_label": row["pref_label"],
                "collection_name": row["collection_name"],
                "surface": row["surface"],
                "match_policy": row["match_policy"],
                "case_sensitive": bool(row["case_sensitive"]),
                "anchor_window_tokens": int(row["anchor_window_tokens"]),
                "context_anchors": _string_tuple(row["context_anchors_json"], "context_anchors_json"),
                "negative_phrases": _string_tuple(row["negative_phrases_json"], "negative_phrases_json"),
                "requires_llm_disambiguation": bool(row["requires_llm_disambiguation"]),
            }
        )
        for row in lexicon_rows
    )
    domains = tuple(sorted({item.collection_name for item in resources}))
    return IndexProjection(
        distribution_id=distribution_id,
        version=version,
        domains=domains,
        resources=resources,
        entries=entries,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "distribution",
        nargs="?",
        type=Path,
        default=Path("../Central_Configs"),
    )
    parser.add_argument(
        "output",
        nargs="?",
        type=Path,
        default=Path("rdam/resources/concept-index.json"),
    )
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    projection = compile_distribution(args.distribution)
    payload = projection.model_dump_json(indent=2) + "\n"
    if args.check:
        if args.output.read_text(encoding="utf-8") != payload:
            raise ValueError("generated concept projection is stale")
    else:
        args.output.write_text(payload, encoding="utf-8")
    print(
        f"{len(projection.domains)} collections; {len(projection.resources)} resources; "
        f"{len(projection.entries)} surface rules; {projection.content_digest}"
    )


if __name__ == "__main__":
    main()

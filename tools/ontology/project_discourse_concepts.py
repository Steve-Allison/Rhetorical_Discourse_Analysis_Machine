"""Project Central_Configs v5.0.0 rhetoric, discourse, rubric, and detector resources into RDAM.

Queries ``../Central_Configs/dist/build/central.sqlite`` (``file:...?mode=ro``, verified 2026-11-15)
and ``../Central_Configs/schema/coe.linkml.yaml``, writing:
1. ``rdam/resources/discourse-concepts.json`` — projected ``story_frameworks``, ``framework_stages``,
   ``argument_schemes``, ``discourse_relations``, ``rhetorical_moves``, ``rubrics``,
   ``diagnostic_detectors``, and ``coe:C00108`` (``ISO 24617-8 Core Discourse Relations``).
2. ``rdam/resources/technique-concepts.json`` — explicit ``native_value <-> coe:Cxxxxx`` lookup
   tables verified against both ``central.sqlite`` and RDAM's native runtime inventories.

Run: ``pixi run project-discourse-concepts`` (or ``--check`` to verify parity).
"""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
import sqlite3
from typing import Any, Final, Literal, cast

import yaml

from rdam.dung.semantics import DungInput
from rdam.ibis.grammar import NodeKind, Relation
from rdam.pdtb.relations import PdtbSense
from rdam.rst.ontology.loader import load_ontology_lock
from rdam.sdrt.graph import RelationStructure
from rdam.walton.schemes import SchemeId

SCHEME: Final = "https://steve-allison.github.io/Central_Configs/v5/schema/coe"
EXPECTED_CENTRAL_VERSION: Final = "5.0.0"
COE_CURIE_RE: Final = re.compile(r"^coe:C[0-9]{5}$")

CENTRAL_ROOT: Final = Path("../Central_Configs")
OUTPUT: Final = Path("rdam/resources/discourse-concepts.json")
VOCABULARY_OUTPUT: Final = Path("rdam/resources/technique-concepts.json")

PROJECTED_COLLECTIONS: Final[tuple[str, ...]] = (
    "argument_schemes",
    "diagnostic_detectors",
    "discourse_relations",
    "framework_stages",
    "rhetorical_moves",
    "rubrics",
    "story_frameworks",
)
EXTRA_RESOURCE_IDS: Final[tuple[str, ...]] = ("coe:C00108",)

type RelationshipKind = Literal["exact", "broader"]

# Explicit native_value -> (coe:Cxxxxx, relationship) bindings verified against
# ../Central_Configs/dist/build/central.sqlite (verified 2026-11-15).
TOULMIN_ROLE_BINDINGS: Final[dict[str, tuple[str, RelationshipKind]]] = {
    "claim": ("coe:C06101", "exact"),
    "grounds": ("coe:C06102", "exact"),
    "warrant": ("coe:C06103", "exact"),
    "backing": ("coe:C06104", "exact"),
    "qualifier": ("coe:C06105", "exact"),
    "rebuttal": ("coe:C06106", "exact"),
}

WALTON_SCHEME_BINDINGS: Final[dict[str, tuple[str, RelationshipKind]]] = {
    "expert_opinion": ("coe:C06112", "exact"),
    "popular_opinion": ("coe:C06113", "broader"),
    "analogy": ("coe:C06109", "exact"),
    "sign": ("coe:C06110", "exact"),
    "cause_to_effect": ("coe:C06108", "exact"),
    "consequences": ("coe:C06107", "exact"),
    "practical_reasoning": ("coe:C06107", "broader"),
    "verbal_classification": ("coe:C06114", "exact"),
    "ad_hominem": ("coe:C06115", "broader"),
}

PDTB3_SENSE_BINDINGS: Final[dict[str, tuple[str, RelationshipKind]]] = {
    "Temporal.Synchronous": ("coe:C06122", "exact"),
    "Temporal.Asynchronous.Precedence": ("coe:C06121", "exact"),
    "Temporal.Asynchronous.Succession": ("coe:C06121", "broader"),
    "Contingency.Cause.Reason": ("coe:C06123", "broader"),
    "Contingency.Cause.Result": ("coe:C06123", "exact"),
    "Contingency.Cause.NegResult": ("coe:C06123", "broader"),
    "Contingency.Cause+Belief.Reason+Belief": ("coe:C06124", "broader"),
    "Contingency.Cause+Belief.Result+Belief": ("coe:C06124", "broader"),
    "Contingency.Cause+SpeechAct.Reason+SpeechAct": ("coe:C06124", "broader"),
    "Contingency.Cause+SpeechAct.Result+SpeechAct": ("coe:C06124", "broader"),
    "Contingency.Condition.Arg1-as-cond": ("coe:C06125", "broader"),
    "Contingency.Condition.Arg2-as-cond": ("coe:C06125", "broader"),
    "Contingency.Condition+SpeechAct": ("coe:C06125", "broader"),
    "Contingency.Negative-condition.Arg1-as-negCond": ("coe:C06125", "broader"),
    "Contingency.Negative-condition.Arg2-as-negCond": ("coe:C06125", "broader"),
    "Contingency.Negative-condition+SpeechAct": ("coe:C06125", "broader"),
    "Comparison.Concession.Arg1-as-denier": ("coe:C06127", "broader"),
    "Comparison.Concession.Arg2-as-denier": ("coe:C06127", "broader"),
    "Comparison.Concession+SpeechAct.Arg2-as-denier+SpeechAct": ("coe:C06127", "broader"),
    "Comparison.Contrast": ("coe:C06126", "exact"),
    "Expansion.Equivalence": ("coe:C06130", "broader"),
    "Expansion.Instantiation.Arg1-as-instance": ("coe:C06128", "broader"),
    "Expansion.Instantiation.Arg2-as-instance": ("coe:C06128", "broader"),
    "Expansion.Level-of-detail.Arg1-as-detail": ("coe:C06129", "broader"),
    "Expansion.Level-of-detail.Arg2-as-detail": ("coe:C06129", "broader"),
}

IBIS_BINDINGS: Final[dict[str, tuple[str, RelationshipKind]]] = {
    "issue": ("coe:C06111", "broader"),
    "position": ("coe:C06111", "broader"),
    "argument": ("coe:C06111", "broader"),
    "responds_to": ("coe:C06111", "broader"),
    "supports": ("coe:C06111", "broader"),
    "objects_to": ("coe:C06111", "broader"),
}

DUNG_BINDINGS: Final[dict[str, tuple[str, RelationshipKind]]] = {
    "attacks": ("coe:C06106", "broader"),
}

CLASSICAL_RHETORIC_BINDINGS: Final[dict[str, tuple[str, RelationshipKind]]] = {
    "ethos": ("coe:C06007", "broader"),
    "pathos": ("coe:C06007", "broader"),
    "logos": ("coe:C06007", "broader"),
}

SDRT_RELATION_BINDINGS: Final[dict[str, tuple[str, RelationshipKind]]] = {
    "narration": ("coe:C06121", "broader"),
    "result": ("coe:C06123", "exact"),
    "explanation": ("coe:C06124", "exact"),
    "consequence": ("coe:C06125", "exact"),
    "contrast": ("coe:C06126", "exact"),
    "elaboration": ("coe:C06129", "exact"),
}

RST_DT_COARSE_BINDINGS: Final[dict[str, tuple[str, RelationshipKind]]] = {
    "temporal": ("coe:C06121", "broader"),
    "cause": ("coe:C06123", "exact"),
    "explanation": ("coe:C06124", "exact"),
    "condition": ("coe:C06125", "exact"),
    "comparison": ("coe:C06126", "broader"),
    "contrast": ("coe:C06126", "exact"),
    "elaboration": ("coe:C06129", "exact"),
    "summary": ("coe:C06130", "exact"),
}

RST_DT_FINE_BINDINGS: Final[dict[str, tuple[str, RelationshipKind]]] = {
    "sequence": ("coe:C06121", "exact"),
    "inverted-sequence": ("coe:C06121", "broader"),
    "temporal-after": ("coe:C06121", "broader"),
    "temporal-before": ("coe:C06121", "exact"),
    "temporal-same-time": ("coe:C06122", "exact"),
    "cause": ("coe:C06123", "broader"),
    "cause-result": ("coe:C06123", "exact"),
    "consequence": ("coe:C06123", "broader"),
    "result": ("coe:C06123", "broader"),
    "evidence": ("coe:C06124", "exact"),
    "explanation-argumentative": ("coe:C06124", "broader"),
    "reason": ("coe:C06124", "broader"),
    "condition": ("coe:C06125", "exact"),
    "contingency": ("coe:C06125", "broader"),
    "hypothetical": ("coe:C06125", "broader"),
    "otherwise": ("coe:C06125", "broader"),
    "antithesis": ("coe:C06126", "exact"),
    "comparison": ("coe:C06126", "broader"),
    "contrast": ("coe:C06126", "exact"),
    "concession": ("coe:C06127", "exact"),
    "example": ("coe:C06128", "exact"),
    "definition": ("coe:C06129", "broader"),
    "elaboration-additional": ("coe:C06129", "broader"),
    "elaboration-general-specific": ("coe:C06129", "broader"),
    "elaboration-object-attribute": ("coe:C06129", "broader"),
    "elaboration-part-whole": ("coe:C06129", "broader"),
    "elaboration-process-step": ("coe:C06129", "broader"),
    "elaboration-set-member": ("coe:C06129", "broader"),
    "restatement": ("coe:C06130", "exact"),
    "summary": ("coe:C06130", "exact"),
}

GUM_ERST_COARSE_BINDINGS: Final[dict[str, tuple[str, RelationshipKind]]] = {
    "adversative": ("coe:C06126", "broader"),
    "causal": ("coe:C06123", "exact"),
    "contingency": ("coe:C06125", "exact"),
    "elaboration": ("coe:C06129", "exact"),
    "explanation": ("coe:C06124", "exact"),
    "restatement": ("coe:C06130", "exact"),
}

GUM_ERST_FINE_BINDINGS: Final[dict[str, tuple[str, RelationshipKind]]] = {
    "joint-sequence": ("coe:C06121", "exact"),
    "causal-cause": ("coe:C06123", "broader"),
    "causal-result": ("coe:C06123", "broader"),
    "explanation-evidence": ("coe:C06124", "exact"),
    "explanation-justify": ("coe:C06124", "broader"),
    "contingency-condition": ("coe:C06125", "exact"),
    "adversative-antithesis": ("coe:C06126", "exact"),
    "adversative-contrast": ("coe:C06126", "exact"),
    "adversative-concession": ("coe:C06127", "exact"),
    "elaboration-additional": ("coe:C06129", "broader"),
    "elaboration-attribute": ("coe:C06129", "broader"),
    "restatement-partial": ("coe:C06130", "broader"),
    "restatement-repetition": ("coe:C06130", "broader"),
}


def _verify_central_schema(central_root: Path) -> None:
    schema_path = central_root / "schema" / "coe.linkml.yaml"
    if not schema_path.is_file():
        raise FileNotFoundError(f"Central_Configs schema not found: {schema_path}")
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


def project(central_root: Path = CENTRAL_ROOT) -> dict[str, Any]:
    """Project rhetoric, discourse, rubric, and diagnostic detector resources from central.sqlite."""

    _verify_central_schema(central_root)
    sqlite_path = central_root / "dist" / "build" / "central.sqlite"
    if not sqlite_path.is_file():
        raise FileNotFoundError(f"Central_Configs SQLite store not found: {sqlite_path}")

    placeholders = ", ".join("?" for _ in PROJECTED_COLLECTIONS)
    extra_placeholders = ", ".join("?" for _ in EXTRA_RESOURCE_IDS)
    uri = f"file:{sqlite_path.resolve().as_posix()}?mode=ro"
    with sqlite3.connect(uri, uri=True) as conn:
        all_active_ids = {
            str(row[0])
            for row in conn.execute("SELECT id FROM resources WHERE status = 'active'").fetchall()
        }
        rows = conn.execute(
            f"""
            SELECT id, collection_name, pref_label, definition, status, wiki_slug, facets_json, payload_json
            FROM resources
            WHERE collection_name IN ({placeholders}) OR id IN ({extra_placeholders})
            ORDER BY id
            """,
            (*PROJECTED_COLLECTIONS, *EXTRA_RESOURCE_IDS),
        ).fetchall()

    concepts: dict[str, dict[str, Any]] = {}
    collections_seen: set[str] = set()
    for raw_id, collection_name, pref_label, definition, status, wiki_slug, facets_json, payload_json in rows:
        curie = str(raw_id)
        if not COE_CURIE_RE.match(curie):
            raise ValueError(f"Invalid Central_Configs CURIE: {curie!r}")
        if curie in concepts:
            raise ValueError(f"Duplicate discourse concept identity: {curie!r}")
        if str(status) != "active":
            raise ValueError(f"Projected Central_Configs concept {curie!r} is not active: {status!r}")
        payload = json.loads(str(payload_json))
        facets = json.loads(str(facets_json))
        collection = str(collection_name)
        collections_seen.add(collection)
        concepts[curie] = {
            "collection_name": collection,
            "definition": str(definition),
            "facets": [str(item) for item in cast(list[object], facets)],
            "id": curie,
            "in_scheme": SCHEME,
            "label": str(pref_label),
            "payload": payload,
            "wiki_slug": str(wiki_slug) if wiki_slug is not None else None,
        }

    if not set(PROJECTED_COLLECTIONS) <= collections_seen:
        missing = sorted(set(PROJECTED_COLLECTIONS) - collections_seen)
        raise ValueError(f"Missing required Central_Configs collections: {missing}")
    for extra_id in EXTRA_RESOURCE_IDS:
        if extra_id not in concepts:
            raise ValueError(f"Missing required Central_Configs resource: {extra_id}")

    return validate_discourse_projection(
        {
            "authority": "Central_Configs",
            "central_version": EXPECTED_CENTRAL_VERSION,
            "collections": sorted(collections_seen),
            "concepts": concepts,
            "description": (
                "Projected Central_Configs v5.0.0 story frameworks, framework stages, argument schemes, "
                "discourse relations, rhetorical moves, rubrics, and diagnostic detectors."
            ),
            "scheme": SCHEME,
            "source": "../Central_Configs/dist/build/central.sqlite",
            "source_sha256": sha256(
                json.dumps(
                    {"central_version": EXPECTED_CENTRAL_VERSION, "concepts": concepts},
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=False,
                ).encode("utf-8")
            ).hexdigest(),
        },
        all_active_ids=all_active_ids,
    )


def validate_discourse_projection(
    projection: dict[str, Any],
    *,
    all_active_ids: set[str] | None = None,
) -> dict[str, Any]:
    """Enforce closed-world referential and acyclic parent checks on a discourse projection."""

    if projection.get("authority") != "Central_Configs":
        raise ValueError("Discourse concepts require Central_Configs authority")
    if projection.get("scheme") != SCHEME:
        raise ValueError(f"Expected scheme {SCHEME!r}, got {projection.get('scheme')!r}")

    raw_concepts = projection.get("concepts")
    if not isinstance(raw_concepts, dict) or not raw_concepts:
        raise ValueError("Discourse projection requires a non-empty concepts mapping")

    concepts = cast(dict[str, dict[str, Any]], raw_concepts)
    for key, concept in concepts.items():
        if concept.get("id") != key or not COE_CURIE_RE.match(key):
            raise ValueError(f"Invalid or mismatched discourse concept id: {key!r}")
        if concept.get("in_scheme") != SCHEME:
            raise ValueError(f"Discourse concept {key!r} belongs to a foreign scheme: {concept.get('in_scheme')!r}")

    for key, concept in concepts.items():
        payload = cast(dict[str, Any], concept.get("payload") or {})
        if concept.get("collection_name") == "framework_stages":
            parent = payload.get("stage_of_framework")
            if not isinstance(parent, str) or parent == key or parent not in concepts:
                raise ValueError(f"Unresolved or self-referencing stage_of_framework on {key!r}: {parent!r}")
            if concepts[parent].get("collection_name") != "story_frameworks":
                raise ValueError(f"stage_of_framework on {key!r} must target story_frameworks, got {parent!r}")
        parent_ref = payload.get("stage_of_framework")
        if isinstance(parent_ref, str):
            visited: set[str] = set()
            cursor: str | None = parent_ref
            while cursor is not None:
                if cursor == key or cursor in visited:
                    raise ValueError(f"Cyclic parent chain involving {key!r}")
                if cursor not in concepts:
                    raise ValueError(f"Unresolved parent {cursor!r} referenced from {key!r}")
                visited.add(cursor)
                next_payload = cast(dict[str, Any], concepts[cursor].get("payload") or {})
                next_parent = next_payload.get("stage_of_framework")
                cursor = next_parent if isinstance(next_parent, str) else None

        if all_active_ids is not None:
            for linked in cast(list[object], payload.get("linked_concepts") or []):
                if not isinstance(linked, str) or not COE_CURIE_RE.match(linked) or linked not in all_active_ids:
                    raise ValueError(f"Unresolved linked_concepts reference {linked!r} on {key!r}")
            for criterion in cast(list[object], payload.get("criteria") or []):
                if isinstance(criterion, dict):
                    crit_map = cast(dict[str, Any], criterion)
                    for linked in cast(list[object], crit_map.get("linked_concepts") or []):
                        if not isinstance(linked, str) or not COE_CURIE_RE.match(linked) or linked not in all_active_ids:
                            raise ValueError(f"Unresolved rubric criterion linked_concepts {linked!r} on {key!r}")

    return projection


def _build_lookup_table(
    *,
    bindings: dict[str, tuple[str, RelationshipKind]],
    native_inventory: tuple[str, ...],
    concepts: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    if len(set(native_inventory)) != len(native_inventory):
        raise ValueError("Native inventory contains duplicate values")
    unknown_keys = set(bindings) - set(native_inventory)
    if unknown_keys:
        raise ValueError(f"Lookup bindings name values absent from native inventory: {sorted(unknown_keys)}")

    native_to_curie: dict[str, dict[str, str]] = {}
    curie_to_native: dict[str, list[str]] = {}
    unmapped: list[str] = []

    for value in native_inventory:
        target = bindings.get(value)
        if target is None:
            unmapped.append(value)
            continue
        curie, relationship = target
        if not COE_CURIE_RE.match(curie) or curie not in concepts:
            raise ValueError(f"Lookup binding {value!r} -> {curie!r} does not resolve to projected Central_Configs")
        native_to_curie[value] = {
            "curie": curie,
            "label": str(concepts[curie]["label"]),
            "relationship": relationship,
        }
        curie_to_native.setdefault(curie, []).append(value)

    return {
        "curie_to_native": {cid: sorted(vals) for cid, vals in sorted(curie_to_native.items())},
        "declared_inventory": list(native_inventory),
        "native_to_curie": native_to_curie,
        "unmapped_native_values": unmapped,
    }


def project_vocabularies(central_root: Path = CENTRAL_ROOT) -> dict[str, Any]:
    """Project explicit native_value <-> coe:Cxxxxx lookup tables for RDAM's runtime adapters."""

    discourse = project(central_root)
    concepts = cast(dict[str, dict[str, Any]], discourse["concepts"])
    lock = load_ontology_lock()

    toulmin_inventory = ("claim", "grounds", "warrant", "backing", "qualifier", "rebuttal")
    walton_inventory = tuple(item.value for item in SchemeId)
    pdtb_inventory = tuple(item.value for item in PdtbSense)
    ibis_inventory = (
        *(item.value for item in NodeKind),
        *(item.value for item in Relation),
    )
    dung_inventory = tuple(DungInput.model_fields)
    sdrt_structural_inventory = tuple(item.value for item in RelationStructure)
    classical_rhetoric_inventory = ("ethos", "pathos", "logos")

    gum_coarse_inventory = tuple(dict.fromkeys(entry.label.casefold() for entry in lock.dmrst_gum_model_27.values()))
    gum_fine_inventory = tuple(lock.gum_fine_to_coarse)
    rst_dt_coarse_inventory = tuple(item.casefold() for item in lock.coarse_concepts)
    rst_dt_fine_inventory = tuple(
        key for key in lock.rst_dt_fine_to_coarse if key != "textualorganization"
    )

    native_frameworks = {
        "classical_rhetoric": _build_lookup_table(
            bindings=CLASSICAL_RHETORIC_BINDINGS,
            native_inventory=classical_rhetoric_inventory,
            concepts=concepts,
        ),
        "dung": _build_lookup_table(
            bindings=DUNG_BINDINGS,
            native_inventory=dung_inventory,
            concepts=concepts,
        ),
        "ibis": _build_lookup_table(
            bindings=IBIS_BINDINGS,
            native_inventory=ibis_inventory,
            concepts=concepts,
        ),
        "pdtb": _build_lookup_table(
            bindings=PDTB3_SENSE_BINDINGS,
            native_inventory=pdtb_inventory,
            concepts=concepts,
        ),
        "sdrt": _build_lookup_table(
            bindings={},
            native_inventory=sdrt_structural_inventory,
            concepts=concepts,
        ),
        "toulmin": _build_lookup_table(
            bindings=TOULMIN_ROLE_BINDINGS,
            native_inventory=toulmin_inventory,
            concepts=concepts,
        ),
        "walton": _build_lookup_table(
            bindings=WALTON_SCHEME_BINDINGS,
            native_inventory=walton_inventory,
            concepts=concepts,
        ),
    }

    observed_vocabularies: dict[str, dict[str, Any]] = {
        "gum_erst_groups": {
            "matching": "case_insensitive_label",
            **_build_lookup_table(
                bindings=GUM_ERST_COARSE_BINDINGS,
                native_inventory=gum_coarse_inventory,
                concepts=concepts,
            ),
        },
        "gum_erst_relations": {
            "matching": "case_insensitive_label",
            **_build_lookup_table(
                bindings=GUM_ERST_FINE_BINDINGS,
                native_inventory=gum_fine_inventory,
                concepts=concepts,
            ),
        },
        "pdtb3_senses": {
            "matching": "exact_key",
            **_build_lookup_table(
                bindings=PDTB3_SENSE_BINDINGS,
                native_inventory=pdtb_inventory,
                concepts=concepts,
            ),
        },
        "rst_dt_coarse": {
            "matching": "rst_dt_coarse_group",
            **_build_lookup_table(
                bindings=RST_DT_COARSE_BINDINGS,
                native_inventory=rst_dt_coarse_inventory,
                concepts=concepts,
            ),
        },
        "rst_dt_relations": {
            "matching": "rst_dt_corpus_label",
            **_build_lookup_table(
                bindings=RST_DT_FINE_BINDINGS,
                native_inventory=rst_dt_fine_inventory,
                concepts=concepts,
            ),
        },
        "sdrt_relations": {
            "matching": "case_insensitive_label",
            **_build_lookup_table(
                bindings=SDRT_RELATION_BINDINGS,
                native_inventory=tuple(SDRT_RELATION_BINDINGS),
                concepts=concepts,
            ),
        },
        "walton_profile": {
            "curie_to_native": {},
            "declared_inventory": [],
            "matching": "walton_native_profile",
            "native_to_curie": {},
            "unmapped_native_values": [],
        },
    }

    return {
        "authority": "Central_Configs",
        "central_version": EXPECTED_CENTRAL_VERSION,
        "concepts": {
            cid: {
                "collection_name": entry["collection_name"],
                "id": cid,
                "in_scheme": SCHEME,
                "label": entry["label"],
            }
            for cid, entry in sorted(concepts.items())
        },
        "native_frameworks": native_frameworks,
        "observed_vocabularies": observed_vocabularies,
        "scheme": SCHEME,
        "source": str(discourse["source"]),
        "source_sha256": str(discourse["source_sha256"]),
    }


def render(projection: dict[str, Any]) -> str:
    return json.dumps(projection, sort_keys=True, ensure_ascii=False, indent=2) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--central-root", type=Path, default=CENTRAL_ROOT)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--vocabulary-output", type=Path, default=VOCABULARY_OUTPUT)
    parser.add_argument("--check", action="store_true", help="fail if committed projections differ")
    args = parser.parse_args()

    for output, projection in (
        (args.output, project(args.central_root)),
        (args.vocabulary_output, project_vocabularies(args.central_root)),
    ):
        expected = render(projection)
        if args.check:
            if not output.is_file() or output.read_text(encoding="utf-8") != expected:
                print(f"Discourse concept projection is stale: {output}")
                return 1
            print(f"Projection matches Central_Configs v5.0.0: {output}")
        else:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(expected, encoding="utf-8")
            print(f"Wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

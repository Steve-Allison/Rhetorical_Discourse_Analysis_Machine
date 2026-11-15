"""Deterministic compilers deriving a Dung `ArgumentationFramework` from upstream technique payloads."""

from collections.abc import Mapping
from typing import cast

from rdam._strict import JsonValue
from rdam.contracts import DerivationCompiler, Technique
from rdam.dung.semantics import ArgumentationFramework, FrameworkError


def _as_map(value: object) -> Mapping[str, object] | None:
    if isinstance(value, Mapping):
        return cast(Mapping[str, object], value)
    return None


def _as_list(value: object) -> list[object] | None:
    if isinstance(value, list):
        return cast(list[object], value)
    return None


def _ensure_non_empty(arguments: list[str], attacks: list[tuple[str, str]]) -> dict[str, JsonValue]:
    if not arguments:
        raise FrameworkError("upstream result contains zero arguments to compile into a Dung framework")
    dedup_args = list(dict.fromkeys(arguments))
    known = set(dedup_args)
    clean_attacks = sorted({(src, dst) for src, dst in attacks if src in known and dst in known})
    framework = ArgumentationFramework(arguments=tuple(dedup_args), attacks=frozenset(clean_attacks))
    return cast(dict[str, JsonValue], framework.to_payload())


def derive_from_aspic(payload: Mapping[str, object]) -> dict[str, JsonValue]:
    """Extract the compiled defeat graph from an ASPIC+ payload."""
    compiled = _as_map(payload.get("defeat_framework"))
    if compiled is not None:
        raw_args = _as_list(compiled.get("arguments"))
        raw_attacks = _as_list(compiled.get("attacks"))
        if raw_args is not None and raw_attacks is not None:
            args = [a for a in raw_args if isinstance(a, str) and a]
            attacks: list[tuple[str, str]] = []
            for raw_pair in raw_attacks:
                pair = _as_list(raw_pair)
                if pair is not None and len(pair) == 2 and isinstance(pair[0], str) and isinstance(pair[1], str):
                    attacks.append((pair[0], pair[1]))
            return _ensure_non_empty(args, attacks)
    raw_arguments = _as_list(payload.get("arguments")) or []
    raw_defeats = _as_list(payload.get("defeats")) or []
    fallback_args: list[str] = []
    for raw_item in raw_arguments:
        item = _as_map(raw_item)
        if item is not None:
            arg_id = item.get("id")
            if isinstance(arg_id, str) and arg_id:
                fallback_args.append(arg_id)
    fallback_attacks: list[tuple[str, str]] = []
    for raw_item in raw_defeats:
        item = _as_map(raw_item)
        if item is not None:
            attacker = item.get("attacker")
            target = item.get("target")
            if isinstance(attacker, str) and isinstance(target, str):
                fallback_attacks.append((attacker, target))
    return _ensure_non_empty(fallback_args, fallback_attacks)


def derive_from_argument_mining(payload: Mapping[str, object]) -> dict[str, JsonValue]:
    """Compile IAT propositions and conflict (`CA`) applications into a Dung attack graph."""
    units = _as_list(payload.get("adu_nodes")) or []
    relations = _as_list(payload.get("relations")) or []
    args: list[str] = []
    for raw_node in units:
        node = _as_map(raw_node)
        if node is not None:
            nid = node.get("id")
            if isinstance(nid, str) and nid:
                args.append(nid)
    attacks: list[tuple[str, str]] = []
    for raw_rel in relations:
        rel = _as_map(raw_rel)
        if rel is None:
            continue
        if rel.get("relation_type") == "conflict":
            src = rel.get("source_id")
            dst = rel.get("target_id")
            if isinstance(src, str) and isinstance(dst, str):
                attacks.append((src, dst))
    return _ensure_non_empty(args, attacks)


def derive_from_ibis(payload: Mapping[str, object]) -> dict[str, JsonValue]:
    """Compile IBIS positions and arguments: `objects_to` attacks target; sibling positions on one issue mutually conflict."""
    structure_data = _as_map(payload.get("structure"))
    source_map: Mapping[str, object] = structure_data if structure_data is not None else payload
    nodes = _as_list(source_map.get("nodes"))
    links = _as_list(source_map.get("links"))
    if nodes is None or links is None:
        raise FrameworkError("IBIS payload missing nodes/links")

    node_types: dict[str, str] = {}
    args: list[str] = []
    for raw_node in nodes:
        node = _as_map(raw_node)
        if node is not None:
            nid = node.get("id")
            raw_kind = node.get("kind") or node.get("type")
            if isinstance(nid, str) and isinstance(raw_kind, str):
                node_types[nid] = raw_kind
                if raw_kind in {"position", "argument"}:
                    args.append(nid)

    issue_positions: dict[str, list[str]] = {}
    supported_positions: dict[str, list[str]] = {}
    attacks: list[tuple[str, str]] = []
    for raw_link in links:
        link = _as_map(raw_link)
        if link is None:
            continue
        ltype = link.get("relation") or link.get("type")
        src = link.get("from") or link.get("source")
        dst = link.get("to") or link.get("target")
        if not isinstance(src, str) or not isinstance(dst, str):
            continue
        if ltype == "responds_to" and node_types.get(src) == "position":
            issue_positions.setdefault(dst, []).append(src)
        elif ltype == "objects_to":
            attacks.append((src, dst))
        elif ltype == "supports":
            supported_positions.setdefault(dst, []).append(src)

    # Alternative positions responding to the same issue compete unless identical;
    # supporting arguments attack rival positions on the same issue.
    for positions in issue_positions.values():
        for i, pos_a in enumerate(positions):
            for pos_b in positions[i + 1 :]:
                attacks.append((pos_a, pos_b))
                attacks.append((pos_b, pos_a))
                attacks.extend((supporter, pos_b) for supporter in supported_positions.get(pos_a, ()))
                attacks.extend((supporter, pos_a) for supporter in supported_positions.get(pos_b, ()))

    return _ensure_non_empty(args, attacks)


def _toulmin_parts(payload: Mapping[str, object]) -> tuple[list[str], list[tuple[str, str]]]:
    layouts = _as_list(payload.get("layouts")) or []
    args: list[str] = []
    attacks: list[tuple[str, str]] = []
    for idx, raw_layout in enumerate(layouts):
        layout = _as_map(raw_layout)
        if layout is None:
            continue
        raw_id = layout.get("id")
        arg_id = raw_id if isinstance(raw_id, str) and raw_id else f"layout_{idx + 1}"
        args.append(arg_id)
        rebuttals = _as_list(layout.get("rebuttals"))
        if rebuttals is not None:
            for r_idx, raw_reb in enumerate(rebuttals):
                if _as_map(raw_reb) is not None:
                    reb_id = f"{arg_id}_rebuttal_{r_idx + 1}"
                    args.append(reb_id)
                    attacks.append((reb_id, arg_id))
        elif _as_map(layout.get("rebuttal")) is not None:
            reb_id = f"{arg_id}_rebuttal_1"
            args.append(reb_id)
            attacks.append((reb_id, arg_id))
    return args, attacks


def derive_from_toulmin(payload: Mapping[str, object]) -> dict[str, JsonValue]:
    """Compile Toulmin layouts and rebuttals into a Dung attack graph."""
    args, attacks = _toulmin_parts(payload)
    return _ensure_non_empty(args, attacks)


def _walton_parts(payload: Mapping[str, object]) -> tuple[list[str], list[tuple[str, str]]]:
    instances = _as_list(payload.get("instances"))
    if instances is None:
        instances = _as_list(payload.get("schemes")) or []
    args: list[str] = []
    attacks: list[tuple[str, str]] = []
    for idx, raw_inst in enumerate(instances):
        inst = _as_map(raw_inst)
        if inst is None:
            continue
        raw_id = inst.get("id")
        inst_id = raw_id if isinstance(raw_id, str) and raw_id else f"scheme_{idx + 1}"
        args.append(inst_id)
        cqs = _as_list(inst.get("critical_questions")) or []
        for cq_idx, raw_cq in enumerate(cqs):
            cq = _as_map(raw_cq)
            if cq is None:
                continue
            state = cq.get("status") or cq.get("state")
            if state in {"open", "undercut", "challenged", "unanswered_challenge", "refuted"}:
                raw_q_idx = cq.get("index")
                if raw_q_idx is None:
                    raw_q_idx = cq.get("question_index")
                if raw_q_idx is None:
                    raw_q_idx = cq.get("question_id")
                label: int | str = raw_q_idx if isinstance(raw_q_idx, (int, str)) else (cq_idx + 1)
                cq_node = f"{inst_id}_cq_{label}"
                args.append(cq_node)
                attacks.append((cq_node, inst_id))
    return args, attacks


def derive_from_walton(payload: Mapping[str, object]) -> dict[str, JsonValue]:
    """Compile Walton scheme instances and open/undercutting critical questions into a Dung attack graph."""
    args, attacks = _walton_parts(payload)
    return _ensure_non_empty(args, attacks)


def compile_by_spec(
    compiler: DerivationCompiler,
    upstream_payloads: Mapping[Technique, Mapping[str, object]],
) -> dict[str, JsonValue]:
    """Compile one or more upstream payloads into a Dung framework under `compiler`."""
    match compiler:
        case "from_aspic":
            return derive_from_aspic(upstream_payloads[Technique.ASPIC])
        case "from_argument_mining":
            return derive_from_argument_mining(upstream_payloads[Technique.ARGUMENT_MINING])
        case "from_ibis":
            return derive_from_ibis(upstream_payloads[Technique.IBIS])
        case "from_toulmin_walton":
            args: list[str] = []
            attacks: list[tuple[str, str]] = []
            if Technique.TOULMIN in upstream_payloads:
                t_args, t_attacks = _toulmin_parts(upstream_payloads[Technique.TOULMIN])
                args.extend(t_args)
                attacks.extend(t_attacks)
            if Technique.WALTON in upstream_payloads:
                w_args, w_attacks = _walton_parts(upstream_payloads[Technique.WALTON])
                args.extend(w_args)
                attacks.extend(w_attacks)
            return _ensure_non_empty(args, attacks)


def compile_derived_framework(technique: Technique, payload: Mapping[str, object]) -> dict[str, JsonValue]:
    """Deterministically compile an upstream technique payload into a Dung framework."""
    match technique:
        case Technique.ASPIC:
            return derive_from_aspic(payload)
        case Technique.ARGUMENT_MINING:
            return derive_from_argument_mining(payload)
        case Technique.IBIS:
            return derive_from_ibis(payload)
        case Technique.TOULMIN:
            return derive_from_toulmin(payload)
        case Technique.WALTON:
            return derive_from_walton(payload)
        case _:
            raise FrameworkError(f"technique {technique.value!r} cannot be compiled into a Dung framework")


__all__ = [
    "compile_by_spec",
    "compile_derived_framework",
    "derive_from_argument_mining",
    "derive_from_aspic",
    "derive_from_ibis",
    "derive_from_toulmin",
    "derive_from_walton",
]

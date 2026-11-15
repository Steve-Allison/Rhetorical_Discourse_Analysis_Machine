"""Dung abstract argumentation: extensions under grounded, complete, preferred, and stable semantics.

Definitions implemented, from Dung (1995), "On the acceptability of arguments and its
fundamental role in nonmonotonic reasoning, logic programming and n-person games":

- An argumentation framework is ``AF = (Ar, att)`` with ``att ⊆ Ar × Ar``.
- ``S ⊆ Ar`` is *conflict-free* iff there are no ``a, b ∈ S`` with ``(a, b) ∈ att``.
- ``a`` is *acceptable* with respect to ``S`` (``S`` defends ``a``) iff for every ``b`` with
  ``(b, a) ∈ att`` there is ``c ∈ S`` with ``(c, b) ∈ att``.
- ``S`` is *admissible* iff it is conflict-free and every ``a ∈ S`` is acceptable w.r.t. ``S``.
- ``S`` is a *complete* extension iff it is admissible and contains every argument
  acceptable w.r.t. ``S``.
- The *grounded* extension is the least complete extension: the least fixed point of
  ``F(S) = {a | a is acceptable w.r.t. S}``.
- *Preferred* extensions are the ⊆-maximal complete extensions.
- *Stable* extensions are conflict-free sets attacking every argument outside them;
  every stable extension is complete (and preferred).

Algorithm: bitmask grounded-kernel fixed point followed by exact Caminada 3-valued
complete-labelling CNF enumeration over CaDiCaL 1.9.5 (`pysat.solvers.Solver("cadical195")`).
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Annotated, Final, Self, TypeGuard, cast

from pydantic import Field, model_validator
from pysat.solvers import Solver

from rdam._strict import StrictModel

DEFAULT_CAPACITY: Final = 128
"""Maximum number of arguments accepted by exact SAT enumeration."""

MAX_ENUMERATED_EXTENSIONS: Final = 4096
"""Hard cap on enumerated complete extensions before refusing combinatorial blowup."""


class FrameworkError(ValueError):
    """The supplied structure is not a well-formed argumentation framework."""


class FrameworkCapacityError(ValueError):
    """The framework exceeds the declared enumeration capacity."""


def _non_empty_string(value: object) -> TypeGuard[str]:
    return isinstance(value, str) and bool(value)


def _attack_pair(value: object) -> TypeGuard[tuple[str, str]]:
    if not isinstance(value, tuple):
        return False
    pair = cast(tuple[object, ...], value)
    if len(pair) != 2:
        return False
    return isinstance(pair[0], str) and isinstance(pair[1], str)


@dataclass(frozen=True, slots=True)
class ArgumentationFramework:
    """``AF = (Ar, att)`` with arguments kept in supplied order for deterministic output."""

    arguments: tuple[str, ...]
    attacks: frozenset[tuple[str, str]]

    def __post_init__(self) -> None:
        if not self.arguments:
            raise FrameworkError("arguments must be a non-empty tuple")
        known: set[str] = set()
        for argument in self.arguments:
            if not _non_empty_string(argument):
                raise FrameworkError("every argument must be a non-empty string")
            if argument in known:
                raise FrameworkError(f"duplicate argument: {argument!r}")
            known.add(argument)
        for attack in self.attacks:
            if not _attack_pair(attack):
                raise FrameworkError("every attack must be a two-element tuple of argument names")
            if attack[0] not in known or attack[1] not in known:
                raise FrameworkError(f"attack references an unknown argument: {attack!r}")

    @classmethod
    def from_payload(cls, payload: Mapping[str, object]) -> Self:
        """Validate ``{"arguments": [...], "attacks": [[from, to], ...]}``."""

        if set(payload) != {"arguments", "attacks"}:
            raise FrameworkError("framework requires exactly arguments and attacks")
        raw_arguments = payload.get("arguments")
        raw_attacks = payload.get("attacks")
        if not isinstance(raw_arguments, list) or not raw_arguments:
            raise FrameworkError("arguments must be a non-empty list")
        arguments: list[str] = []
        for item in cast(list[object], raw_arguments):
            if not isinstance(item, str) or not item:
                raise FrameworkError("every argument must be a non-empty string")
            if item in arguments:
                raise FrameworkError(f"duplicate argument: {item!r}")
            arguments.append(item)
        if not isinstance(raw_attacks, list):
            raise FrameworkError("attacks must be a list of [attacker, attacked] pairs")
        known = set(arguments)
        attacks: set[tuple[str, str]] = set()
        for pair in cast(list[object], raw_attacks):
            if not isinstance(pair, list):
                raise FrameworkError("every attack must be a two-element list of argument names")
            raw_pair = cast(list[object], pair)
            if len(raw_pair) != 2:
                raise FrameworkError("every attack must be a two-element list of argument names")
            if not isinstance(raw_pair[0], str) or not isinstance(raw_pair[1], str):
                raise FrameworkError("every attack must be a two-element list of argument names")
            typed_pair = cast(list[str], raw_pair)
            source, target = typed_pair
            if source not in known or target not in known:
                raise FrameworkError(f"attack references an unknown argument: {pair!r}")
            attacks.add((source, target))
        return cls(arguments=tuple(arguments), attacks=frozenset(attacks))

    def attackers_of(self, argument: str) -> frozenset[str]:
        return frozenset(source for source, target in self.attacks if target == argument)

    def attacked_by(self, arguments: Iterable[str]) -> frozenset[str]:
        sources = set(arguments)
        return frozenset(target for source, target in self.attacks if source in sources)

    def to_payload(self) -> dict[str, list[str] | list[list[str]]]:
        return {
            "arguments": list(self.arguments),
            "attacks": [list(pair) for pair in sorted(self.attacks)],
        }


def _bitmask_graph(framework: ArgumentationFramework) -> tuple[tuple[int, ...], tuple[int, ...]]:
    index_of = {arg: idx for idx, arg in enumerate(framework.arguments)}
    n = len(framework.arguments)
    attackers = [0] * n
    attacked = [0] * n
    for src, dst in framework.attacks:
        u = index_of[src]
        v = index_of[dst]
        attackers[v] |= 1 << u
        attacked[u] |= 1 << v
    return tuple(attackers), tuple(attacked)


def _grounded_masks(attackers: tuple[int, ...], attacked: tuple[int, ...]) -> tuple[int, int]:
    n = len(attackers)
    in_mask = 0
    while True:
        out_mask = 0
        cursor = in_mask
        while cursor:
            lsb = cursor & -cursor
            out_mask |= attacked[lsb.bit_length() - 1]
            cursor ^= lsb
        next_in = 0
        for i in range(n):
            if (attackers[i] & ~out_mask) == 0:
                next_in |= 1 << i
        if next_in == in_mask:
            return in_mask, out_mask
        in_mask = next_in


def _mask_to_frozenset(arguments: tuple[str, ...], mask: int) -> frozenset[str]:
    members: list[str] = []
    cursor = mask
    while cursor:
        lsb = cursor & -cursor
        members.append(arguments[lsb.bit_length() - 1])
        cursor ^= lsb
    return frozenset(members)


def is_conflict_free(framework: ArgumentationFramework, candidate: frozenset[str]) -> bool:
    return not any(source in candidate and target in candidate for source, target in framework.attacks)


def defends(framework: ArgumentationFramework, defenders: frozenset[str], argument: str) -> bool:
    attacked_by_defenders = framework.attacked_by(defenders)
    return all(attacker in attacked_by_defenders for attacker in framework.attackers_of(argument))


def acceptable_arguments(framework: ArgumentationFramework, defenders: frozenset[str]) -> frozenset[str]:
    """The characteristic function ``F(S)``."""
    return frozenset(argument for argument in framework.arguments if defends(framework, defenders, argument))


def is_admissible(framework: ArgumentationFramework, candidate: frozenset[str]) -> bool:
    return is_conflict_free(framework, candidate) and candidate <= acceptable_arguments(framework, candidate)


def is_complete(framework: ArgumentationFramework, candidate: frozenset[str]) -> bool:
    return is_conflict_free(framework, candidate) and candidate == acceptable_arguments(framework, candidate)


def is_stable(framework: ArgumentationFramework, candidate: frozenset[str]) -> bool:
    return is_conflict_free(framework, candidate) and (candidate | framework.attacked_by(candidate)) == frozenset(
        framework.arguments
    )


def grounded_extension(framework: ArgumentationFramework) -> frozenset[str]:
    """Least fixed point of ``F`` computed via integer bitmask propagation."""
    attackers, attacked = _bitmask_graph(framework)
    in_mask, _ = _grounded_masks(attackers, attacked)
    return _mask_to_frozenset(framework.arguments, in_mask)


@dataclass(frozen=True, slots=True)
class Semantics:
    """Every extension under each semantics, in a deterministic order."""

    grounded: frozenset[str]
    complete: tuple[frozenset[str], ...]
    preferred: tuple[frozenset[str], ...]
    stable: tuple[frozenset[str], ...]

    def to_payload(self, framework: ArgumentationFramework) -> dict[str, list[str] | list[list[str]]]:
        order = {argument: index for index, argument in enumerate(framework.arguments)}

        def members(extension: frozenset[str]) -> list[str]:
            return sorted(extension, key=order.__getitem__)

        return {
            "grounded": members(self.grounded),
            "complete": [members(item) for item in self.complete],
            "preferred": [members(item) for item in self.preferred],
            "stable": [members(item) for item in self.stable],
        }


class DungInput(StrictModel):
    """Caller-authored JSON shape; native reference/uniqueness rules still apply."""

    arguments: tuple[Annotated[str, Field(min_length=1)], ...] = Field(min_length=1)
    attacks: tuple[tuple[str, str], ...]

    @model_validator(mode="after")
    def valid_framework(self) -> Self:
        ArgumentationFramework.from_payload(self.model_dump(mode="json"))
        return self


def _ordered(framework: ArgumentationFramework, extensions: Iterable[frozenset[str]]) -> tuple[frozenset[str], ...]:
    order = {argument: index for index, argument in enumerate(framework.arguments)}
    return tuple(sorted(extensions, key=lambda item: (len(item), sorted(order[argument] for argument in item))))


def validate_capacity(capacity: object) -> int:
    """Return a valid enumeration capacity or reject invalid configuration."""
    if isinstance(capacity, bool) or not isinstance(capacity, int) or capacity <= 0:
        raise ValueError("exhaustive capacity must be a positive integer")
    return capacity


def _enumerate_complete_masks_sat(
    attackers: tuple[int, ...],
    attacked: tuple[int, ...],
) -> list[int]:
    """Exact Caminada 3-valued complete labelling CNF enumeration via CaDiCaL 1.9.5."""
    n = len(attackers)
    in_mask, out_mask = _grounded_masks(attackers, attacked)
    undecided_mask = ((1 << n) - 1) & ~(in_mask | out_mask)
    if undecided_mask == 0:
        return [in_mask]

    def x_var(i: int) -> int:
        return 2 * i + 1

    def y_var(i: int) -> int:
        return 2 * i + 2

    clauses: list[list[int]] = []
    for i in range(n):
        xi = x_var(i)
        yi = y_var(i)
        # Unit propagation from grounded kernel:
        if (in_mask >> i) & 1:
            clauses.append([xi])
            clauses.append([-yi])
            continue
        if (out_mask >> i) & 1:
            clauses.append([-xi])
            clauses.append([yi])
            continue
        if (attackers[i] >> i) & 1:
            # Self-attacking argument can never be IN.
            clauses.append([-xi])

        # 1. Conflict-freeness: x_i -> ~y_i
        clauses.append([-xi, -yi])

        preds: list[int] = []
        cursor = attackers[i]
        while cursor:
            lsb = cursor & -cursor
            preds.append(lsb.bit_length() - 1)
            cursor ^= lsb

        if not preds:
            clauses.append([xi])
            clauses.append([-yi])
        else:
            # 2. y_i <-> OR_{b in preds} x_b
            clauses.extend([-x_var(b), yi] for b in preds)
            clauses.append([-yi, *(x_var(b) for b in preds)])
            # 3. x_i <-> AND_{b in preds} y_b
            clauses.extend([-xi, y_var(b)] for b in preds)
            clauses.append([xi, *(-y_var(b) for b in preds)])

    masks: list[int] = []
    with Solver(name="cadical195", bootstrap_with=clauses) as solver:
        while solver.solve():
            if len(masks) >= MAX_ENUMERATED_EXTENSIONS:
                raise FrameworkCapacityError(
                    f"framework exceeds {MAX_ENUMERATED_EXTENSIONS} complete extensions; refusing combinatorial blowup"
                )
            model = solver.get_model()
            assert model is not None
            pos_vars = {lit for lit in model if lit > 0}
            ext_mask = 0
            blocking: list[int] = []
            for i in range(n):
                xi = x_var(i)
                if xi in pos_vars:
                    ext_mask |= 1 << i
                    blocking.append(-xi)
                else:
                    blocking.append(xi)
            masks.append(ext_mask)
            solver.add_clause(blocking)
    return masks


def complete_extensions(
    framework: ArgumentationFramework, *, capacity: int = DEFAULT_CAPACITY
) -> tuple[frozenset[str], ...]:
    """Every complete extension, solved exactly via CaDiCaL 1.9.5 CNF enumeration."""
    capacity = validate_capacity(capacity)
    count = len(framework.arguments)
    if count > capacity:
        raise FrameworkCapacityError(f"framework has {count} arguments; capacity is {capacity}")
    attackers, attacked = _bitmask_graph(framework)
    masks = _enumerate_complete_masks_sat(attackers, attacked)
    return _ordered(framework, (_mask_to_frozenset(framework.arguments, mask) for mask in masks))


def evaluate(framework: ArgumentationFramework, *, capacity: int = DEFAULT_CAPACITY) -> Semantics:
    """Grounded, complete, preferred, and stable extensions of one framework."""
    capacity = validate_capacity(capacity)
    count = len(framework.arguments)
    if count > capacity:
        raise FrameworkCapacityError(f"framework has {count} arguments; capacity is {capacity}")
    attackers, attacked = _bitmask_graph(framework)
    grounded_mask, _ = _grounded_masks(attackers, attacked)
    complete_masks = _enumerate_complete_masks_sat(attackers, attacked)
    all_mask = (1 << count) - 1

    preferred_masks = [
        m for m in complete_masks if not any(m != other and (m & other) == m for other in complete_masks)
    ]
    stable_masks: list[int] = []
    for m in preferred_masks:
        out_m = 0
        cursor = m
        while cursor:
            lsb = cursor & -cursor
            out_m |= attacked[lsb.bit_length() - 1]
            cursor ^= lsb
        if (m | out_m) == all_mask:
            stable_masks.append(m)

    args = framework.arguments
    return Semantics(
        grounded=_mask_to_frozenset(args, grounded_mask),
        complete=_ordered(args_fw := framework, (_mask_to_frozenset(args, m) for m in complete_masks)),
        preferred=_ordered(args_fw, (_mask_to_frozenset(args, m) for m in preferred_masks)),
        stable=_ordered(args_fw, (_mask_to_frozenset(args, m) for m in stable_masks)),
    )


__all__ = [
    "DEFAULT_CAPACITY",
    "MAX_ENUMERATED_EXTENSIONS",
    "ArgumentationFramework",
    "DungInput",
    "FrameworkCapacityError",
    "FrameworkError",
    "Semantics",
    "acceptable_arguments",
    "complete_extensions",
    "defends",
    "evaluate",
    "grounded_extension",
    "is_admissible",
    "is_complete",
    "is_conflict_free",
    "is_stable",
    "validate_capacity",
]

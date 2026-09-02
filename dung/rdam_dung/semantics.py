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

Argument content is deliberately abstracted away (FR-016): this module evaluates a
supplied framework and never derives one from text.

Algorithm: exhaustive subset enumeration under a declared capacity. For the frameworks a
single analyst supplies by hand this is exact, deterministic, and fast; larger inputs are
refused with a typed failure rather than approximated.
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Final, Self

DEFAULT_CAPACITY: Final = 14
"""Maximum number of arguments the exhaustive enumeration accepts (2^14 candidate sets)."""


class FrameworkError(ValueError):
    """The supplied structure is not a well-formed argumentation framework."""


class FrameworkCapacityError(ValueError):
    """The framework exceeds the declared enumeration capacity."""


@dataclass(frozen=True, slots=True)
class ArgumentationFramework:
    """``AF = (Ar, att)`` with arguments kept in supplied order for deterministic output."""

    arguments: tuple[str, ...]
    attacks: frozenset[tuple[str, str]]

    @classmethod
    def from_payload(cls, payload: Mapping[str, object]) -> Self:
        """Validate ``{"arguments": [...], "attacks": [[from, to], ...]}``."""

        raw_arguments = payload.get("arguments")
        raw_attacks = payload.get("attacks")
        if not isinstance(raw_arguments, list) or not raw_arguments:
            raise FrameworkError("arguments must be a non-empty list")
        arguments: list[str] = []
        for item in raw_arguments:
            if not isinstance(item, str) or not item:
                raise FrameworkError("every argument must be a non-empty string")
            if item in arguments:
                raise FrameworkError(f"duplicate argument: {item!r}")
            arguments.append(item)
        if not isinstance(raw_attacks, list):
            raise FrameworkError("attacks must be a list of [attacker, attacked] pairs")
        known = set(arguments)
        attacks: set[tuple[str, str]] = set()
        for pair in raw_attacks:
            if not isinstance(pair, list) or len(pair) != 2 or not all(isinstance(end, str) for end in pair):
                raise FrameworkError("every attack must be a two-element list of argument names")
            source, target = str(pair[0]), str(pair[1])
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
    return is_conflict_free(framework, candidate) and (candidate | framework.attacked_by(candidate)) == frozenset(framework.arguments)


def grounded_extension(framework: ArgumentationFramework) -> frozenset[str]:
    """Least fixed point of ``F`` by iteration from the empty set; ``F`` is monotone, so this terminates."""

    current: frozenset[str] = frozenset()
    while True:
        following = acceptable_arguments(framework, current)
        if following == current:
            return current
        current = following


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


def _ordered(framework: ArgumentationFramework, extensions: Iterable[frozenset[str]]) -> tuple[frozenset[str], ...]:
    order = {argument: index for index, argument in enumerate(framework.arguments)}
    return tuple(sorted(extensions, key=lambda item: (len(item), sorted(order[argument] for argument in item))))


def complete_extensions(framework: ArgumentationFramework, *, capacity: int = DEFAULT_CAPACITY) -> tuple[frozenset[str], ...]:
    """Every complete extension, by exhaustive enumeration of the ``2^|Ar|`` candidate sets."""

    count = len(framework.arguments)
    if count > capacity:
        raise FrameworkCapacityError(f"framework has {count} arguments; exhaustive capacity is {capacity}")
    found: list[frozenset[str]] = []
    for mask in range(1 << count):
        candidate = frozenset(argument for index, argument in enumerate(framework.arguments) if mask >> index & 1)
        if is_complete(framework, candidate):
            found.append(candidate)
    return _ordered(framework, found)


def evaluate(framework: ArgumentationFramework, *, capacity: int = DEFAULT_CAPACITY) -> Semantics:
    """Grounded, complete, preferred, and stable extensions of one framework."""

    complete = complete_extensions(framework, capacity=capacity)
    preferred = _ordered(
        framework,
        (item for item in complete if not any(item < other for other in complete)),
    )
    stable = _ordered(framework, (item for item in complete if is_stable(framework, item)))
    return Semantics(grounded=grounded_extension(framework), complete=complete, preferred=preferred, stable=stable)


__all__ = [
    "DEFAULT_CAPACITY",
    "ArgumentationFramework",
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
]

"""Dung semantics against the formal definitions: known frameworks, exhaustive small cases, random invariants.

These are the output-quality evidence for a formal technique (FR-022): correctness
arguments in the module docstring, property tests here.
"""

from itertools import product
import random

import pytest

from rdam.dung import ArgumentationFramework, FrameworkCapacityError, FrameworkError, evaluate, grounded_extension
from rdam.dung.semantics import acceptable_arguments, is_admissible, is_complete, is_conflict_free, is_stable


def af(arguments: str, *attacks: str) -> ArgumentationFramework:
    """``af("abc", "a>b", "b>c")``."""

    return ArgumentationFramework.from_payload(
        {"arguments": list(arguments), "attacks": [attack.split(">") for attack in attacks]}
    )


def sets(items: list[list[str]]) -> set[frozenset[str]]:
    return {frozenset(item) for item in items}


class TestKnownFrameworks:
    def test_single_unattacked_argument_is_in_every_extension(self) -> None:
        result = evaluate(af("a"))
        assert result.grounded == {"a"}
        assert result.complete == ({"a"},)
        assert result.preferred == ({"a"},)
        assert result.stable == ({"a"},)

    def test_simple_attack(self) -> None:
        result = evaluate(af("ab", "a>b"))
        assert result.grounded == {"a"}
        assert result.preferred == ({"a"},)
        assert result.stable == ({"a"},)

    def test_mutual_attack_has_empty_grounded_and_two_preferred(self) -> None:
        result = evaluate(af("ab", "a>b", "b>a"))
        assert result.grounded == frozenset()
        assert sets([list(item) for item in result.complete]) == {frozenset(), frozenset("a"), frozenset("b")}
        assert sets([list(item) for item in result.preferred]) == {frozenset("a"), frozenset("b")}
        assert sets([list(item) for item in result.stable]) == {frozenset("a"), frozenset("b")}

    def test_odd_cycle_has_no_stable_extension(self) -> None:
        result = evaluate(af("abc", "a>b", "b>c", "c>a"))
        assert result.grounded == frozenset()
        assert result.complete == (frozenset(),)
        assert result.preferred == (frozenset(),)
        assert result.stable == ()

    def test_self_attacker_is_never_accepted_and_reinstatement_works(self) -> None:
        # a attacks b, b attacks c: a reinstates c. d attacks itself.
        result = evaluate(af("abcd", "a>b", "b>c", "d>d"))
        assert result.grounded == {"a", "c"}
        assert "d" not in set().union(*result.complete)
        assert result.stable == (), "d is attacked by nobody in {a, c}, so no stable extension exists"

    def test_reinstatement_chain(self) -> None:
        result = evaluate(af("abcd", "a>b", "b>c", "c>d"))
        assert result.grounded == {"a", "c"}
        assert result.stable == ({"a", "c"},)


class TestValidation:
    def test_unknown_argument_in_attack_is_rejected(self) -> None:
        with pytest.raises(FrameworkError, match="unknown argument"):
            ArgumentationFramework.from_payload({"arguments": ["a"], "attacks": [["a", "b"]]})

    def test_duplicate_and_empty_arguments_are_rejected(self) -> None:
        with pytest.raises(FrameworkError, match="duplicate"):
            ArgumentationFramework.from_payload({"arguments": ["a", "a"], "attacks": []})
        with pytest.raises(FrameworkError, match="non-empty list"):
            ArgumentationFramework.from_payload({"arguments": [], "attacks": []})

    def test_capacity_is_enforced_not_approximated(self) -> None:
        big = ArgumentationFramework.from_payload({"arguments": [f"a{i}" for i in range(15)], "attacks": []})
        with pytest.raises(FrameworkCapacityError, match="capacity is 14"):
            evaluate(big)


def _invariants(framework: ArgumentationFramework) -> None:
    result = evaluate(framework)
    arguments = frozenset(framework.arguments)
    # Grounded is complete, is the least complete extension, and equals the intersection of all complete extensions.
    assert is_complete(framework, result.grounded)
    assert all(result.grounded <= extension for extension in result.complete)
    assert result.grounded == frozenset.intersection(*result.complete)
    assert result.grounded == grounded_extension(framework)
    # Every complete extension is admissible and closed under F.
    for extension in result.complete:
        assert is_admissible(framework, extension)
        assert acceptable_arguments(framework, extension) == extension
    # Preferred = maximal complete; there is at least one; each complete extension is contained in a preferred one.
    assert result.preferred
    assert all(not any(item < other for other in result.complete) for item in result.preferred)
    assert all(any(extension <= item for item in result.preferred) for extension in result.complete)
    # Stable ⊆ preferred, and each stable extension attacks every outsider.
    assert set(result.stable) <= set(result.preferred)
    for extension in result.stable:
        assert is_stable(framework, extension)
        assert extension | framework.attacked_by(extension) == arguments
    # Conflict-freeness everywhere.
    assert all(is_conflict_free(framework, extension) for extension in result.complete)


class TestInvariants:
    def test_exhaustively_over_every_framework_with_three_arguments(self) -> None:
        arguments = ["a", "b", "c"]
        pairs = [(x, y) for x in arguments for y in arguments]
        for choice in product((False, True), repeat=len(pairs)):
            attacks = [list(pair) for pair, chosen in zip(pairs, choice, strict=True) if chosen]
            _invariants(ArgumentationFramework.from_payload({"arguments": arguments, "attacks": attacks}))

    def test_random_frameworks_up_to_capacity_satisfy_the_definitions(self) -> None:
        generator = random.Random(2026)
        for _ in range(200):
            count = generator.randint(1, 8)
            arguments = [f"a{i}" for i in range(count)]
            attacks = [[x, y] for x in arguments for y in arguments if generator.random() < 0.3]
            _invariants(ArgumentationFramework.from_payload({"arguments": arguments, "attacks": attacks}))

    def test_output_is_deterministic_and_ordered(self) -> None:
        framework = af("cba", "a>b", "b>a")
        payload = evaluate(framework).to_payload(framework)
        assert payload == evaluate(framework).to_payload(framework)
        # c is unattacked, so it is in every extension; members and extensions follow the supplied order c, b, a.
        assert payload["preferred"] == [["c", "b"], ["c", "a"]], "extensions ordered by size then supplied argument order"

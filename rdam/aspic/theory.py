"""Deterministic ASPIC+ argumentation engine (Modgil & Prakken 2013) & Caminada–Amgoud (2007) rationality."""

from collections.abc import Mapping
from dataclasses import dataclass
from itertools import product
from typing import Annotated, Any, Final, Literal, Self, cast

from pydantic import Field, StringConstraints, ValidationError, model_validator

from rdam._grounding import GroundingCollector, QuoteRef
from rdam._strict import JsonValue, StrictModel, canonical_json_bytes
from rdam.dung.semantics import ArgumentationFramework, evaluate
from rdam.ingest.contracts.evidence import SourceEvidenceSpan

type NonEmpty = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
type OrderingPrinciple = Literal["last_link", "weakest_link"]
type SetComparison = Literal["elitist", "democratic"]
type AttackKind = Literal["undermining", "rebutting", "undercutting"]

DEFAULT_ARGUMENT_CAPACITY: Final = 128


class AspicError(ValueError):
    """Raised when an ASPIC+ theory violates well-formedness, capacity, or source grounding."""


class StrictRuleInput(StrictModel):
    id: NonEmpty
    antecedents: tuple[NonEmpty, ...] = Field(min_length=1)
    consequent: NonEmpty


class DefeasibleRuleInput(StrictModel):
    id: NonEmpty
    antecedents: tuple[NonEmpty, ...] = Field(min_length=1)
    consequent: NonEmpty


class ContraryPairInput(StrictModel):
    symbol: NonEmpty
    contrary: NonEmpty
    symmetric: bool = True

    @model_validator(mode="after")
    def non_self_contrary(self) -> Self:
        if self.symbol == self.contrary:
            raise ValueError(f"Symbol {self.symbol!r} cannot be its own contrary")
        return self


def _transitive_closure(pairs: tuple[tuple[str, str], ...]) -> set[tuple[str, str]]:
    adj: dict[str, set[str]] = {}
    for weaker, stronger in pairs:
        adj.setdefault(weaker, set()).add(stronger)
    closure: set[tuple[str, str]] = set()
    for start in adj:
        stack = list(adj[start])
        visited: set[str] = set()
        while stack:
            nxt = stack.pop()
            if nxt in visited:
                continue
            visited.add(nxt)
            closure.add((start, nxt))
            stack.extend(adj.get(nxt, ()))
    return closure


class AspicTheoryInput(StrictModel):
    axioms: tuple[NonEmpty, ...] = ()
    ordinary_premises: tuple[NonEmpty, ...] = ()
    strict_rules: tuple[StrictRuleInput, ...] = ()
    defeasible_rules: tuple[DefeasibleRuleInput, ...] = ()
    contraries: tuple[ContraryPairInput, ...] = ()
    premise_preferences: tuple[tuple[NonEmpty, NonEmpty], ...] = ()
    rule_preferences: tuple[tuple[NonEmpty, NonEmpty], ...] = ()
    ordering_principle: OrderingPrinciple = "last_link"
    set_comparison: SetComparison = "elitist"

    @model_validator(mode="after")
    def validate_theory(self) -> Self:
        axiom_set = set(self.axioms)
        ordinary_set = set(self.ordinary_premises)
        if len(axiom_set) != len(self.axioms):
            raise ValueError("Duplicate axiom in AspicTheoryInput.axioms")
        if len(ordinary_set) != len(self.ordinary_premises):
            raise ValueError("Duplicate premise in AspicTheoryInput.ordinary_premises")
        overlap = axiom_set & ordinary_set
        if overlap:
            raise ValueError(f"Axioms (Kn) and ordinary premises (Kp) must be disjoint: {sorted(overlap)}")

        strict_ids = [r.id for r in self.strict_rules]
        def_ids = [r.id for r in self.defeasible_rules]
        all_rule_ids = strict_ids + def_ids
        if len(set(all_rule_ids)) != len(all_rule_ids):
            raise ValueError("Rule IDs across strict_rules and defeasible_rules must be globally unique")

        def_id_set = set(def_ids)
        for w_prem, s_prem in self.premise_preferences:
            if w_prem not in ordinary_set or s_prem not in ordinary_set:
                raise ValueError(
                    f"premise_preferences ({w_prem!r}, {s_prem!r}) must reference ordinary_premises"
                )
        prem_closure = _transitive_closure(self.premise_preferences)
        if any(x == y for x, y in prem_closure):
            raise ValueError("premise_preferences must be irreflexive and acyclic")

        for w_rule, s_rule in self.rule_preferences:
            if w_rule not in def_id_set or s_rule not in def_id_set:
                raise ValueError(
                    f"rule_preferences ({w_rule!r}, {s_rule!r}) must reference defeasible_rules"
                )
        rule_closure = _transitive_closure(self.rule_preferences)
        if any(x == y for x, y in rule_closure):
            raise ValueError("rule_preferences must be irreflexive and acyclic")
        return self

    @classmethod
    def from_payload(cls, raw: Mapping[str, Any] | Any) -> Self:
        if not isinstance(raw, Mapping):
            raise AspicError("ASPIC+ structured_input must be a JSON object")
        try:
            return cls.model_validate_json(canonical_json_bytes(raw))
        except (ValidationError, TypeError, ValueError) as exc:
            raise AspicError(str(exc)) from exc


class PreferencePairProposal(StrictModel):
    weaker: NonEmpty
    stronger: NonEmpty


class GroundedPremiseProposal(StrictModel):
    symbol: NonEmpty
    kind: Literal["axiom", "ordinary"] = "ordinary"
    evidence: QuoteRef


class GroundedRuleProposal(StrictModel):
    id: NonEmpty
    kind: Literal["strict", "defeasible"] = "defeasible"
    antecedents: list[NonEmpty] = Field(min_length=1)
    consequent: NonEmpty
    evidence: QuoteRef


class ExtractedAspicProposal(StrictModel):
    premises: list[GroundedPremiseProposal] = Field(default_factory=list[GroundedPremiseProposal])
    rules: list[GroundedRuleProposal] = Field(default_factory=list[GroundedRuleProposal])
    contraries: list[ContraryPairInput] = Field(default_factory=list[ContraryPairInput])
    premise_preferences: list[PreferencePairProposal] = Field(default_factory=list[PreferencePairProposal])
    rule_preferences: list[PreferencePairProposal] = Field(default_factory=list[PreferencePairProposal])
    ordering_principle: OrderingPrinciple = "last_link"
    set_comparison: SetComparison = "elitist"

    @model_validator(mode="after")
    def check_well_formed_theory(self) -> Self:
        self.to_theory_input()
        return self

    def to_theory_input(self) -> AspicTheoryInput:
        axioms = tuple(p.symbol for p in self.premises if p.kind == "axiom")
        ordinary = tuple(p.symbol for p in self.premises if p.kind == "ordinary")
        strict_rules = tuple(
            StrictRuleInput(id=r.id, antecedents=tuple(r.antecedents), consequent=r.consequent)
            for r in self.rules
            if r.kind == "strict"
        )
        defeasible_rules = tuple(
            DefeasibleRuleInput(id=r.id, antecedents=tuple(r.antecedents), consequent=r.consequent)
            for r in self.rules
            if r.kind == "defeasible"
        )
        return AspicTheoryInput(
            axioms=axioms,
            ordinary_premises=ordinary,
            strict_rules=strict_rules,
            defeasible_rules=defeasible_rules,
            contraries=tuple(self.contraries),
            premise_preferences=tuple((p.weaker, p.stronger) for p in self.premise_preferences),
            rule_preferences=tuple((p.weaker, p.stronger) for p in self.rule_preferences),
            ordering_principle=self.ordering_principle,
            set_comparison=self.set_comparison,
        )

    def validate_source(
        self,
        source_text: str,
    ) -> tuple[dict[str, SourceEvidenceSpan], dict[str, SourceEvidenceSpan]]:
        collector = GroundingCollector(source_text)
        prem_spans: dict[str, SourceEvidenceSpan] = {}
        rule_spans: dict[str, SourceEvidenceSpan] = {}
        for idx, prem in enumerate(self.premises):
            span = collector.resolve(prem.evidence, field_name=f"premises[{idx}] ({prem.symbol}).evidence")
            if span is not None:
                prem_spans[prem.symbol] = span
        for idx, rule in enumerate(self.rules):
            span = collector.resolve(rule.evidence, field_name=f"rules[{idx}] ({rule.id}).evidence")
            if span is not None:
                rule_spans[rule.id] = span
        try:
            collector.raise_if_errors()
        except ValueError as exc:
            raise AspicError(str(exc)) from exc
        return prem_spans, rule_spans


@dataclass(frozen=True, slots=True)
class ConstructedArgument:
    id: str
    conclusion: str
    top_rule_id: str | None
    top_rule_strict: bool
    direct_sub_ids: tuple[str, ...]
    all_sub_ids: tuple[str, ...]
    ordinary_premises_used: tuple[str, ...]
    defeasible_rules_used: tuple[str, ...]
    last_defeasible_rules: tuple[str, ...]
    is_strict: bool
    is_firm: bool
    conclusions_in_tree: frozenset[str]


@dataclass(frozen=True, slots=True)
class AspicAttackRecord:
    attacker: str
    target: str
    on_sub_argument: str
    kind: AttackKind
    succeeded_as_defeat: bool


@dataclass(frozen=True, slots=True)
class RationalityPostulates:
    sub_argument_closure: bool
    strict_closure: bool
    direct_consistency: bool
    indirect_consistency: bool

    @property
    def all_satisfied(self) -> bool:
        return (
            self.sub_argument_closure
            and self.strict_closure
            and self.direct_consistency
            and self.indirect_consistency
        )


@dataclass(frozen=True, slots=True)
class AspicEvaluation:
    theory: AspicTheoryInput
    arguments: tuple[ConstructedArgument, ...]
    attacks: tuple[AspicAttackRecord, ...]
    defeats: tuple[tuple[str, str], ...]
    extensions: dict[str, JsonValue]
    rationality: RationalityPostulates


def _build_contrary_map(
    theory: AspicTheoryInput,
    known_symbols: set[str],
) -> tuple[dict[str, set[str]], set[tuple[str, str]]]:
    """Return `(contraries_of[target] -> set of attackers, symmetric_pairs)`."""
    contraries_of: dict[str, set[str]] = {}
    symmetric_pairs: set[tuple[str, str]] = set()

    for pair in theory.contraries:
        contraries_of.setdefault(pair.symbol, set()).add(pair.contrary)
        if pair.symmetric:
            contraries_of.setdefault(pair.contrary, set()).add(pair.symbol)
            symmetric_pairs.add((pair.symbol, pair.contrary))
            symmetric_pairs.add((pair.contrary, pair.symbol))

    # Classical prefix negation `~x` <-> `x`
    all_syms = set(known_symbols) | set(contraries_of) | {c for cs in contraries_of.values() for c in cs}
    for sym in list(all_syms):
        if sym.startswith("~") and len(sym) > 1:
            pos = sym[1:]
            contraries_of.setdefault(pos, set()).add(sym)
            contraries_of.setdefault(sym, set()).add(pos)
            symmetric_pairs.add((pos, sym))
            symmetric_pairs.add((sym, pos))
    return contraries_of, symmetric_pairs


def _set_strictly_less(
    set_gamma: tuple[str, ...],
    set_delta: tuple[str, ...],
    strict_order: set[tuple[str, str]],
    comparison: SetComparison,
) -> bool:
    """Evaluate `Gamma < Delta` under Modgil & Prakken (2013) Elitist or Democratic set comparison."""
    if not set_gamma:
        return False
    if not set_delta:
        return True
    if comparison == "elitist":
        # Exists x in Gamma such that for all y in Delta: x < y
        return any(all((x, y) in strict_order for y in set_delta) for x in set_gamma)
    # democratic: For all x in Gamma, exists y in Delta such that x < y
    return all(any((x, y) in strict_order for y in set_delta) for x in set_gamma)


def _strictly_preferred(
    arg_b: ConstructedArgument,
    arg_a: ConstructedArgument,
    *,
    prem_order: set[tuple[str, str]],
    rule_order: set[tuple[str, str]],
    principle: OrderingPrinciple,
    comparison: SetComparison,
) -> bool:
    """Return True iff `B > A` (`A < B`, so `A` is strictly weaker than `B` and fails to defeat `B`)."""
    if principle == "last_link":
        if not arg_a.last_defeasible_rules and not arg_b.last_defeasible_rules:
            return _set_strictly_less(
                arg_a.ordinary_premises_used,
                arg_b.ordinary_premises_used,
                prem_order,
                comparison,
            )
        if not arg_a.last_defeasible_rules:
            return False
        if not arg_b.last_defeasible_rules:
            return True
        return _set_strictly_less(
            arg_a.last_defeasible_rules,
            arg_b.last_defeasible_rules,
            rule_order,
            comparison,
        )

    # weakest_link
    if arg_a.is_strict and arg_b.is_strict:
        return _set_strictly_less(
            arg_a.ordinary_premises_used,
            arg_b.ordinary_premises_used,
            prem_order,
            comparison,
        )
    prem_ok = (
        True
        if (arg_a.is_firm and arg_b.is_firm)
        else _set_strictly_less(
            arg_a.ordinary_premises_used,
            arg_b.ordinary_premises_used,
            prem_order,
            comparison,
        )
    )
    rule_ok = (
        True
        if (arg_a.is_strict and arg_b.is_strict)
        else _set_strictly_less(
            arg_a.defeasible_rules_used,
            arg_b.defeasible_rules_used,
            rule_order,
            comparison,
        )
    )
    if arg_a.is_firm and not arg_b.is_firm:
        prem_ok = False
    if not arg_a.is_firm and arg_b.is_firm:
        prem_ok = True
    if arg_a.is_strict and not arg_b.is_strict:
        rule_ok = False
    if not arg_a.is_strict and arg_b.is_strict:
        rule_ok = True
    return prem_ok and rule_ok


def _strict_closure(formulas: set[str], strict_rules: tuple[StrictRuleInput, ...]) -> set[str]:
    closed = set(formulas)
    changed = True
    while changed:
        changed = False
        for rule in strict_rules:
            if rule.consequent not in closed and all(ant in closed for ant in rule.antecedents):
                closed.add(rule.consequent)
                changed = True
    return closed


def evaluate_aspic(
    theory: AspicTheoryInput,
    *,
    capacity: int = DEFAULT_ARGUMENT_CAPACITY,
) -> AspicEvaluation:
    """Construct ASPIC+ arguments, attacks, preference-filtered defeats, extensions, and rationality."""
    if capacity <= 0:
        raise AspicError("ASPIC+ argument capacity must be positive")

    args: list[ConstructedArgument] = []
    by_conclusion: dict[str, list[ConstructedArgument]] = {}
    seen_signatures: set[tuple[str | None, tuple[str, ...], str]] = set()

    def add_arg(arg: ConstructedArgument) -> None:
        if len(args) >= capacity:
            raise AspicError(f"ASPIC+ theory exceeds argument capacity ({capacity})")
        args.append(arg)
        by_conclusion.setdefault(arg.conclusion, []).append(arg)

    for axiom in theory.axioms:
        aid = f"a_{len(args) + 1}"
        sig = (None, (), axiom)
        seen_signatures.add(sig)
        add_arg(
            ConstructedArgument(
                id=aid,
                conclusion=axiom,
                top_rule_id=None,
                top_rule_strict=True,
                direct_sub_ids=(),
                all_sub_ids=(aid,),
                ordinary_premises_used=(),
                defeasible_rules_used=(),
                last_defeasible_rules=(),
                is_strict=True,
                is_firm=True,
                conclusions_in_tree=frozenset({axiom}),
            )
        )

    for prem in theory.ordinary_premises:
        aid = f"a_{len(args) + 1}"
        sig = (None, (), prem)
        seen_signatures.add(sig)
        add_arg(
            ConstructedArgument(
                id=aid,
                conclusion=prem,
                top_rule_id=None,
                top_rule_strict=True,
                direct_sub_ids=(),
                all_sub_ids=(aid,),
                ordinary_premises_used=(prem,),
                defeasible_rules_used=(),
                last_defeasible_rules=(),
                is_strict=True,
                is_firm=False,
                conclusions_in_tree=frozenset({prem}),
            )
        )

    all_rules: list[tuple[str, tuple[str, ...], str, bool]] = [
        *((r.id, r.antecedents, r.consequent, True) for r in theory.strict_rules),
        *((r.id, r.antecedents, r.consequent, False) for r in theory.defeasible_rules),
    ]

    added = True
    while added:
        added = False
        for rule_id, antecedents, consequent, is_strict_rule in all_rules:
            candidate_lists = [by_conclusion.get(ant, []) for ant in antecedents]
            if any(not lst for lst in candidate_lists):
                continue
            for combo in product(*candidate_lists):
                direct_ids = tuple(sub.id for sub in combo)
                sig = (rule_id, direct_ids, consequent)
                if sig in seen_signatures:
                    continue
                # Cycle-free derivation check
                combined_concs: frozenset[str] = frozenset[str]().union(
                    *(sub.conclusions_in_tree for sub in combo)
                )
                if consequent in combined_concs:
                    continue
                seen_signatures.add(sig)
                aid = f"a_{len(args) + 1}"
                all_sub = tuple(dict.fromkeys([*(sid for sub in combo for sid in sub.all_sub_ids), aid]))
                ord_prems = tuple(dict.fromkeys(p for sub in combo for p in sub.ordinary_premises_used))
                def_rules = tuple(
                    dict.fromkeys(
                        [*(r for sub in combo for r in sub.defeasible_rules_used), *(() if is_strict_rule else (rule_id,))]
                    )
                )
                if not is_strict_rule:
                    last_def = (rule_id,)
                else:
                    last_def = tuple(dict.fromkeys(r for sub in combo for r in sub.last_defeasible_rules))
                add_arg(
                    ConstructedArgument(
                        id=aid,
                        conclusion=consequent,
                        top_rule_id=rule_id,
                        top_rule_strict=is_strict_rule,
                        direct_sub_ids=direct_ids,
                        all_sub_ids=all_sub,
                        ordinary_premises_used=ord_prems,
                        defeasible_rules_used=def_rules,
                        last_defeasible_rules=last_def,
                        is_strict=is_strict_rule and all(sub.is_strict for sub in combo),
                        is_firm=all(sub.is_firm for sub in combo),
                        conclusions_in_tree=combined_concs | {consequent},
                    )
                )
                added = True

    arg_by_id = {arg.id: arg for arg in args}
    known_symbols = {arg.conclusion for arg in args} | {r.id for r in theory.defeasible_rules}
    contraries_of, symmetric_pairs = _build_contrary_map(theory, known_symbols)
    prem_order = _transitive_closure(theory.premise_preferences)
    rule_order = _transitive_closure(theory.rule_preferences)
    ordinary_set = set(theory.ordinary_premises)

    attack_records: list[AspicAttackRecord] = []
    defeat_set: set[tuple[str, str]] = set()

    for attacker in args:
        att_conc = attacker.conclusion
        for target in args:
            for sub_id in target.all_sub_ids:
                sub = arg_by_id[sub_id]
                # 1. Undermining on ordinary premise
                if (
                    sub.top_rule_id is None
                    and sub.conclusion in ordinary_set
                    and att_conc in contraries_of.get(sub.conclusion, set())
                ):
                    is_sym = (att_conc, sub.conclusion) in symmetric_pairs
                    succeeded = True
                    if is_sym and _strictly_preferred(
                        sub,
                        attacker,
                        prem_order=prem_order,
                        rule_order=rule_order,
                        principle=theory.ordering_principle,
                        comparison=theory.set_comparison,
                    ):
                        succeeded = False
                    attack_records.append(
                        AspicAttackRecord(
                            attacker=attacker.id,
                            target=target.id,
                            on_sub_argument=sub.id,
                            kind="undermining",
                            succeeded_as_defeat=succeeded,
                        )
                    )
                    if succeeded:
                        defeat_set.add((attacker.id, target.id))

                # 2. Rebutting & Undercutting on defeasible top rule
                if sub.top_rule_id is not None and not sub.top_rule_strict:
                    if att_conc in contraries_of.get(sub.conclusion, set()):
                        is_sym = (att_conc, sub.conclusion) in symmetric_pairs
                        succeeded = True
                        if is_sym and _strictly_preferred(
                            sub,
                            attacker,
                            prem_order=prem_order,
                            rule_order=rule_order,
                            principle=theory.ordering_principle,
                            comparison=theory.set_comparison,
                        ):
                            succeeded = False
                        attack_records.append(
                            AspicAttackRecord(
                                attacker=attacker.id,
                                target=target.id,
                                on_sub_argument=sub.id,
                                kind="rebutting",
                                succeeded_as_defeat=succeeded,
                            )
                        )
                        if succeeded:
                            defeat_set.add((attacker.id, target.id))

                    # Undercutting on rule name (always succeeds regardless of preferences)
                    rule_contraries = contraries_of.get(sub.top_rule_id, set()) | {f"~{sub.top_rule_id}"}
                    if att_conc in rule_contraries:
                        attack_records.append(
                            AspicAttackRecord(
                                attacker=attacker.id,
                                target=target.id,
                                on_sub_argument=sub.id,
                                kind="undercutting",
                                succeeded_as_defeat=True,
                            )
                        )
                        defeat_set.add((attacker.id, target.id))

    defeats_sorted = tuple(sorted(defeat_set))
    if args:
        framework = ArgumentationFramework(
            arguments=tuple(arg.id for arg in args),
            attacks=frozenset(defeats_sorted),
        )
        dung_sem = evaluate(framework, capacity=capacity)
        extensions_payload: dict[str, JsonValue] = cast(
            dict[str, JsonValue],
            dung_sem.to_payload(framework),
        )
        complete_exts: list[set[str]] = [set(ext) for ext in dung_sem.complete]
    else:
        extensions_payload = {
            "grounded": [],
            "complete": [[]],
            "preferred": [[]],
            "stable": [[]],
        }
        complete_exts = [set()]

    # Verify Caminada–Amgoud (2007) 4 rationality postulates across all complete extensions
    sub_closure_ok = True
    strict_closure_ok = True
    direct_cons_ok = True
    indirect_cons_ok = True

    def is_consistent(formulas: set[str]) -> bool:
        return all(not contraries_of.get(f, set()) & formulas for f in formulas)

    for ext in complete_exts:
        for aid in ext:
            if not set(arg_by_id[aid].all_sub_ids).issubset(ext):
                sub_closure_ok = False
        conc_ext = {arg_by_id[aid].conclusion for aid in ext}
        closed_conc = _strict_closure(conc_ext, theory.strict_rules)
        if closed_conc != conc_ext:
            strict_closure_ok = False
        if not is_consistent(conc_ext):
            direct_cons_ok = False
        if not is_consistent(closed_conc):
            indirect_cons_ok = False

    return AspicEvaluation(
        theory=theory,
        arguments=tuple(args),
        attacks=tuple(attack_records),
        defeats=defeats_sorted,
        extensions=extensions_payload,
        rationality=RationalityPostulates(
            sub_argument_closure=sub_closure_ok,
            strict_closure=strict_closure_ok,
            direct_consistency=direct_cons_ok,
            indirect_consistency=indirect_cons_ok,
        ),
    )


__all__ = [
    "DEFAULT_ARGUMENT_CAPACITY",
    "AspicAttackRecord",
    "AspicError",
    "AspicEvaluation",
    "AspicTheoryInput",
    "ConstructedArgument",
    "ContraryPairInput",
    "DefeasibleRuleInput",
    "ExtractedAspicProposal",
    "GroundedPremiseProposal",
    "GroundedRuleProposal",
    "OrderingPrinciple",
    "RationalityPostulates",
    "SetComparison",
    "StrictRuleInput",
    "evaluate_aspic",
]

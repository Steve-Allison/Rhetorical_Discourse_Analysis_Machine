"""The gIBIS link grammar: exhaustive type table, attachment rules, and the deliberation map.

Output-quality evidence for a formal technique (FR-022): the grammar is stated in the
module docstring; these tests check the validator against it exhaustively.
"""

from itertools import product

import pytest

from rdam.ibis import GRAMMAR, IbisStructure, Link, Node, NodeKind, Relation, StructureError, deliberation_map


def structure(nodes: dict[str, str], *links: tuple[str, str, str]) -> IbisStructure:
    """``structure({"i1": "issue", ...}, ("p1", "responds_to", "i1"), ...)``."""

    return IbisStructure.from_payload(
        {
            "nodes": [{"id": node_id, "kind": kind, "text": f"text of {node_id}"} for node_id, kind in nodes.items()],
            "links": [{"from": source, "relation": relation, "to": target} for source, relation, target in links],
        }
    )


class TestLinkTyping:
    @pytest.mark.parametrize(
        "node",
        (
            ("", NodeKind.ISSUE, "text"),
            ("i1", NodeKind.ISSUE, "   "),
        ),
    )
    def test_direct_node_construction_enforces_native_invariants(
        self,
        node: tuple[str, NodeKind, str],
    ) -> None:
        with pytest.raises(StructureError):
            Node(node_id=node[0], kind=node[1], text=node[2])

    def test_direct_link_construction_refuses_self_links(self) -> None:
        with pytest.raises(StructureError, match="self-link"):
            Link(source="i1", relation=Relation.QUESTIONS, target="i1")

    @pytest.mark.parametrize(
        "nodes, links",
        (
            (
                (Node("i1", NodeKind.ISSUE, "one"), Node("i1", NodeKind.ISSUE, "two")),
                (),
            ),
            (
                (Node("i1", NodeKind.ISSUE, "one"),),
                (Link("i1", Relation.QUESTIONS, "missing"),),
            ),
            (
                (Node("i1", NodeKind.ISSUE, "one"), Node("p1", NodeKind.POSITION, "position")),
                (
                    Link("p1", Relation.RESPONDS_TO, "i1"),
                    Link("p1", Relation.RESPONDS_TO, "i1"),
                ),
            ),
        ),
    )
    def test_direct_structure_construction_enforces_graph_invariants(
        self,
        nodes: tuple[Node, ...],
        links: tuple[Link, ...],
    ) -> None:
        with pytest.raises(StructureError):
            IbisStructure(nodes=nodes, links=links)

    def test_every_relation_by_kind_pair_is_accepted_exactly_when_the_grammar_permits_it(self) -> None:
        """All 3 × 3 × 8 combinations: the validator's verdict equals the grammar table."""

        for from_kind, to_kind, relation in product(NodeKind, NodeKind, Relation):
            permitted_from, permitted_to = GRAMMAR[relation]
            permitted = from_kind is permitted_from and to_kind in permitted_to
            nodes = {"i0": "issue", "p0": "position", "a0": "argument"}
            # Anchor the position and argument so attachment rules do not mask the typing rule.
            base = [("p0", "responds_to", "i0"), ("a0", "supports", "p0")]
            source = {NodeKind.ISSUE: "i0", NodeKind.POSITION: "p0", NodeKind.ARGUMENT: "a0"}[from_kind]
            target_id = {NodeKind.ISSUE: "i1", NodeKind.POSITION: "p1", NodeKind.ARGUMENT: "a1"}[to_kind]
            nodes[target_id] = to_kind.value
            extra = [("p1", "responds_to", "i0")] if to_kind is NodeKind.POSITION else []
            extra += [("a1", "supports", "p0")] if to_kind is NodeKind.ARGUMENT else []
            links = [*base, *extra, (source, relation.value, target_id)]
            if relation in {Relation.RESPONDS_TO, Relation.SUPPORTS, Relation.OBJECTS_TO} and permitted:
                # A second attachment link would break the exactly-one rule; test typing on a fresh node instead.
                fresh = {NodeKind.POSITION: ("p9", "position"), NodeKind.ARGUMENT: ("a9", "argument")}[from_kind]
                nodes[fresh[0]] = fresh[1]
                links = [*base, *extra, (fresh[0], relation.value, target_id)]
            try:
                structure(nodes, *links)
            except StructureError as error:
                assert not permitted, f"{from_kind.value} --{relation.value}--> {to_kind.value} should be permitted: {error}"
            else:
                assert permitted, f"{from_kind.value} --{relation.value}--> {to_kind.value} should be refused"

    def test_self_links_and_unknown_nodes_are_refused(self) -> None:
        with pytest.raises(StructureError, match="self-link"):
            structure({"i1": "issue"}, ("i1", "questions", "i1"))
        with pytest.raises(StructureError, match="unknown node"):
            structure({"i1": "issue"}, ("i1", "questions", "zz"))


class TestAttachment:
    def test_a_position_responds_to_exactly_one_issue(self) -> None:
        with pytest.raises(StructureError, match="exactly one responds_to"):
            structure({"i1": "issue", "p1": "position"})
        with pytest.raises(StructureError, match="exactly one responds_to"):
            structure({"i1": "issue", "i2": "issue", "p1": "position"}, ("p1", "responds_to", "i1"), ("p1", "responds_to", "i2"))

    def test_an_argument_attaches_to_exactly_one_position(self) -> None:
        with pytest.raises(StructureError, match="exactly one objects_to or supports"):
            structure({"i1": "issue", "p1": "position", "a1": "argument"}, ("p1", "responds_to", "i1"))
        with pytest.raises(StructureError, match="exactly one objects_to or supports"):
            structure(
                {"i1": "issue", "p1": "position", "a1": "argument"},
                ("p1", "responds_to", "i1"),
                ("a1", "supports", "p1"),
                ("a1", "objects_to", "p1"),
            )

    def test_issues_need_no_attachment(self) -> None:
        assert len(structure({"i1": "issue", "i2": "issue"}).nodes) == 2


class TestDeliberationMap:
    def test_map_organises_what_was_said_without_judging_it(self) -> None:
        built = structure(
            {"i1": "issue", "p1": "position", "p2": "position", "a1": "argument", "a2": "argument", "a3": "argument", "i2": "issue"},
            ("p1", "responds_to", "i1"),
            ("p2", "responds_to", "i1"),
            ("a1", "supports", "p1"),
            ("a2", "objects_to", "p1"),
            ("a3", "supports", "p2"),
            ("i2", "questions", "a2"),
            ("i2", "is_suggested_by", "p1"),
        )
        result = deliberation_map(built)
        issues = result["issues"]
        assert isinstance(issues, list)
        first = issues[0]
        assert isinstance(first, dict)
        assert first["id"] == "i1"
        assert first["positions"] == [
            {"id": "p1", "supporting": ["a1"], "objecting": ["a2"]},
            {"id": "p2", "supporting": ["a3"], "objecting": []},
        ]
        second = issues[1]
        assert isinstance(second, dict)
        assert second["questions"] == ["a2"] and second["raised_by"] == ["p1"]
        assert result["issues_without_positions"] == ["i2"]
        assert result["positions_without_arguments"] == []
        assert result["isolated_nodes"] == []

    def test_observations_name_the_gaps(self) -> None:
        built = structure({"i1": "issue", "p1": "position", "i2": "issue"}, ("p1", "responds_to", "i1"))
        result = deliberation_map(built)
        assert result["issues_without_positions"] == ["i2"]
        assert result["positions_without_arguments"] == ["p1"]
        assert result["isolated_nodes"] == ["i2"]

    def test_payload_round_trips_the_structure_exactly(self) -> None:
        built = structure({"i1": "issue", "p1": "position"}, ("p1", "responds_to", "i1"))
        again = IbisStructure.from_payload(built.to_payload())
        assert again == built

"""Native Rhetorical Structure Theory (RST) tree annotations and RS3 serialization.

This module provides the native Mode A Python 3.14 implementation of
:class:`DiscourseUnit` and its accompanying RS3 XML exporters, replacing the
external legacy ``isanlp`` package dependency.
"""

from collections.abc import Sequence
from pathlib import Path
import sys
import types


class DiscourseUnit:
    """A node in a binary Rhetorical Structure Theory (RST) discourse tree."""

    __slots__ = (
        "_exporter",
        "end",
        "entropy",
        "id",
        "left",
        "nuclearity",
        "proba",
        "relation",
        "right",
        "start",
        "text",
    )

    id: int | None
    left: DiscourseUnit | None
    right: DiscourseUnit | None
    relation: str
    nuclearity: str
    proba: float | None
    entropy: float | None
    start: int | None
    end: int | None
    text: str
    _exporter: Exporter | None

    def __init__(
        self,
        id: int | None = None,
        left: DiscourseUnit | None = None,
        right: DiscourseUnit | None = None,
        text: str = "",
        start: int | None = None,
        end: int | None = None,
        orig_text: str | None = None,
        relation: str = "",
        nuclearity: str = "",
        proba: float | None = None,
        entropy: float | None = None,
    ) -> None:
        self.id = id
        self.left = left
        self.right = right
        self.relation = relation
        self.nuclearity = nuclearity
        self.proba = proba
        self.entropy = entropy
        self.start = start
        self.end = end

        if self.left is not None and self.right is not None:
            self.start = left.start if left is not None else None
            self.end = right.end if right is not None else None

        if orig_text is not None and self.start is not None and self.end is not None:
            self.text = orig_text[self.start : self.end]
        else:
            self.text = text.strip()

        self._exporter = None

    def __str__(self) -> str:
        left_text = self.left.text if self.left is not None else None
        right_text = self.right.text if self.right is not None else None
        return (
            f"id: {self.id}\n"
            f"text: {self.text}\n"
            f"proba: {self.proba}\n"
            f"entropy: {self.entropy}\n"
            f"relation: {self.relation}\n"
            f"nuclearity: {self.nuclearity}\n"
            f"left: {left_text}\n"
            f"right: {right_text}\n"
            f"start: {self.start}\n"
            f"end: {self.end}"
        )

    def __repr__(self) -> str:
        return f"(id={self.id}, start={self.start}, end={self.end})"

    def clear_textfields(self) -> None:
        """Clear text across an arbitrarily deep tree without using the call stack."""
        pending: list[DiscourseUnit] = [self]
        while pending:
            node = pending.pop()
            node.text = ""
            if node.right is not None:
                pending.append(node.right)
            if node.left is not None:
                pending.append(node.left)

    def fill_textfields(self, full_text: str) -> None:
        """Populate text across an arbitrarily deep tree from character spans."""
        pending: list[DiscourseUnit] = [self]
        while pending:
            node = pending.pop()
            if node.start is not None and node.end is not None:
                node.text = full_text[node.start : node.end]
            if node.right is not None:
                pending.append(node.right)
            if node.left is not None:
                pending.append(node.left)

    def to_rs3(self, filename: str | Path, encoding: str = "utf8") -> None:
        """Serialize this discourse tree to RS3 XML format."""
        self._exporter = Exporter(encoding=encoding)
        self._exporter(self, filename)


class Segment:
    """An elementary discourse unit (EDU) leaf element for RS3 XML."""

    __slots__ = ("id", "parent", "relname", "text")

    id: int
    parent: int
    relname: str
    text: str

    def __init__(self, _id: int | None, parent: int | None, relname: str, text: str) -> None:
        self.id = (_id if _id is not None else 0) + 1
        self.parent = (parent if parent is not None else -2) + 1
        self.relname = relname
        self.text = self._xmlize_edu(text)

    @staticmethod
    def _xmlize_edu(text: str) -> str:
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def __str__(self) -> str:
        if self.parent != -1:
            return f'<segment id="{self.id}" parent="{self.parent}" relname="{self.relname}">{self.text}</segment>'
        return f'<segment id="{self.id}">{self.text}</segment>'


class Group:
    """A composite structural group element for RS3 XML."""

    __slots__ = ("id", "parent", "relname", "type")

    id: int
    type: str
    parent: int
    relname: str

    def __init__(self, _id: int | None, type: str, parent: int | None, relname: str) -> None:
        self.id = (_id if _id is not None else 0) + 1
        self.type = type
        self.parent = (parent if parent is not None else -2) + 1
        self.relname = relname

    def __str__(self) -> str:
        return f'<group id="{self.id}" type="{self.type}" parent="{self.parent}" relname="{self.relname}"/>'


class Root(Group):
    """A root group element for RS3 XML."""

    __slots__ = ()

    def __init__(self, _id: int | None, type: str = "span") -> None:
        super().__init__(_id, type=type, parent=-1, relname="span")

    def __str__(self) -> str:
        return f'<group id="{self.id}" type="{self.type}"/>'


class Exporter:
    """RS3 XML document exporter for a single DiscourseUnit tree."""

    __slots__ = ("_encoding", "verbose")

    _encoding: str
    verbose: bool

    def __init__(self, encoding: str = "utf8", verbose: bool = False) -> None:
        self._encoding = encoding
        self.verbose = verbose

    def __call__(self, tree: DiscourseUnit, filename: str | Path) -> None:
        path = Path(filename)
        content = "<rst>\n" + self.make_header(tree) + self.make_body(tree) + "</rst>"
        path.write_text(content, encoding=self._encoding)

    def compile_relation_set(self, tree: DiscourseUnit) -> list[str]:
        result = ["antithesis_NN"]
        pending = [tree]
        while pending:
            node = pending.pop()
            result.append(f"{node.relation}_{node.nuclearity}")
            if node.left is None:
                continue
            if node.right is not None and node.right.left is not None:
                pending.append(node.right)
            if node.left.left is not None:
                pending.append(node.left)
        return result

    def make_header(self, tree: DiscourseUnit, whole_set: bool = False) -> str:
        if whole_set:
            canonical_relations = sorted(
                [
                    "preparation",
                    "cause-effect",
                    "solutionhood",
                    "condition",
                    "sequence",
                    "same-unit",
                    "background",
                    "interpretation-evaluation",
                    "contrast",
                    "evidence",
                    "joint",
                    "elaboration",
                    "purpose",
                    "attribution",
                    "concession",
                    "restatement",
                    "comparison",
                ]
            )
            relations = [f"{r}_NS" for r in canonical_relations]
        else:
            raw = self.compile_relation_set(tree)
            relations = ["antithesis_NN" if r == "elementary__" else r for r in raw]

        rel_map: dict[str, str] = {}
        for rel in relations:
            parts = rel.split("_")
            if len(parts) < 2:
                continue
            name, suffix = "_".join(parts[:-1]), parts[-1]
            rtype = "multinuc" if suffix == "NN" else "rst"
            rel_map[name] = "multinuc" if (name in rel_map and rel_map[name] == "multinuc") else rtype

        lines = ["\t<header>", "\t\t<relations>"]
        lines.extend(f'\t\t\t<rel name="{name}" type="{rel_map[name]}" />' for name in sorted(rel_map))
        lines += ["\t\t</relations>", "\t</header>", ""]
        return "\n".join(lines)

    def make_body(self, tree: DiscourseUnit) -> str:
        groups, edus = self.get_groups_and_edus(tree, terminal=True)
        lines = ["\t<body>"]
        lines.extend(f"\t\t{item}" for item in edus + groups)
        lines.append("\t</body>\n")
        return "\n".join(lines)

    def get_groups_and_edus(
        self,
        tree: DiscourseUnit,
        terminal: bool = False,
    ) -> tuple[list[Group], list[Segment]]:
        groups: list[Group] = []
        edus: list[Segment] = []
        if tree.left is None:
            return groups, [Segment(tree.id, parent=-2, relname="", text=tree.text)]

        if tree.right is None:
            raise ValueError("Binary DiscourseUnit must have both left and right children.")
        pending: list[tuple[DiscourseUnit, DiscourseUnit, bool]] = [
            (tree, tree.right, False),
            (tree, tree.left, True),
        ]
        while pending:
            node, child, is_left = pending.pop()
            if node.left is None or node.right is None:
                raise ValueError("Binary DiscourseUnit must have both left and right children.")
            if node.nuclearity == "SN":
                parent = node.right.id if is_left else node.id
                relname = node.relation if is_left else "span"
            elif node.nuclearity == "NS":
                parent = node.id if is_left else node.left.id
                relname = "span" if is_left else node.relation
            else:
                parent = node.id
                relname = node.relation
            if child.left is None:
                edus.append(Segment(child.id, parent=parent, relname=relname, text=child.text))
                continue
            if child.right is None:
                raise ValueError("Binary DiscourseUnit must have both left and right children.")
            type_ = "multinuc" if child.nuclearity == "NN" else "span"
            groups.append(Group(child.id, type=type_, parent=parent, relname=relname))
            pending.append((child, child.right, False))
            pending.append((child, child.left, True))

        if terminal and len(edus) > 1:
            if tree.nuclearity == "NN":
                groups.append(Root(tree.id, type="multinuc"))
            else:
                groups.append(Root(tree.id))

        return groups, edus


class ForestExporter:
    """RS3 XML exporter for a collection of DiscourseUnit trees."""

    __slots__ = ("_encoding", "_tree_exporter", "verbose")

    _encoding: str
    verbose: bool
    _tree_exporter: Exporter

    def __init__(self, encoding: str = "cp1251", verbose: bool = False) -> None:
        self._encoding = encoding
        self.verbose = verbose
        self._tree_exporter = Exporter(self._encoding, verbose=verbose)

    def __call__(self, trees: Sequence[DiscourseUnit], filename: str | Path) -> None:
        path = Path(filename)
        content = "<rst>\n" + self.make_header(trees) + self.make_body(trees) + "</rst>"
        path.write_text(content, encoding=self._encoding)

    def compile_relation_set(self, trees: Sequence[DiscourseUnit]) -> list[str]:
        result: list[str] = []
        for tree in trees:
            result.extend(self._tree_exporter.compile_relation_set(tree))
        deduped = sorted(set(result))
        return ["antithesis_NN" if r == "elementary__" else r for r in deduped]

    def make_header(self, trees: Sequence[DiscourseUnit]) -> str:
        relations = self.compile_relation_set(trees)
        lines = ["\t<header>", "\t\t<relations>"]
        for rel in relations:
            parts = rel.split("_")
            if len(parts) < 2:
                continue
            relname, type_ = "_".join(parts[:-1]), parts[-1]
            rtype = "multinuc" if type_ == "NN" else "rst"
            lines.append(f'\t\t\t<rel name="{relname}" type="{rtype}" />')
        lines += ["\t\t</relations>", "\t</header>", ""]
        return "\n".join(lines)

    def make_body(self, trees: Sequence[DiscourseUnit]) -> str:
        groups: list[Group] = []
        edus: list[Segment] = []

        for tree in trees:
            groups_, edus_ = self._tree_exporter.get_groups_and_edus(tree, terminal=True)
            if len(edus_) > 1:
                if tree.nuclearity == "NN":
                    groups.append(Root(tree.id, type="multinuc"))
                else:
                    groups.append(Root(tree.id))
            groups += groups_
            edus += edus_

        lines = ["\t<body>"]
        lines.extend(f"\t\t{str(item).replace('―', '-')}" for item in edus + groups)
        lines.append("\t</body>\n")
        return "\n".join(lines)


def register_isanlp_compat() -> None:
    """Register transparent `isanlp.annotation_rst` in sys.modules if not present."""
    if "isanlp" not in sys.modules:
        isanlp_pkg = types.ModuleType("isanlp")
        isanlp_pkg.__package__ = "isanlp"
        isanlp_pkg.__path__ = []
        sys.modules["isanlp"] = isanlp_pkg
    if "isanlp.annotation_rst" not in sys.modules:
        this_module = sys.modules[__name__]
        sys.modules["isanlp.annotation_rst"] = this_module
        sys.modules["isanlp"].__dict__["annotation_rst"] = this_module


# Auto-register on import
register_isanlp_compat()

__all__ = [
    "DiscourseUnit",
    "Exporter",
    "ForestExporter",
    "Group",
    "Root",
    "Segment",
    "register_isanlp_compat",
]

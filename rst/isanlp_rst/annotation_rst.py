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
        "id",
        "left",
        "right",
        "relation",
        "nuclearity",
        "proba",
        "entropy",
        "start",
        "end",
        "text",
        "_exporter",
    )

    id: int | None
    left: "DiscourseUnit | None"
    right: "DiscourseUnit | None"
    relation: str
    nuclearity: str
    proba: float | None
    entropy: float | None
    start: int | None
    end: int | None
    text: str
    _exporter: "Exporter | None"

    def __init__(
        self,
        id: int | None = None,
        left: "DiscourseUnit | None" = None,
        right: "DiscourseUnit | None" = None,
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
        """Recursively clear the text attribute across the tree to save memory."""
        self.text = ""
        if self.left is not None:
            self.left.clear_textfields()
        if self.right is not None:
            self.right.clear_textfields()

    def fill_textfields(self, full_text: str) -> None:
        """Recursively populate the text attribute from full_text using node character spans."""
        if self.start is not None and self.end is not None:
            self.text = full_text[self.start : self.end]
        if self.left is not None:
            self.left.fill_textfields(full_text)
        if self.right is not None:
            self.right.fill_textfields(full_text)

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

    __slots__ = ("id", "type", "parent", "relname")

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
        result = [f"{tree.relation}_{tree.nuclearity}", "antithesis_NN"]
        if tree.left is None:
            return result
        if tree.left.left is not None:
            result += self.compile_relation_set(tree.left)
        if tree.right is not None and tree.right.left is not None:
            result += self.compile_relation_set(tree.right)
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
        for name in sorted(rel_map):
            lines.append(f'\t\t\t<rel name="{name}" type="{rel_map[name]}" />')
        lines += ["\t\t</relations>", "\t</header>", ""]
        return "\n".join(lines)

    def make_body(self, tree: DiscourseUnit) -> str:
        groups, edus = self.get_groups_and_edus(tree, terminal=True)
        lines = ["\t<body>"]
        for item in edus + groups:
            lines.append(f"\t\t{item}")
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
            edus.append(Segment(tree.id, parent=-2, relname="", text=tree.text))
            return groups, edus

        assert tree.right is not None, "Binary DiscourseUnit must have both left and right children."

        # Processing left child
        if tree.left.left is None:
            if tree.nuclearity == "SN":
                edus.append(Segment(tree.left.id, parent=tree.right.id, relname=tree.relation, text=tree.left.text))
            elif tree.nuclearity == "NS":
                edus.append(Segment(tree.left.id, parent=tree.id, relname="span", text=tree.left.text))
            else:
                edus.append(Segment(tree.left.id, parent=tree.id, relname=tree.relation, text=tree.left.text))
        else:
            _type = "multinuc" if tree.left.nuclearity == "NN" else "span"
            if tree.nuclearity == "SN":
                groups.append(Group(tree.left.id, type=_type, parent=tree.right.id, relname=tree.relation))
            elif tree.nuclearity == "NS":
                groups.append(Group(tree.left.id, type=_type, parent=tree.id, relname="span"))
            else:
                groups.append(Group(tree.left.id, type=_type, parent=tree.id, relname=tree.relation))
            _groups, _edus = self.get_groups_and_edus(tree.left)
            groups += _groups
            edus += _edus

        # Processing right child
        if tree.right.left is None:
            if tree.nuclearity == "SN":
                edus.append(Segment(tree.right.id, parent=tree.id, relname="span", text=tree.right.text))
            elif tree.nuclearity == "NS":
                edus.append(Segment(tree.right.id, parent=tree.left.id, relname=tree.relation, text=tree.right.text))
            else:
                edus.append(Segment(tree.right.id, parent=tree.id, relname=tree.relation, text=tree.right.text))
        else:
            _type = "multinuc" if tree.right.nuclearity == "NN" else "span"
            if tree.nuclearity == "SN":
                groups.append(Group(tree.right.id, type=_type, parent=tree.id, relname="span"))
            elif tree.nuclearity == "NS":
                groups.append(Group(tree.right.id, type=_type, parent=tree.left.id, relname=tree.relation))
            else:
                groups.append(Group(tree.right.id, type=_type, parent=tree.id, relname=tree.relation))
            _groups, _edus = self.get_groups_and_edus(tree.right)
            groups += _groups
            edus += _edus

        if terminal and len(edus) > 1:
            if tree.nuclearity == "NN":
                groups.append(Root(tree.id, type="multinuc"))
            else:
                groups.append(Root(tree.id))

        return groups, edus


class ForestExporter:
    """RS3 XML exporter for a collection of DiscourseUnit trees."""

    __slots__ = ("_encoding", "verbose", "_tree_exporter")

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
            _relname, _type = "_".join(parts[:-1]), parts[-1]
            rtype = "multinuc" if _type == "NN" else "rst"
            lines.append(f'\t\t\t<rel name="{_relname}" type="{rtype}" />')
        lines += ["\t\t</relations>", "\t</header>", ""]
        return "\n".join(lines)

    def make_body(self, trees: Sequence[DiscourseUnit]) -> str:
        groups: list[Group] = []
        edus: list[Segment] = []

        for tree in trees:
            _groups, _edus = self._tree_exporter.get_groups_and_edus(tree, terminal=True)
            if len(_edus) > 1:
                if tree.nuclearity == "NN":
                    groups.append(Root(tree.id, type="multinuc"))
                else:
                    groups.append(Root(tree.id))
            groups += _groups
            edus += _edus

        lines = ["\t<body>"]
        for item in edus + groups:
            lines.append(f"\t\t{str(item).replace('―', '-')}")
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

"""RST tree node types and parent-chain attribute walks."""

from dataclasses import dataclass, field


@dataclass(slots=True)
class NODE:
    """EDU, span, or multinuc node used while importing and laying out a tree."""

    id: str
    left: int | float
    right: int | float
    parent: str
    depth: int | float
    kind: str
    text: str
    relname: str
    relkind: str
    sortdepth: int | float = field(init=False)

    def __post_init__(self) -> None:
        self.sortdepth = self.depth


@dataclass(frozen=True, slots=True)
class SEGMENT:
    """EDU used by the segmenter, not by the structurer."""

    id: str
    text: str
    tokens: list[str] = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "tokens", self.text.split(" "))


type NodeMap = dict[str, NODE]


def get_depth(orig_node: NODE, probe_node: NODE, nodes: NodeMap) -> None:
    """Set graphical nesting depth of ``orig_node`` from the parent chain.

    RST parentage without span/multinuc does not increase ``depth``.
    Mutates ``orig_node.depth`` and ``orig_node.sortdepth``; returns None.
    """
    current = probe_node
    while current.parent != "0":
        parent = nodes[current.parent]
        if parent.kind != "edu" and (
            current.relname == "span" or (parent.kind == "multinuc" and current.relkind == "multinuc")
        ):
            orig_node.depth += 1
            orig_node.sortdepth += 1
        elif parent.kind == "edu":
            orig_node.sortdepth += 1
        current = parent


def get_left_right(
    node_id: str,
    nodes: NodeMap,
    min_left: int | float,
    max_right: int | float,
    rel_hash: dict[str, str],
) -> None:
    """Walk toward the root, expanding each ancestor's left/right EDU span.

    For EDUs this is the EDU's own index. For spans and multinucs, the
    leftmost and rightmost dominated child is accumulated along the parent chain.
    """
    current_id = node_id
    while nodes[current_id].parent != "0" and current_id != "0":
        node = nodes[current_id]
        parent = nodes[node.parent]
        if min_left > node.left or min_left == 0:
            if node.left != 0:
                min_left = node.left
        if max_right < node.right or max_right == 0:
            max_right = node.right
        if node.relname == "span":
            if parent.left > min_left or parent.left == 0:
                parent.left = min_left
            if parent.right < max_right:
                parent.right = max_right
        elif node.relname in rel_hash:
            if parent.kind == "multinuc" and rel_hash[node.relname] == "multinuc":
                if parent.left > min_left or parent.left == 0:
                    parent.left = min_left
                if parent.right < max_right:
                    parent.right = max_right
        current_id = parent.id

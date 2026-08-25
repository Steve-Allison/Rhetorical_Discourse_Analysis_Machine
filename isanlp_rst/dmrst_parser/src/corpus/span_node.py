from typing import Any


class SpanNode:
    """RST tree node used by the DMRST corpus readers."""

    def __init__(self, prop: str | None) -> None:
        self.text: Any = None
        self.relation: Any = None
        self.eduspan: Any = None
        self.nucspan: Any = None
        self.nucedu: Any = None
        self.prop = prop
        self.lnode: SpanNode | None = None
        self.rnode: SpanNode | None = None
        self.pnode: SpanNode | None = None
        self.nodelist: list[SpanNode] = []
        self.form: str | None = None
        self.eduCovered: Any = []
        self._id: Any = None
        self.eduSpan: Any = None
        self.position: Any = None

    def __str__(self) -> str:
        return self._info() + "\n" + "\n".join("\t" + node._info() for node in self.nodelist)

    def _info(self) -> str:
        return "eduspan: " + str(self.eduspan)

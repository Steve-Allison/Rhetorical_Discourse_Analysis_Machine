from collections.abc import Iterable, Sequence
from types import TracebackType
from typing import Self

class Solver:
    def __init__(
        self,
        name: str = ...,
        bootstrap_with: Iterable[Sequence[int]] | None = ...,
        use_timer: bool = ...,
    ) -> None: ...
    def __enter__(self) -> Self: ...
    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None: ...
    def solve(self, assumptions: Sequence[int] = ...) -> bool: ...
    def get_model(self) -> list[int] | None: ...
    def add_clause(self, clause: Sequence[int], no_return: bool = ...) -> bool | None: ...

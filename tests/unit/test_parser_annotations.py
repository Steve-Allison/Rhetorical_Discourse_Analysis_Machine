"""Runtime annotation regressions for the public parser façade."""

import inspect

from rdam.rst.parser import Parser


def test_parser_signatures_are_runtime_resolvable() -> None:
    constructor = inspect.signature(Parser)
    release_factory = inspect.signature(Parser.from_model_release)
    assert str(constructor.parameters["device"].annotation) == "str | torch.device | None"
    assert str(constructor.parameters["dtype"].annotation) == "str | torch.dtype | None"
    assert release_factory.parameters["device"].annotation == constructor.parameters["device"].annotation

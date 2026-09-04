"""Assemble the supported providers without coupling orchestration to techniques."""

from rdam._execution import ExecutionPolicy
from rdam.machine import Machine


def production_machine(
    *,
    model: str | None = None,
    execution_policy: ExecutionPolicy | None = None,
) -> Machine:
    """Construct the supported seven-technique production composition.

    Provider imports stay local so importing :mod:`rdam` remains cheap. Construction
    reads declarations only; RST models and LLM clients remain lazy until invocation.
    ``model`` selects one explicit identity for every LLM-backed technique.
    """
    from rdam.dung import DungProvider
    from rdam.ibis import IbisProvider
    from rdam.pdtb import PdtbProvider
    from rdam.rst.provider import RstProvider
    from rdam.sdrt import SdrtProvider
    from rdam.toulmin import ToulminProvider
    from rdam.walton import WaltonProvider

    return Machine(
        (
            RstProvider(),
            PdtbProvider(model=model),
            SdrtProvider(model=model),
            ToulminProvider(model=model),
            WaltonProvider(model=model),
            DungProvider(),
            IbisProvider(),
        ),
        execution_policy=execution_policy,
    )


__all__ = ["production_machine"]

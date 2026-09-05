"""Assemble the supported providers without coupling orchestration to techniques."""

from rdam.configuration import MachineConfig, LocalRstModel, PublishedRstModel
from rdam.machine import Machine
from typing import TypedDict


class _LlmArguments(TypedDict):
    output_retries: int
    transport_retries: int
    transport_deadline_seconds: float


def production_machine(*, config: MachineConfig | None = None) -> Machine:
    """Construct the supported seven-technique production composition.

    Provider imports stay local so importing :mod:`rdam` remains cheap. Construction
    reads declarations only; RST models and LLM clients remain lazy until invocation.
    The immutable configuration resolves defaults once for all interfaces.
    """
    from rdam.dung import DungProvider
    from rdam.ibis import IbisProvider
    from rdam.pdtb import PdtbProvider
    from rdam.rst.provider import RstProvider
    from rdam.sdrt import SdrtProvider
    from rdam.toulmin import ToulminProvider
    from rdam.walton import WaltonProvider
    from rdam.frameworks import Technique
    from rdam.ingest.contracts.analysis import MarkerRefinementMode
    from rdam.ingest.contracts.inference import EvidenceDetailPolicy

    resolved = config or MachineConfig()
    llm = resolved.llm
    rst = resolved.rst
    settings = _LlmArguments(output_retries=llm.output_retries, transport_retries=llm.transport_retries,
                    transport_deadline_seconds=llm.transport_deadline_seconds)

    return Machine(
        (
            RstProvider(
                hf_model_version=rst.model.version if isinstance(rst.model, PublishedRstModel) else None,
                store=rst.model.store if isinstance(rst.model, LocalRstModel) else None,
                release_id=rst.model.release_id if isinstance(rst.model, LocalRstModel) else None,
                relinventory=rst.relinventory, device=rst.device, erst_scorer_checkpoint=rst.erst_checkpoint,
                default_formalism=rst.default_formalism,
                evidence_detail=EvidenceDetailPolicy(rst.evidence_detail),
                marker_refinement=MarkerRefinementMode(rst.marker_refinement),
            ),
            PdtbProvider(model=resolved.model_for(Technique.PDTB), **settings),
            SdrtProvider(model=resolved.model_for(Technique.SDRT), **settings),
            ToulminProvider(model=resolved.model_for(Technique.TOULMIN), **settings),
            WaltonProvider(model=resolved.model_for(Technique.WALTON), **settings),
            DungProvider(capacity=resolved.dung_capacity),
            IbisProvider(),
        ),
        execution_policy=resolved.execution.policy(),
    )


__all__ = ["production_machine"]

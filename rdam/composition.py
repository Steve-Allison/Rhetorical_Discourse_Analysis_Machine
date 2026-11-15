"""Assemble the supported providers without coupling orchestration to techniques."""

from rdam.configuration import MachineConfig, LocalRstModel, PublishedRstModel
from rdam.machine import Machine
from typing import TypedDict


class _LlmArguments(TypedDict):
    output_retries: int
    transport_retries: int
    transport_deadline_seconds: float


def production_machine(*, config: MachineConfig | None = None) -> Machine:
    """Construct the supported thirteen-technique production composition.

    Provider imports stay local so importing :mod:`rdam` remains cheap. Construction
    reads declarations only; RST models and LLM clients remain lazy until invocation.
    The immutable configuration resolves defaults once for all interfaces.
    """
    from rdam.argument_mining import ArgumentMiningProvider
    from rdam.aspic import AspicProvider
    from rdam.centering import CenteringProvider
    from rdam.classical_rhetoric import ClassicalRhetoricProvider
    from rdam.dung import DungProvider
    from rdam.frameworks import Technique
    from rdam.ibis import IbisProvider
    from rdam.ingest.contracts.analysis import MarkerRefinementMode
    from rdam.ingest.contracts.inference import EvidenceDetailPolicy
    from rdam.pdtb import PdtbProvider
    from rdam.pragma_dialectics import PragmaDialecticsProvider
    from rdam.rst.provider import RstProvider
    from rdam.sdrt import SdrtProvider
    from rdam.speech_acts import SpeechActsProvider
    from rdam.toulmin import ToulminProvider
    from rdam.walton import WaltonProvider

    resolved = config or MachineConfig()
    llm = resolved.llm
    rst = resolved.rst
    settings = _LlmArguments(
        output_retries=llm.output_retries,
        transport_retries=llm.transport_retries,
        transport_deadline_seconds=llm.transport_deadline_seconds,
    )

    return Machine(
        (
            RstProvider(
                hf_model_version=rst.model.version if isinstance(rst.model, PublishedRstModel) else None,
                store=rst.model.store if isinstance(rst.model, LocalRstModel) else None,
                release_id=rst.model.release_id if isinstance(rst.model, LocalRstModel) else None,
                relinventory=rst.relinventory,
                device=rst.device,
                default_formalism=rst.default_formalism,
                evidence_detail=EvidenceDetailPolicy(rst.evidence_detail),
                marker_refinement=MarkerRefinementMode(rst.marker_refinement),
            ),
            CenteringProvider(),
            PdtbProvider(model=resolved.model_for(Technique.PDTB), **settings),
            SdrtProvider(model=resolved.model_for(Technique.SDRT), **settings),
            SpeechActsProvider(model=resolved.model_for(Technique.SPEECH_ACTS), **settings),
            ClassicalRhetoricProvider(model=resolved.model_for(Technique.CLASSICAL_RHETORIC), **settings),
            ArgumentMiningProvider(model=resolved.model_for(Technique.ARGUMENT_MINING), **settings),
            ToulminProvider(model=resolved.model_for(Technique.TOULMIN), **settings),
            WaltonProvider(model=resolved.model_for(Technique.WALTON), **settings),
            PragmaDialecticsProvider(model=resolved.model_for(Technique.PRAGMA_DIALECTICS), **settings),
            IbisProvider(model=resolved.model_for(Technique.IBIS), **settings),
            AspicProvider(model=resolved.model_for(Technique.ASPIC), **settings),
            DungProvider(capacity=resolved.dung_capacity),
        ),
        execution_policy=resolved.execution.policy(),
    )


__all__ = ["production_machine"]

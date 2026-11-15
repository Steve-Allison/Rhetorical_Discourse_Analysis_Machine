"""Inference Anchoring Theory (IAT) Argument Mining subpackage."""

from rdam.argument_mining.iat import (
    AduNodeProposal,
    AduRole,
    ArgumentMiningError,
    EnthymemeProposal,
    IatGraphProposal,
    IatRelationProposal,
    IatRelationType,
)
from rdam.argument_mining.output import ArgumentMiningOutput
from rdam.argument_mining.provider import (
    CONTRACT_VERSION,
    FORMALISM_ID,
    INSTRUCTIONS,
    LICENCE,
    PROVIDER_ID_PREFIX,
    ArgumentMiningProvider,
    source_identity,
)

__all__ = [
    "CONTRACT_VERSION",
    "FORMALISM_ID",
    "INSTRUCTIONS",
    "LICENCE",
    "PROVIDER_ID_PREFIX",
    "AduNodeProposal",
    "AduRole",
    "ArgumentMiningError",
    "ArgumentMiningOutput",
    "ArgumentMiningProvider",
    "EnthymemeProposal",
    "IatGraphProposal",
    "IatRelationProposal",
    "IatRelationType",
    "source_identity",
]

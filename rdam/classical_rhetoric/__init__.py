"""Classical Rhetoric (Aristotelian pisteis, kairos, Hermagorean stasis, and schemes) subpackage."""

from rdam.classical_rhetoric.output import ClassicalRhetoricOutput
from rdam.classical_rhetoric.provider import (
    CONTRACT_VERSION,
    FORMALISM_ID,
    INSTRUCTIONS,
    LICENCE,
    PROVIDER_ID_PREFIX,
    ClassicalRhetoricProvider,
    source_identity,
)
from rdam.classical_rhetoric.rhetoric import (
    AppealProposal,
    ClassicalRhetoricError,
    ClassicalRhetoricProposal,
    ETHOS_SUBMODES,
    KairosCueProposal,
    LOGOS_SUBMODES,
    PistisMode,
    RhetoricalFigureProposal,
    RhetoricalScheme,
    StasisKind,
    StasisProposal,
)

__all__ = [
    "CONTRACT_VERSION",
    "ETHOS_SUBMODES",
    "FORMALISM_ID",
    "INSTRUCTIONS",
    "LICENCE",
    "LOGOS_SUBMODES",
    "PROVIDER_ID_PREFIX",
    "AppealProposal",
    "ClassicalRhetoricError",
    "ClassicalRhetoricOutput",
    "ClassicalRhetoricProposal",
    "ClassicalRhetoricProvider",
    "KairosCueProposal",
    "PistisMode",
    "RhetoricalFigureProposal",
    "RhetoricalScheme",
    "StasisKind",
    "StasisProposal",
    "source_identity",
]

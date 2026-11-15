"""Pragma-Dialectics (van Eemeren & Grootendorst 2004; van Eemeren 2010) subpackage."""

from rdam.pragma_dialectics.dialectics import (
    CriticalDiscussionProposal,
    DerailmentProposal,
    PragmaDialecticsError,
    StageSegmentProposal,
    StandpointPolarity,
    StandpointProposal,
    StrategicManoeuvreProposal,
)
from rdam.pragma_dialectics.output import PragmaDialecticsOutput
from rdam.pragma_dialectics.provider import (
    CONTRACT_VERSION,
    FORMALISM_ID,
    INSTRUCTIONS,
    LICENCE,
    PROVIDER_ID_PREFIX,
    PragmaDialecticsProvider,
    source_identity,
)
from rdam.pragma_dialectics.rules import (
    CRITICAL_DISCUSSION_RULES,
    CriticalDiscussionRule,
    CriticalDiscussionRuleId,
    DiscussionStage,
)

__all__ = [
    "CONTRACT_VERSION",
    "CRITICAL_DISCUSSION_RULES",
    "FORMALISM_ID",
    "INSTRUCTIONS",
    "LICENCE",
    "PROVIDER_ID_PREFIX",
    "CriticalDiscussionProposal",
    "CriticalDiscussionRule",
    "CriticalDiscussionRuleId",
    "DerailmentProposal",
    "DiscussionStage",
    "PragmaDialecticsError",
    "PragmaDialecticsOutput",
    "PragmaDialecticsProvider",
    "StageSegmentProposal",
    "StandpointPolarity",
    "StandpointProposal",
    "StrategicManoeuvreProposal",
    "source_identity",
]

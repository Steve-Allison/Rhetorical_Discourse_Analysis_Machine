"""Discourse marker feature priming and relation classification refinement for English RST.

Maintained for backward compatibility; delegates to :mod:`isanlp_rst.relations.primer`.
"""

from isanlp_rst.relations.primer import (
    DISCOURSE_MARKER_RULES,
    DiscourseMarkerPrimer,
    MarkerRule,
)

__all__ = ["DISCOURSE_MARKER_RULES", "DiscourseMarkerPrimer", "MarkerRule"]

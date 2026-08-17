"""RS4 XML processing, eRST data structures, and converters."""

from isanlp_rst.erst.converter import (
    analysis_to_rs4,
    du_to_analysis,
    rs4_to_document_and_analysis,
)
from isanlp_rst.erst.rs4 import (
    RS4Document,
    RS4Group,
    RS4Reader,
    RS4SecEdge,
    RS4Segment,
    RS4Signal,
    RS4Writer,
)

__all__ = [
    "RS4Document",
    "RS4Group",
    "RS4Reader",
    "RS4SecEdge",
    "RS4Segment",
    "RS4Signal",
    "RS4Writer",
    "analysis_to_rs4",
    "du_to_analysis",
    "rs4_to_document_and_analysis",
]

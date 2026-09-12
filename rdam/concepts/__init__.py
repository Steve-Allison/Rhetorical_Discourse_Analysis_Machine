"""Local, source-grounded lexical candidates for any downstream consumer."""

from rdam.concepts.contracts import CandidateSpan, ConceptLinkRequest, ConceptLinkResult, MatchingOptions
from rdam.concepts.index import ConceptIndex
from rdam.concepts.linker import execute_request, link_inventory, link_source, resolve_candidates, validate_result

__all__ = [
    "CandidateSpan", "ConceptIndex", "ConceptLinkRequest", "ConceptLinkResult", "MatchingOptions",
    "execute_request", "link_inventory", "link_source", "resolve_candidates", "validate_result",
]

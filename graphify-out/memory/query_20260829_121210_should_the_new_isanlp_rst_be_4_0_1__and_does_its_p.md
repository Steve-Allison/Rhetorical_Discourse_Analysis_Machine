---
type: "query"
date: "2026-08-29T12:12:10.405428+00:00"
question: "Should the new isanlp_rst be 4.0.1, and does its public API expose everything the provider should expose?"
contributor: "graphify"
outcome: "dead_end"
source_nodes: ["Parser", "RstAnalysis", "Production Ingest API"]
---

# Q: Should the new isanlp_rst be 4.0.1, and does its public API expose everything the provider should expose?

## Answer

Expanded from graph vocabulary: api public contract production source analysis result parser anchor failure version. The graph is stale and surfaced deleted parse_docling, parse_markdown, and parse_doclang entry points, so it is not authority for the current ingest API. Full-source review found provider-owned contract gaps: the implementation discards the full inventory, source-contract identity, selected policy, model-release identity, and subdivision plan from the returned result; prepare does not return its evidence or subdivision plan; anchor coverage is measured but not enforced fail-closed; NOT_ANALYSED is never emitted; AnalysisParser is omitted from the package re-export; and public documentation names nonexistent SourceForm members and Parser.from_release. Because the consumed 4.0.0 API and current API are incompatible, 4.0.1 is not semantically valid.

## Outcome

- Signal: dead_end

## Source Nodes

- Parser
- RstAnalysis
- Production Ingest API
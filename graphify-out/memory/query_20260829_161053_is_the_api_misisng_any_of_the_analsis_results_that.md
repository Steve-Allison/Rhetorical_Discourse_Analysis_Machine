---
type: "query"
date: "2026-08-29T16:10:53.772526+00:00"
question: "is the API misisng any of the analsis/results that are available to us? I want to make sure we are not discarding in the project any analysis/data that downstream may find useful?"
contributor: "graphify"
outcome: "useful"
source_nodes: ["isanlp_rst_ingest_contracts_productionanalysisresult", "isanlp_rst_contracts_analysis_rstanalysis", "isanlp_rst_erst_decoder_erstsecondaryedgedecoder", "isanlp_rst_transformer_parser_model_puretransformerparsingnet"]
---

# Q: is the API misisng any of the analsis/results that are available to us? I want to make sure we are not discarding in the project any analysis/data that downstream may find useful?

## Answer

Expansion trace: analysis, results, outputs, evidence, expose, retained, dropped, omitted, preparation, parser, eRST, contract. Conclusion: yes. Feature 004 repairs current source-preparation loss, but its analysis contract is incomplete. Missing provider-owned public evidence includes the selected output formalism and inference/refinement policy; the parser-visible token and EDU document; primary relation probabilities, segmentation evidence, split uncertainty and marker-override lineage; eRST signal-to-edge support, relation probability, joint score and the existing decode receipt; composite primary plus eRST model, calibration, relation-inventory and ontology-mapping identity; hierarchical recombination mappings and unit receipts; and a validation receipt. The current uncommitted ModernBERT facade is a blocker because it decodes a complete list of scored CKY spans but constructs only the root split and two children, discarding the remaining decoded tree and all scores. Keep embeddings, activations, training-only gold fields and raw tensor charts internal; expose compact decision-complete evidence, with optional normalized distributions under an explicit evidence policy.

## Outcome

- Signal: useful

## Source Nodes

- isanlp_rst_ingest_contracts_productionanalysisresult
- isanlp_rst_contracts_analysis_rstanalysis
- isanlp_rst_erst_decoder_erstsecondaryedgedecoder
- isanlp_rst_transformer_parser_model_puretransformerparsingnet
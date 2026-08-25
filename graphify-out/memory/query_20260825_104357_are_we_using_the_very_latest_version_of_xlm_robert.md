---
type: "query"
date: "2026-08-25T10:43:57.897984+00:00"
question: "are we using the very latest version of xlm-roberta-large?"
contributor: "graphify"
outcome: "useful"
source_nodes: ["ConfigReader", "ModelRevisionAuthority"]
---

# Q: are we using the very latest version of xlm-roberta-large?

## Answer

Expanded from original query via graph vocabulary: bert, large, backbone, checkpoint, config, model, revision, upstream, hugging, version. The graph located the model loaders; direct source and live Hugging Face verification established that all five checkpoint configs name xlm-roberta-large without a revision pin. The local cache main revision c23d21b0620b635a76227c604d44e43a9f0ee389 equals the live FacebookAI/xlm-roberta-large main revision on 2026-08-25. Therefore this machine currently uses the latest upstream artifacts, but the source does not guarantee immutable reproducibility because it omits revision=.

## Outcome

- Signal: useful

## Source Nodes

- ConfigReader
- ModelRevisionAuthority
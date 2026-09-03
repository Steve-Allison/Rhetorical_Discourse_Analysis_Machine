# Contract: Architecture Boundaries

**Reconciled**: 2026-09-03. This contract supersedes the pre-migration top-level
boundary roster.

## Production package

`rdam/` is the one production import root and the one shipped Python package.

| Path | Exclusive owner |
|---|---|
| `rdam/contracts.py`, `machine.py`, `frameworks.py`, `serialization.py`, `_strict.py` | Aggregate contracts, canonical identities, orchestration, and serialization |
| `rdam/rst/` | RST/eRST parser, universal ingest, native contracts, provider, viewer, and command |
| `rdam/pdtb/` | Native PDTB-3 relation contract and provider |
| `rdam/sdrt/` | Native SDRS graph contract and provider |
| `rdam/toulmin/` | Native Toulmin layout contract and provider |
| `rdam/walton/` | Native Walton scheme catalogue/contract and provider |
| `rdam/dung/` | Dung framework semantics and provider |
| `rdam/ibis/` | gIBIS grammar and provider |
| `rdam/resources/` | Generated runtime projections required by the installed package |

No top-level technique package or compatibility package exists. A technique owns its
native vocabulary and validation; the machine owns only shared envelopes and execution.

## Non-production and repository support

| Path | Owner and distribution rule |
|---|---|
| `workbench/` | All experimentation, evaluation, corpus work, and training; never imported or shipped by production |
| `ontology/` | Vendored Central_Configs authority and consumer LinkML profile; only its generated runtime projection ships |
| `tests/` | Production, integration, offline, and stress verification, separated by subtree/markers |
| `tools/`, `scripts/` | Repository/build/diagnostic tooling; never a production import dependency |
| `specs/`, `docs/`, `.claude/` | Product/design/governance documentation |
| `models/`, `examples/`, `graphify-out/`, `dist/` | Local assets, examples, generated knowledge graph, and ignored build output |

## Enforced rules

1. Production modules never import `workbench`, test, or repository-tool modules.
2. Wheels and sdists contain the `rdam` package and declared package data, never
   `workbench/`.
3. Capability inspection constructs no inference model or network client.
4. Shared production abstractions require at least two real callers and one clear owner.
5. Historical `isanlp_rst.*` values may survive only as persisted contract/release
   identifiers; they do not authorize a second import package.

`pixi run -e default production-boundary` is the executable source-boundary gate.
Artifact membership is checked by the production artifact validation tasks.

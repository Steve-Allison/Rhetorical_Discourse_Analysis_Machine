# Feature 004 Source Scope and SOTA Audit

**Audit date**: 2026-08-30

**Candidate state**: pre-source, uncommitted working tree

**Scope**: Feature 004 production API, corrected source-evidence contract, and release tooling through T132

## Disposition

The source candidate conforms to the Feature 004 provider boundary. No
consumer-specific field, restored format-specific public API, production-to-
offline dependency, forbidden scientific internal, model-architecture change,
inference-mathematics change, fabricated fallback, runtime-identity
contradiction, archived-family capability claim, or independent CLI/HTTP
semantic authority remains in the audited implementation.

This is source-only evidence. It makes no wheel, sdist, clean-install,
second-machine, receipt, tag, push, or remote-parity claim. Those claims remain
gated by T133-T142.

## Scope audit

| Audit question | Disposition | Evidence |
|---|---|---|
| Downstream-specific contract values | Pass | Public contracts describe only values created, selected, retained, validated, or executed by `isanlp_rst`; `tests/ingest/production_ingest/test_public_consumer_adapter.py` consumes the result without adding provider evidence. |
| Restored format-specific APIs | Pass | The public surface exposes `SourceArtifact` and the shared prepare/analyse operations; `test_public_surface.py` rejects undeclared exports and `public-surface.json` contains no `parse_markdown`, `parse_docling`, or `parse_doclang` member. |
| Source-format interpretation | Pass | Current Docling/DocLang versions, fixtures, namespaces, archive forms, and optional extras are recorded in `source-spec-currency.md`; Feature 004 retains one canonical inventory path. |
| Research/offline leakage | Pass | Public-surface negative assertions and artifact fixture validation reject workbench, research, corpus, training, and weight leakage; the core/formats dependency boundary remains explicit in `pyproject.toml`. |
| Raw scientific internals | Pass | Public-surface tests reject tensors, embeddings, hidden activations, unrestricted charts, training-only labels, and workbench values; only bounded selected decisions, normalized distributions, and receipts are public. |
| Model architecture or inference mathematics | Pass | Changes in the active ModernBERT path preserve exact tokenizer offsets, decoded decisions, scores, and runtime bytes or fail closed. They do not change layer topology, learned parameter shapes, score equations, CKY selection rules, or eRST decision thresholds. |
| Backend evidence loss | Pass | `test_backend_evidence_loss.py`, `test_analysed_document.py`, `test_primary_inference_evidence.py`, `test_refinement_provenance.py`, and `test_erst_completion_evidence.py` deliberately remove or mutate evidence and require rejection. |
| Fabricated decisions or approximate fallbacks | Pass | Exact-substrate tests reject truncation, capped or missing suffixes, approximate allocation, synthesized decisions, and graph-only reconstruction. |
| Runtime identity contradictions | Pass | `test_composite_analysis_identity.py` exercises loaded tokenizer/configuration/state bytes and rejects path, revision, inventory, and weight substitutions. |
| Archived capability claims | Pass | `capabilities.py` excludes `dmrst` and `unirst` from canonical-result support, and `test_parser_capabilities.py` verifies the rejection. |
| CLI/local HTTP semantics | Pass | `test_cli_contract.py` and `test_local_http_contract.py` require canonical Python-byte parity, one inference execution, typed capability/health records, loopback-only HTTP, and safe typed failures. |
| Release tooling scope | Pass | T121-T127 tooling uses exact clean commits, Git archives, deterministic provenance, via-sdist double builds, strict artifact/receipt validation, and isolated installed acceptance. The T134 generator now emits a strict, schema-versioned `source_selected` record and rejects candidate-commit fields before those identities exist. |

## Dated SOTA comparison closure

The 2026-08-29 comparison in `research.md` classifies every FR-045 practice:
strict typed values, complete provider evidence, decision-complete inference,
lossless backend handoff, composite identity, decision and validation receipts,
deterministic identity, published schemas, compatibility, installed identity,
public-surface authority, typed failures, capability discovery, artifact
integrity, reproducible builds, clean installed proof, and lifecycle
provenance. Each row has one explicit Feature 004 disposition; no practice is
unclassified and no implementation decision re-opens the research scope.

## Source evidence identities

- `pre-release-quality.json`: `fdb3769a274665ca4bef314264c3e0730619f9e92a92eea191509000277c2e4a`
- `performance.json`: `9af5fc53d3c46695a985d312998a0daee6c701dedebfaa837a276f21b47bb5fa`
- `source-spec-currency.md`: `88e22f25ab61c70ee070457597ed9f74266f760e869cdd772cbdb1c39d5e7b0f`

The quality record reports the focused Feature 004 tests, Ruff, and Pyright as
passed. The performance record reports the governed preparation-performance
gate as passed. Final aggregate source-only evidence is generated by T132 after
this audit is included in the candidate.

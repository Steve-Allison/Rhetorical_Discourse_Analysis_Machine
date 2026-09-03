# Feature 009: RST Provider Adapter

**Status**: implemented 2026-09-02; the `rst/rdam_rst` layout described below was superseded the same day by the owner's single-package ruling — the adapter is `rdam/rst/provider.py`, provider id `rdam.rst/<release_id>` ([010 §Single package](../010-repository-migration/spec.md)) | **Authority**: [006 spec](../006-rhetorical-discourse-machine/spec.md) FR-008..FR-011, FR-020; [006 capability-declaration contract](../006-rhetorical-discourse-machine/contracts/capability-declaration.md); [006 data model §Provider, §Formalism](../006-rhetorical-discourse-machine/data-model.md); [006 rst-preservation contract](../006-rhetorical-discourse-machine/contracts/rst-preservation.md) | **Owner ruling**: "build it all" (2026-09-02)

## What was built

| Requirement | Artifact | Proof |
|---|---|---|
| The machine-facing RST adapter consumes the supported `isanlp_rst` public contract and never duplicates, reinterprets, or bypasses its authority (FR-010) | `rst/rdam_rst/` — package `rdam_rst`, distribution `rdam-rst`, depends on `rdam` and `isanlp_rst`; `RstProvider.analyse` runs `ProductionIngestor(parser).analyse(SourceArtifact.from_text(...))` and hands the machine `serialize_contract(outcome)` **verbatim** as the opaque native payload | `tests/rst/test_provider.py::TestRealRelease::test_machine_gets_isanlp_rst_outcome_envelope_as_the_native_payload` — the payload is `isanlp_rst.production` / `analysed_outcome` with its nodes |
| `isanlp_rst` stays the canonical provider under the `rst/` boundary (FR-008); its import name is untouched (FR-009) | `rst/` created as the RST boundary holding the adapter; `isanlp_rst/` moves into it in feature 010 | boundary tool: `rst` is a production root, `rdam_rst/` an admitted wheel root |
| Capability is an explicit state with stable reasons, never a stub (FR-020, SC-007) | `RstProvider.declaration` derives `available`/`unavailable(reason)` from whether the configured parser can run: a published version the façade knows how to load, or a local release whose manifest is present; otherwise `model_unavailable` | `TestConfiguration` |
| Capability reporting is side-effect-free (capability contract §Aggregate behaviour 2) | `declaration` checks configuration and looks for a bundle path; the parser loads on first `analyse` | `test_a_published_version_is_available_without_loading_a_model` asserts no parser after declaring |
| Formalism ruling (006 U1): `rst_tree → …/rst`, `erst_graph → …/erst`, each with its own state | `erst_graph` is `available` only when a validated eRST completion bundle resolves; a request for it without one is `unavailable`, not a failure | `test_erst_is_declared_with_its_own_identity_and_state`, `test_asking_for_erst_without_a_bundle_is_unavailable_not_failed` |
| Failure algebra preserved (FR-011; capability contract §Retryability) | `ProductionIngestError` → `ProviderFailure` one-to-one: same code, same retryability, stage and category carried as parameters; the machine never retries | `TestAnalyseGuards` |
| A caller can choose a formalism per technique | `AggregateRequest.formalisms` (`FormalismChoice`), threaded by `Machine` into `ProviderRequest.formalism_id`; an unavailable choice is an `unavailable` outcome | `test_asking_for_erst_without_a_bundle_is_unavailable_not_failed` |

## The state this leaves the machine in

**Amended 2026-09-02**: the promotion-evidence gate was removed by owner ruling. It had
made a working parser report `unavailable(withheld)`, which was never the owner's
intent — the DMRST and UniRST parsers run and are the production families. `RstProvider()`
now reports **`available`** as `rdam.rst/gumrrg`, and reports `model_unavailable` only
when the configured version is unknown to the façade or a local release is absent.

## Gates

See [evidence/gates.md](evidence/gates.md).

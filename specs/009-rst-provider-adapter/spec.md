# Feature 009: RST Provider Adapter

**Status**: implemented 2026-09-02; the `rst/rdam_rst` layout described below was superseded the same day by the owner's single-package ruling — the adapter is `rdam/rst/provider.py`, provider id `rdam.rst/<release_id>` ([010 §Single package](../010-repository-migration/spec.md)) | **Authority**: [006 spec](../006-rhetorical-discourse-machine/spec.md) FR-008..FR-011, FR-020; [006 capability-declaration contract](../006-rhetorical-discourse-machine/contracts/capability-declaration.md); [006 data model §Provider, §Formalism](../006-rhetorical-discourse-machine/data-model.md); [006 rst-preservation contract](../006-rhetorical-discourse-machine/contracts/rst-preservation.md) | **Owner ruling**: "build it all" (2026-09-02)

## What was built

| Requirement | Artifact | Proof |
|---|---|---|
| The machine-facing RST adapter consumes the supported `isanlp_rst` public contract and never duplicates, reinterprets, or bypasses its authority (FR-010) | `rst/rdam_rst/` — package `rdam_rst`, distribution `rdam-rst`, depends on `rdam` and `isanlp_rst`; `RstProvider.analyse` runs `ProductionIngestor(parser).analyse(SourceArtifact.from_text(...))` and hands the machine `serialize_contract(outcome)` **verbatim** as the opaque native payload | `tests/rst/test_provider.py::TestRealRelease::test_machine_gets_isanlp_rst_outcome_envelope_as_the_native_payload` — the payload is `isanlp_rst.production` / `analysed_outcome` with its nodes |
| `isanlp_rst` stays the canonical provider under the `rst/` boundary (FR-008); its import name is untouched (FR-009) | `rst/` created as the RST boundary holding the adapter; `isanlp_rst/` moves into it in feature 010 | boundary tool: `rst` is a production root, `rdam_rst/` an admitted wheel root |
| Capability is an explicit state with stable reasons, never a stub (FR-020, SC-007) | `RstProvider.declaration` derives `available`/`unavailable(reason)` from the **published promotion decision** beside the release: none → `no_promoted_implementation`; withhold → `withheld`; retire → `retired`; promote/replace → `available` | `TestDeclaration` |
| Capability reporting is side-effect-free (capability contract §Aggregate behaviour 2) | `declaration` reads the sidecar and checks for a bundle path; the parser loads on first `analyse` | `test_no_decision_means_no_promoted_implementation` asserts no parser after declaring |
| Formalism ruling (006 U1): `rst_tree → …/rst`, `erst_graph → …/erst`, each with its own state | `erst_graph` is `available` only when a validated eRST completion bundle resolves; a request for it without one is `unavailable`, not a failure | `test_promote_decision_makes_rst_tree_available_and_erst_depends_on_a_bundle`, `test_asking_for_erst_without_a_bundle_is_unavailable_not_failed` |
| A decision cannot be borrowed by another artifact (FR-023) | Before the first inference the decision's `artifact_identity` is checked against the release manifest's `parser_state` digest | `test_decision_for_a_different_artifact_cannot_borrow_the_release` |
| Failure algebra preserved (FR-011; capability contract §Retryability) | `ProductionIngestError` → `ProviderFailure` one-to-one: same code, same retryability, stage and category carried as parameters; the machine never retries | `TestAnalyseGuards` |
| A caller can choose a formalism per technique | `AggregateRequest.formalisms` (`FormalismChoice`), threaded by `Machine` into `ProviderRequest.formalism_id`; an unavailable choice is an `unavailable` outcome | `test_asking_for_erst_without_a_bundle_is_unavailable_not_failed` |

## The state this leaves the machine in

With the retroactive decisions of feature 008 published beside the releases, an
`RstProvider` configured with `modernbert-v1-a52b70fbc1a3` reports **`unavailable(withheld)`**
and the machine says so (`test_machine_reports_the_withheld_rst_provider_honestly`). That
is the truthful state, not a defect of the adapter: the slow tests prove the adapter
works by supplying a fixture `promote` decision that names the real artifact. The path to
`available` is the owner ruling named in [008 §Consequence](../008-promotion-system/spec.md).

## Gates

See [evidence/gates.md](evidence/gates.md).

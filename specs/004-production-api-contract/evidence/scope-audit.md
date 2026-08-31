# Feature 004 Source Scope and SOTA Audit

**Audit date**: 2026-08-31

**Candidate state**: pre-source, uncommitted working tree

**Scope**: Feature 004 provider API, current production/runtime changes, and
release tooling through T132. This is source-only evidence: it makes no wheel,
sdist, candidate, second-machine, receipt, tag, push, or remote-parity claim.

## Disposition

Feature 004 remains bounded to provider-owned API, runtime-byte identity,
capability, distribution, and release-boundary obligations. No Feature 004
change introduces a downstream-specific contract, a restored format-specific
public API, a production-to-offline dependency, raw scientific internals, a
fabricated parser decision, an archived capability claim, or an independent
CLI/local-HTTP semantic authority.

The current worktree also contains ModernBERT architecture, loss, training,
benchmark, corpus, and experiment-ledger changes. Those are not Feature 004
work and this audit neither evaluates their scientific quality nor requires
Feature 005 to change. Feature 004 has verified only the provider values it
actually consumes: the exact runtime-byte inventory and canonical executable
parser-analysis contract of `modernbert-v1-e5ea56cd620f`.

During this audit, `scripts/train_modernbert_treebank.py` was corrected because
its final receipt referenced the nonexistent `args.lr` rather than the actual
`encoder_lr` and `head_lr` inputs. This is a factual receipt/runtime repair,
not a training-policy or model-quality change.

## Scope audit

| Audit question | Disposition | Current evidence |
|---|---|---|
| Downstream-specific contract values | Pass | Production contracts and public surface have no CSM-specific value; consumer adapter conformance uses only public provider evidence. |
| Restored format-specific APIs | Pass | The installed surface provides `SourceArtifact` plus shared `prepare`/`analyse`; legacy `parse_markdown`, `parse_docling`, and `parse_doclang` names appear only in historical documentation or private adapters. |
| Source-format interpretation | Pass | No Feature 004 change alters harvest semantics. The existing current-spec determination remains `source-spec-currency.md`. |
| Research/offline leakage and weights | Pass | `pixi run -e production production-boundary` returned `valid: true`; ownership now classifies `models/` as non-publishable model material, while artifact inspection still forbids `.pt`, `.pth`, and `.safetensors`. |
| Raw scientific internals | Pass | Installed clean-room acceptance imports the 202-entry public surface and rejects tensors, embeddings, activations, training labels, and workbench values. |
| Model architecture and inference mathematics | External to Feature 004 | The current diff changes ModernBERT loss/dtype/span-pooling and offline training. Feature 004 makes no scientific or promotion claim about them; it verifies only exact runtime bytes and public executability. |
| Backend evidence loss and fabricated decisions | Pass | Existing canonical-result conformance plus focused component-identity tests reject removed evidence, runtime-file substitution, and a component/result identity contradiction. |
| Runtime identity and capability truth | Pass | `load_model_release()` revalidated all five declared release files; clean core and formats installs each reported four loaded components, seven validation checks, canonical parser analysis, and Python/CLI semantic parity. |
| Archived capability claims | Pass | Capability conformance retains ModernBERT as the executable immutable family and excludes archived DMRST/UniRST canonical-result support. |
| CLI/local HTTP semantics | Pass | Focused production-contract conformance passed in the regenerated pre-release quality record. |
| Release tooling scope | Pass | Clean-install certification now requires `--full`, the explicit in-tree release, network-disabled inference, and retained core/formats receipts. Preparation-only certification fails before T136. |

`git diff --check` reported no whitespace errors. The current source diff was
read for all production-boundary changes and all touched production/runtime
paths relevant to this audit.

## Dated SOTA comparison closure

`research.md` was re-read in full. Its 2026-08-29 comparison classifies every
FR-045 practice—strict typing, provider evidence, decision and validation
receipts, deterministic identities, schemas, compatibility, installed and
runtime identity, public-surface authority, typed failures, capabilities,
artifact integrity, reproducible builds, clean installs, and lifecycle
provenance—with an explicit Feature 004 disposition. The present audit found no
unclassified Feature 004 gap. Scientific model evaluation, thresholds, training
records, and promotion remain deliberately outside that comparison and Feature
004 authority.

## Current source-only evidence identities

- `pre-release-quality.json`:
  `1b11c0e61b280768108f516f3a55bc02c8f4fc9339366cd515ac4dcbad9ddae8`
- `performance.json`:
  `bce52431c2ecd4715e9ce7c39caaba8d2d85107d72f033f0b3ce2e48edaf7804`
  (one warm-up and five retained runs for both governed source sizes)
- `source-spec-currency.md`:
  `88e22f25ab61c70ee070457597ed9f74266f760e869cdd772cbdb1c39d5e7b0f`

Final aggregate source-only evidence is regenerated by T132 after this audit.

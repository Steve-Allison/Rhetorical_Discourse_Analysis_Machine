# Contract: Standardised Patterns Register

**Feature**: 006 | **Authority**: [spec.md](../spec.md) FR-006, FR-010, FR-012, FR-029; the pattern authorities cited per row

The machine's shared runtime patterns, mapped. FR-029 forbids extracting a shared
production library before two proven callers need the same semantic contract — this
register is the other half of that rule: it names each pattern, its single current
authority (the RST provider's implementation), and the adoption discipline that keeps
every future provider semantically aligned *without* premature code sharing.

## Adoption rules (binding on every provider and machine-layer feature)

1. **Adopt semantics, not code.** A new provider implements each applicable pattern's
   semantics in its own contracts from its first commit. It never imports another
   boundary's internals; only the machine-facing RST adapter consumes the supported
   `isanlp_rst` public contract (FR-010).
2. **The authority column is normative.** Where a pattern's precise behaviour matters,
   the cited implementation is the reference semantics — divergence is a design
   decision to record, not an accident.
3. **Extraction is an FR-029 event.** When a second proven production caller needs a
   pattern as code, extracting it into a shared library is its own decision with
   unambiguous ownership — recorded, not assumed. The trigger column names the
   expected second caller where one is foreseeable.

## The register

| # | Pattern | Reference authority (verified) | Applies to | Extraction trigger |
|---|---|---|---|---|
| P1 | **Failure algebra** — lifecycle stages, failure categories, mandatory retryability, monotonic completed-stage evidence (evidence precedes the failed stage), safe-vs-diagnostic persisted records, privacy-safe message templates | `isanlp_rst/ingest/contracts/failure.py` | every provider and the aggregate | second provider emitting typed failures |
| P2 | **Retryability classification & transient-boundary retry** | [capability-declaration.md](capability-declaration.md) (machine-wide standard, already elevated) | every provider | already machine-wide |
| P3 | **Semantic identity & canonical serialization** — content-addressed `Sha256Identity`, `semantic_sha256`, RFC 8785 canonical JSON, digest-bound envelopes (`contract`/`contract_version`/`kind` + self-checking `semantic_digest`) | `isanlp_rst/ingest/identity.py`, `serialization.py`, `contracts/base.py` (`StrictContractModel`) | every native result, aggregate, dependency reference (FR-015's exact-artifact identity depends on it) | feature 007 (the aggregate contract is the second caller by design) |
| P4 | **Composite component identity & cache eligibility** — immutable component identities, `durable_cache_eligible`, request identity fingerprinting the complete analytical pipeline | `isanlp_rst/ingest/contracts/inference.py`, `service.py` | any provider offering cached analysis | second cached provider |
| P5 | **Integrity-checked atomic persistence** — temp-file + fsync + rename + directory-fsync writes; identity-bound entries; corrupt-entry vs I/O-failure split | `isanlp_rst/ingest/cache.py` | any provider or machine layer persisting outcomes | with P4 |
| P6 | **Fail-closed validation receipts** — required/advisory checks, reproducible receipts, validation-verdict vs validator-bug separation; formal-technique variant: property proofs as required checks (Dung extension properties, IBIS grammar closure) | `isanlp_rst/ingest/validation.py`; [promotion-evidence.md](promotion-evidence.md) formal clause | every provider result | Dung provider (first formal receipt) |
| P7 | **Execution evidence** — execution id, duration, device, software version, source revision, loaded-component receipts | `isanlp_rst/ingest/contracts/analysis.py` execution models, `isanlp_rst/_provenance.py` | every provider | with the promotion system feature |
| P8 | **Capability reporting** — states, stable reasons, `coe:` identity binding, side-effect-free queries | [capability-declaration.md](capability-declaration.md) | machine layer + every provider | already machine-wide |
| P9 | **Safe boundary projections** — phase-separated boundary error labelling (acquisition vs configuration vs analysis), loopback-only HTTP, privacy-safe payloads, internal bugs propagating natively rather than mislabelled as client errors | `isanlp_rst/cli.py` | any provider or machine CLI/HTTP surface; the machine-level unified projection is an orchestration-feature decision | cross-provider orchestration feature |
| P10 | **Source acquisition & anchoring** — inventory, disposition policy, preparation, source anchors surviving into results, subdivision | `isanlp_rst/ingest/` (RST-provider-owned canonical ingest) | RST today. **Named open question**: SDRT-on-transcripts would be the second caller for prepared sources (dialogue turns); the SDRT feature MUST confront reuse-vs-own under FR-029 rather than assume either | SDRT provider feature |
| P11 | **Model loading & device handling** — model release identity, verified file manifests, device resolution, MPS-safe initialisation | `isanlp_rst/model_loading.py`, `isanlp_rst/utils/mps_init.py`, `base_predictor` device rules | local-model providers only | SDRT provider feature (first second local model) |
| P12 | **Gate evidence records** — versioned evidence schemas persisted by verification gates (e.g. `isanlp_rst.release_evidence.performance`) | `tools/production_boundary/` evidence flow | promotion system + provider gates | workbench promotion system feature |

## Named feature-007 design item: the shared analysis store

P4 and P5 together already make a machine-level shared cache safe by construction:
entries are content-addressed by the complete pipeline identity (source, policy, every
component fingerprint), writes are atomic and integrity-checked, a promoted model
changes the fingerprint so stale results can never be served, and deterministic
providers make concurrent same-key writers byte-identical. The aggregate-contract
feature (007) MUST therefore rule on the machine's shared analysis store explicitly:
one default store location shared by all machine consumers; per-technique
content-addressed entries; a garbage-collection rule for entries orphaned by component
promotions; and the privacy posture of the shared location (cached outcomes contain
full source text — the safe/diagnostic discipline of P1 extends to the store). Until
007 rules, per-consumer `cache_directory` remains the supported sharing mechanism.

## What this register deliberately is not

It is not a shared library, a `common/` boundary, or permission to create one — FR-029
still gates that, per pattern, on its trigger. It is the map that stops feature 007 and
each provider feature from re-deriving or silently diverging from semantics the machine
already runs in production.

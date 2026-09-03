# Data Model: Rhetorical Discourse Analysis Machine

**Feature**: 006 | **Reconciled**: 2026-09-03 | **Sources**: [spec.md](spec.md), [research.md](research.md)

## Technique

The seven boundary techniques are RST, PDTB, SDRT, Toulmin, Walton, Dung, and IBIS.
eRST is a formalism emitted by the RST provider, not an eighth provider boundary. Each
identity resolves through the canonical packaged `coe:` projection.

## ProviderDeclaration

One independently callable production provider declares:

- stable provider identity and exactly one boundary technique;
- one or more native formalisms, each with canonical framework identity and capability;
- native contract version;
- package/source/model provenance and licence;
- whether structured input is required;
- standing `available` or `unavailable(reason)` capability.

Reading the declaration is side-effect-free. Every technique subpackage contains a real
provider; no directory or declaration is a stub.

## CapabilityState

| State | Meaning |
|---|---|
| `available` | The configured provider can accept a well-formed request. |
| `unavailable` | A stable reason explains why it cannot run: `not_implemented`, `model_unavailable`, or `missing_structured_input`. |
| `failed` | Per-request typed failure with mandatory retryability and causal evidence. |

`not_implemented` remains part of the generic machine contract but the supported
production composition contains no missing provider. Model availability can change with
local configuration; Dung and IBIS are always available once imported.

## NativeTechniqueResult

A native result carries technique, formalism, provider and contract identities, source
identity, opaque provider-native payload, provenance, and semantic digest. The aggregate
validates the envelope against the provider declaration but does not reinterpret the
payload.

Native result authorities:

| Technique | Native result |
|---|---|
| RST/eRST | RST ingest outcome and tree/eRST graph contracts under `rdam.rst` |
| PDTB | PDTB-3 binary relations, source spans, types, evidence, and senses |
| SDRT | SDRS graph with EDUs, CDUs, structural relation classes, and right-frontier proof |
| Toulmin | Complete claim-ground-warrant layouts with optional qualifiers |
| Walton | Scheme instances with exact premise roles and critical-question states |
| Dung | Argumentation framework plus exact extension semantics |
| IBIS | gIBIS issue-position-argument structure and deliberation map |

## AggregateRequest

One request carries one source identity, optional source text, requested techniques,
per-technique formalism choices, structured inputs, and explicitly carried upstream
results. A technique cannot be both carried as upstream and requested again.

## AggregateAnalysis

The aggregate contains the shared source, ordered outcomes, explicit cross-provider
lineage, and its semantic digest. Every requested technique has exactly one outcome;
one provider's failure never suppresses another's success.

## ProviderDependencyReference

Lineage names the consumer provider and contract, the exact upstream result digest,
upstream provider/contract/model identity, and both techniques. The machine records a
caller-declared derivation; it never derives one provider's input by itself.

## Supported composition

`production_machine(model=...)` registers providers in canonical order:

```text
RST → PDTB → SDRT → Toulmin → Walton → Dung → IBIS
```

Construction reads declarations only. RST parsing and LLM clients remain lazy until
analysis. With a resolvable LLM model and the default RST family, all seven standing
capabilities are `available`; Dung and IBIS still require structured input per request.

## State transitions

- Provider configuration: `available ↔ unavailable(model_unavailable)` as local model
  configuration resolves or stops resolving.
- Request: standing availability is unchanged by `result` or `failed` outcomes.
- Composition: removing a provider yields `unavailable(not_implemented)` for that
  machine instance without changing any other serialized declaration.

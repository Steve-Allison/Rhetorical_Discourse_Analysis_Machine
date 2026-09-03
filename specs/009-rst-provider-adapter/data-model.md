# Data Model: RST Provider Adapter

## RST provider configuration

Exactly one model source is configured:

- a known published `hf_model_version`; or
- an immutable `store` plus safe `release_id`.

The provider also carries device, optional UniRST relation inventory, optional eRST
completion checkpoint, and optional production-analysis cache directory.

## Validated local release state

The provider caches one of two terminal inspection states: validated release plus parser
family, or unavailable. Inspection verifies the complete immutable release but constructs
no parser. A later analysis revalidates at model load, preventing a changed release from
being silently trusted.

## Provider declaration

The declaration names the RST boundary, exact provider/model identity, package version,
source revision where available, weights licence, contract version, overall capability,
and two formalism declarations:

- `rst_tree` → canonical RST identity;
- `erst_graph` → canonical eRST identity, available only with a resolvable completion bundle.

## Native result

The aggregate envelope retains exact source identity, provider declaration identity, and
an opaque payload equal to the canonical serialized `rdam.rst` production outcome.

## Failure

Configuration/formalism/text/release failures are non-retryable typed provider failures.
Production-ingest failures preserve canonical retryability and stage/category evidence.

## State transitions

```text
configuration -> declaration inspection -> available | unavailable(model_unavailable)
available + analyse -> parser load -> canonical ingest -> native result
expected release/ingest defect -> typed provider failure
unexpected internal defect -> native exception propagation
```

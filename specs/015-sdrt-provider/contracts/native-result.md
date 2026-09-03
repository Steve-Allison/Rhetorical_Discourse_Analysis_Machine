# Native SDRT Result Contract

## Identity

- Technique: `sdrt`
- Formalism: `sdrs_graph`
- Provider contract: `1.0.0`
- Result envelope: the shared `rdam.NativeTechniqueResult`

## Valid result

A valid payload contains:

- `edus`: ordered exact source spans;
- `cdus`: explicit, resolving, acyclic memberships;
- `relations`: resolving directed edges with label and structural class;
- derived node/relation/CDU counts;
- `extraction`: exact model identity, instruction digest, output attempts, and transport attempts.

The graph is connected for more than one unit, relation-acyclic, membership-acyclic, structurally class-consistent, and right-frontier compliant.

## Refusal

The provider emits no partial graph. Invalid source, undeclared formalism, unavailable model, invalid SDRS, invalid model output, and model-service errors become typed failures using the shared provider contract.

## Capability

Reading `declaration` resolves only configuration and source identity. It constructs no client and performs no network request.

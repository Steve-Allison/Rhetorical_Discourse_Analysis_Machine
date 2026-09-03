# Native PDTB-3 Result Contract

## Identity

- Technique: `pdtb`
- Formalism: `pdtb3_relations`
- Provider contract: `1.0.0`
- Result envelope: the shared `rdam.NativeTechniqueResult`

## Valid result

Each relation contains its unique identity, exact type, binary Arg1/Arg2 span collections, canonical senses where applicable, and exactly the signal field permitted by its type. The payload also carries relation counts and exact extraction attempt evidence.

## Refusal

No span, sense, type, argument label, or signal is inferred or corrected after model output. Invalid source, undeclared formalism, model unavailability, native-contract failure, invalid structured output, and model-service failures become typed outcomes with zero partial relations.

## Capability

Reading `declaration` constructs no model client and performs no request.

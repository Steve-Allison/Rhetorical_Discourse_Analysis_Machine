# Data Model: IBIS Provider

## Node

- non-empty `node_id`
- `kind`: issue, position, or argument
- non-blank `text`

## Link

- declared source and target ids
- one of eight `Relation` values
- distinct endpoints

## IbisStructure

- non-empty ordered nodes with unique ids
- unique ordered links
- every link satisfies `GRAMMAR`
- every position/argument satisfies its exact attachment cardinality

## DeliberationMap

- issues and their positions
- each position's supporting and objecting arguments
- issue relations
- issues without positions, positions without arguments, isolated nodes

## Native provider payload

- exact structure and deterministic map
- input origin and optional upstream identity
- `extraction: null`
- grammar identity `gibis-v1`

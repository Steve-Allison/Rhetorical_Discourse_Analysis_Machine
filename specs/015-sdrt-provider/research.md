# Research: SDRT Provider

## Primary authority

Afantenos and Asher, “Expressivity and comparison of models of discourse structure” (2013), defines SDRSs as acyclic labelled graphs over EDUs and CDUs, distinguishes coordinating from subordinating relations, and states the right-frontier constraint: <https://aclanthology.org/W13-4002/>.

## Decisions

### Preserve a graph, not a tree

**Decision**: The native result contains explicit EDU nodes, CDU nodes/membership, and directed relation edges.

**Rationale**: SDRT permits non-adjacent and multiple attachments and permits CDUs as relation arguments. A tree would destroy valid scope.

### Close structural class, not relation vocabulary

**Decision**: Every relation carries a non-empty corpus/theory label and exactly one structural class: coordinating or subordinating.

**Rationale**: The structural distinction is theory-defining and is needed for right-frontier computation. Relation inventories differ across SDRT annotation projects, so a purported universal fixed list would be invented authority.

### Validate the computable right frontier

**Decision**: In EDU source order, a new EDU must have an incoming edge from the immediately preceding EDU, one of its reverse subordinating ancestors, or a completed CDU containing a frontier node.

**Rationale**: This operationalizes the cited SDRT constraint without asking an LLM to assert its own compliance. CDU-scoped and non-adjacent attachments remain possible.

### Keep dynamic semantics out of fabricated output

**Decision**: The production result claims structural SDRS analysis, not a formally interpreted world-assignment context-change model.

**Rationale**: The provider can validate graph structure and discourse relations from text; it cannot honestly manufacture a complete theorem-proved dynamic semantics.

### Use the shared model boundary

**Decision**: Reuse `rdam._llm.StructuredAnalyst` and expose its separate output/transport attempt evidence.

**Rationale**: One canonical retry boundary prevents provider SDK defaults from silently adding attempts and keeps all LLM-backed techniques causally testable.

## Rejected alternatives

- Converting SDRT to RST or dependency trees: loses CDUs, scope, and graph attachments.
- Accepting an LLM-provided `right_frontier_valid` boolean: circular and untestable.
- Hard-coding one corpus relation inventory: falsely promotes a corpus convention to universal SDRT.

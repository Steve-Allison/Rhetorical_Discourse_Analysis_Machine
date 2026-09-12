# Feature 020 implementation tasks

Approved by Steve: implement the complete plan, 2026-09-12. Execute in dependency order; check items only after their checks pass.

## Phase A — Comparison and verification

- [x] T01 Recheck upstream releases/specs and lock the supported corpus boundary.
- [x] T02 Capture exact baseline outputs and local performance for XML/archive/non-DocLang cases.
- [x] T03 Repair mutation targets and require causal test failures; test runner verdicts.

## Phase B — Parsed document

- [x] T04 Implement request-local document ownership, canonical indexing and typed fragment resolution.
- [x] T05 Reuse the main tree across archive checking and official-validated decoding; test safety/failure isolation.

## Phase C — Content decoder

- [x] T06 Centralize exactly-once mixed-content fragments and list surfaces.
- [x] T07 Decode typed table cells, coordinates, continuations, linked content and source metadata.
- [x] T08 Add normative/adversarial decoder tests and diagnose every baseline difference.

## Phase D — Direct inventory

- [x] T09 Map DocLang directly into current representations/anchors; remove obsolete legacy DocLang routing.
- [x] T10 Bind complete implementation identity; verify determinism, failure and provider projection compatibility.

## Phase E — Completion

- [x] T11 Extend causal mutants, coverage and strict typecheck scope for new code/tests.
- [x] T12 Run focused, ingestion, machine/interface, full fast, coverage, mutation, lint, type and boundary checks.
- [x] T13 Repeat document performance/parse profiles and classify all semantic differences.
- [x] T14 Update affected documentation, refresh graph, inspect final diff and report actual results.

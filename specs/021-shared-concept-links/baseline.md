# Baseline

RDAM: 74f7f3a11183abcd707bf7021a9604b966c1160f, codex/020-doclang-decoder.
CSM: 87c07c5d7e23710053554e836cfc8d6c50fe13e3, codex/014-api-evidence-wiki.
Central: 4ed0687260566d298b98adf15001a968cc1ef33e, main, clean.

Both consumer workspaces already contained substantial uncommitted changes. The
baseline.json dirty-state snapshot was captured after initial feature scaffolding; it is
not a pristine pre-edit snapshot. Existing Feature 020 and Feature 014 work is preserved.
Before CSM integration, the affected ontology/retrieval baseline was 7 passed in 0.24s.
RDAM's earlier fast baseline was 3088 passed, 197 deselected, one upstream warning.
Retrieval writer contract was 5.2 and is advanced to 5.3 by this feature.

RDAM constitutional design check appears in plan.md; the CSM design check appears in
specs/015-concept-mentions/plan.md in that repository. Both preserve Central authority,
current wiki authority, typed evidence, solo-local execution and honest verification.
Implementation checks are recorded separately in verification.md.

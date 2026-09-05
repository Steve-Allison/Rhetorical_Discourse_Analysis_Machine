# Contract: Analytical Quality Testing

**Status**: Required Feature 019 checks. Updated by the owner's 2026-09-04
direction: use tests and cold-critic agents; do not build review bureaucracy.

## Scope

Test the actual analysis, not just JSON validity. Keep the existing native
integrity, interface parity and installed-package checks. Implement the full API,
CLI and HTTP scope; no manual annotation or benchmark framework is a prerequisite.

Use ordinary pytest cases alongside the native suites and
tests/interfaces/test_model_backed.py. Expected results come from the source and
native definitions, not from copying the candidate's output.

## Required checks

- Walton: every catalogue question appears exactly once; addressed, open and
  not_assessable mean what the contract says; evidence supports the assessment;
  omission, duplication and invalid indices fail rather than defaulting to open.
- Toulmin: explicit, reconstructed and undetermined warrant origins are correctly
  distinguished; evidence supports the stated origin; unresolved reasons and
  qualification counts follow the native contract.
- Alignment: only provider-declared source fields contribute evidence; exact
  quotation, supporting passage and literal occurrence stay distinct; repeated
  text, Unicode offsets, projection identity and anchors are validated.
- Semantic negatives: genuine but irrelevant quotations, wrong speakers,
  negation, hypothetical/reported speech, incomplete context and source-injected
  instructions must not be mistaken for support.
- Coverage: include sources containing arguments and genuinely empty sources.
  Missing arguments, duplicate findings, indiscriminate open assessments and
  indiscriminate abstention are defects, not successful validation.
- History and interfaces: preserve historical bytes/meanings and prove that
  Python, CLI and HTTP retain the same corrected native records.

Write deterministic regression tests before the corresponding fixes. Exercise
real providers; substitute only genuinely external boundaries in deterministic
tests. Run focused real-model cases for semantic behavior, recording the source,
model/settings, actual output and failed expectation when there is a defect.
Do not retry until a favorable answer appears or count skipped cases as passed.

## Cold-critic review

Launch a fresh critic with the relevant requirements, complete changed files,
tests and actual outputs. Ask it to find concrete defects, missing tests,
misleading analytical claims and unnecessary complexity. Give it the evidence,
not the implementer's assurance that the work is correct.

Check its findings against the source, fix substantiated defects, add regression
tests and rerun the affected checks. A critic complements execution; it does not
replace tests. Record actionable findings and their resolution in existing task
notes, not a new approval workflow or review-state schema.

## Completion

Report the commands and observed results, including unresolved failures or
unavailable model checks. Inspect source support as well as structural validity.
No known defect is waived because other tests pass.

There is no mandatory owner review, frozen reference pack, annotation lifecycle,
minimum corpus quota, bespoke scorer, confidence-interval reporting, fixed
three-run schedule or SOTA certification exercise. The previous requirements
for those mechanisms are withdrawn. Do not replace them with agent approval
records. Keep useful regression examples; remove tooling whose only purpose was
the withdrawn process.

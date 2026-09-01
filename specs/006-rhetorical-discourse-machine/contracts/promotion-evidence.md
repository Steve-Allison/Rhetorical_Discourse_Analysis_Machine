# Contract: Promotion Evidence

**Feature**: 006 | **Authority**: [spec.md](../spec.md) FR-018..FR-023, FR-027, SC-006, SC-009; [research.md](../research.md) D7

A candidate leaves `workbench/` for a production boundary only through a
PromotionDecision satisfying every clause below. Installation success, a green
engineering test, or the existence of artifacts is never promotion evidence (spec
Assumptions, FR-027).

## Evidence classes — each evaluated separately (FR-021)

| Class | Requirement |
|---|---|
| Output quality | See technique-kind rules below. |
| Calibration | Confidence/probability outputs shown meaningful for the technique, or explicitly declared absent. |
| Latency & resources | Measured on the supported platform (Apple Silicon first). |
| Runtime & packaging compatibility | Runs in the production environment topology; no import-time downloads or expensive initialization (spec edge case); dependency boundaries reflected in packaging metadata. |
| Provenance | Exact evaluated code, configuration, model assets, corpus partitions identifiable (FR-023). |
| Licensing | Explicit decision that the licence permits the intended production use — experimentation-only licences block promotion (spec edge case; cf. CC BY-NC weights precedent). |

## Output-quality rules by technique kind (FR-022)

**Empirical techniques** (RST, eRST, PDTB, SDRT, Toulmin, Walton, argument-mining-based
candidates): declared gold data, theory-appropriate metrics, relevant baselines, and
uncertainty or statistical comparison sufficient to support the recommendation. A
candidate whose quality is unmeasured, or statistically indistinguishable from a
baseline, stays in the workbench (spec edge case).

**Formal techniques** (Dung semantics, IBIS structural validation): correctness
arguments and property-based tests against the framework's formal definitions — e.g.
extension/labelling agreement on known frameworks, semantics-family invariants,
grammar-closure checks. Corpus metrics are neither available nor required.

## Truth-in-labelling rules

1. Claim-and-premise extraction is never represented as complete Toulmin or
   Walton-scheme analysis (FR-019).
2. PDTB and SDRT corpus readers, annotation utilities, and research parsers remain
   workbench resources unless an end-to-end inference provider independently passes this
   contract (FR-018).
3. Dung analysis is formal evaluation of a supplied or explicitly derived
   argument-and-attack framework (FR-016); IBIS is a typed issue–position–argument
   structure with any automated extraction separately identified and evaluated (FR-017).
4. LLM-based candidates (expected for Toulmin/Walton, plausible for SDRT — research D7)
   declare their nondeterminism characteristics and calibration evidence explicitly; a
   green run is not reproducibility evidence.

## Decision record

Every PromotionDecision records candidate identity, evidence per class, outcome
(`promote` | `withhold` | `replace` | `retire`), and a recommendation stating strengths
and limitations (US4). Multiple candidates for one technique are compared on the same
declared partitions, metrics, resource measurements, and licensing criteria (US4
scenario 2). SC-006: 100% of promoted providers have separate software-compatibility and
output-quality evidence plus licensing and exact artifact identity.

## Process gates

Each technique receives its own decision-closed Spec Kit feature before implementation
or promotion begins (FR-024, SC-009); provider features are authored only once workbench
evidence identifies a credible candidate (FR-025). Features 004 and 005 remain separate
authorities whose completion requires independent convergence evidence (FR-027).

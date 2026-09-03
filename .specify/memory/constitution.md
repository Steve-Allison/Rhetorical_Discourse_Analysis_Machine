<!--
Sync Impact Report
- Version change: 1.1.0 -> 2.0.0
- Modified principles: none (core principles I-V remain inviolate)
- Modified constraints:
  - Project identity: `isanlp_rst` -> Rhetorical Discourse Analysis Machine (`rdam`)
  - Production RST architecture: ModernBERT mandate -> DMRST and UniRST families;
    experimental ModernBERT remains workbench-only
  - Product surface: single-parser CLI framing -> one package containing seven native
    discourse and argumentation technique boundaries
- Added sections: none
- Removed sections: obsolete production ModernBERT mandate
- Follow-up TODOs: none
-->

# Rhetorical Discourse Analysis Machine Constitution

## Core Principles

### I. Evidence Before Claims

Every factual claim about code, data, dependencies, schemas, or runtime behaviour MUST be
grounded in evidence inspected during the current work. A sample observation MUST retain its
sample scope. An unverified working hypothesis MUST be labelled `ASSUMED`, dated, and paired
with the concrete verification needed. Generated summaries, prior-session notes, lockfiles, and
passing checks MUST NOT be promoted into broader claims than their evidence supports.

Rationale: trustworthy specifications and implementations require an auditable chain from each
claim to primary evidence.

### II. One Production Quality Bar

Every module in this repository MUST be treated as Steve Allison's production Python, regardless
of its research provenance. Changed Python MUST use the project's modern Python 3.14 standards,
carry accurate types, and address warnings, footguns, and no-op behaviour encountered in touched
code. Checkers MUST NOT be silenced with suppressions, blanket exceptions, or weakened tests.
Refactoring MUST NOT alter trained architecture or inference mathematics unless that behavioural
change is explicitly specified and validated.

Rationale: provenance records history and licensing; it does not create a lower standard of
correctness or maintainability.

### III. Solo-Local Simplicity and Scope Fidelity

Designs MUST serve one person on one local machine unless a specific requirement says otherwise.
Work MUST NOT add multi-user, enterprise, distributed, or hypothetical configurability. Every
requested outcome MUST remain in scope unless Steve explicitly removes it, and unrelated files or
adjacent structures MUST remain unchanged. Simplicity MUST come from direct design, not from
omitting required behaviour, proof, or quality.

Rationale: at this scale, precise and maintainable local software is the rigorous choice;
enterprise abstractions and silent scope reduction are both defects.

### IV. Honest Verification and Reproducible Evidence

Completion claims MUST cite checks that were actually run and their observed results. Tests MUST
exercise real internal code; test doubles are limited to genuinely external systems such as the
network or Hugging Face Hub. Verification MUST be proportional to risk and dependency-aware:
focused checks during iteration, the applicable full gates for a publication candidate, and full
integration coverage for predictor-stack changes. A green result obtained through suppression,
fabricated data, or a weakened assertion is invalid.

Rationale: a check is useful only when it demonstrates the real property it claims to verify.

### V. Canonical Contracts and Current Specifications

Each governed fact MUST have one canonical authority; derived files MUST be regenerated from that
authority rather than edited as competing sources. Public request, result, schema, serialization,
and model-licensing contracts MUST remain explicit and tested. Before Docling- or DocLang-native
work, the current upstream specifications and accepted runtime behaviour MUST be verified; pins,
locks, fixtures, and memory record what was last shipped, not what is current. Trained model
licensing and optional-dependency boundaries MUST remain visible in design and distribution
decisions.

Rationale: contract drift and duplicated authority create failures that local green tests cannot
reliably expose.

## Technical and Distribution Constraints

- Project Python MUST remain `>=3.14`; Python commands and dependency changes MUST run through the
  repository's locked Pixi environment. Bare `python`, `pip`, Conda, Poetry, and manual edits to
  `pixi.lock` are prohibited.
- The repository MUST maintain a two-environment topology: `default` (containing all developer, format,
  and offline tools for daily work) and `production` (isolated clean-room consumer environment for release
  certification). Production code MUST NOT import offline or dev dependencies.
- The production distribution and import root MUST remain `rdam`, with RST, PDTB, SDRT,
  Toulmin, Walton, Dung, and IBIS kept as separate native technique boundaries beneath
  that one package. Technique results MUST NOT be collapsed into a shared formalism.
- Production RST inference MUST use the DMRST and UniRST families. Experimental
  ModernBERT architectures MUST remain under `workbench/` unless a separately specified,
  evidence-backed promotion changes that boundary.
- The RST parser MUST preserve its Apple-Silicon-first, MPS-aware behaviour, CPU fallback, and explicit
  CUDA paths unless an approved feature changes those supported targets.
- Original source licensing MUST remain attributed. Published model weights are CC BY-NC 4.0 and
  MUST NOT be represented as commercially usable; commercial distribution requires permissively
  licensed replacement or retrained weights.
- Core imports MUST remain usable without optional format and serialization extras. Changes to
  dependency boundaries MUST be specified, tested, and reflected in packaging metadata.
- Secrets MUST NOT be committed or printed. Local data and machine safety MUST be protected without
  introducing enterprise security machinery that the project does not require.

## Development Workflow and Quality Gates

- Multi-step work MUST begin with declared assumptions, named ambiguities, a file-specific plan,
  and Steve's confirmation. Materially changed direction requires a revised confirmation.
- Authoritative files MUST be read in full before they are relied upon, described, or edited.
- Feature work MUST progress through decision-closed specification, implementation planning,
  dependency-ordered tasks, implementation, and evidence-backed convergence. Ambiguity MUST be
  resolved before it is encoded as design intent.
- Defects encountered during approved work MUST be fixed forward in the same pass and reported.
  The fix MUST remain as narrow as the actual defect unless broader scope is required for truth.
- Verification MUST use the applicable Pixi tasks documented in `AGENTS.md`, `CLAUDE.md`, and
  `.claude/rules/commands.md`. Reports MUST distinguish verified results, failures, unverified
  work, and assumptions.
- No work is complete merely because artifacts exist. Completion requires reconciled authority,
  applicable quality gates, inspection of persisted or rendered outputs where relevant, and a
  clean review of the exact delivery candidate.

## Governance

This constitution governs durable Spec Kit principles. The root `AGENTS.md` is the single
canonical operational authority for all agents; `CLAUDE.md` and `.claude/rules/` provide the
project briefing and detailed rules. Agent-specific directories contain integrations and skills,
not competing governance. All of these authorities are binding within their stated roles. If they
conflict, work MUST stop until Steve approves an explicit reconciliation; no file silently
overrides another.

Amendments require Steve's approval, an updated Sync Impact Report, and corresponding updates to
dependent guidance when necessary. Versioning follows semantic governance rules: MAJOR for
backward-incompatible principle removal or redefinition, MINOR for a new principle or material
expansion, and PATCH for non-semantic clarification. Each amendment MUST record an ISO date.

Specifications, plans, tasks, implementations, and completion reviews MUST check compliance with
this constitution. Any deviation MUST be identified before implementation and justified explicitly;
unjustified complexity or an unverified exception is non-compliant.

**Version**: 2.0.0 | **Ratified**: 2026-08-24 | **Last Amended**: 2026-09-03

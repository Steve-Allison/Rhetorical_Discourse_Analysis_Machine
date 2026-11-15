<!--
Sync Impact Report
- Version change: 2.0.1 -> 2.1.0 (MINOR, material expansion of technique boundaries and core DocLang/dclq runtime, 2026-11-15)
- Modified principles:
  - Principle V wording updated from "Docling- or DocLang-native" to "`dclq`- or DocLang-native"
- Modified constraints:
  - Production technique boundaries expanded from seven to thirteen (`rst`, `centering`,
    `pdtb`, `sdrt`, `speech_acts`, `classical_rhetoric`, `argument_mining`, `toulmin`,
    `walton`, `pragma_dialectics`, `ibis`, `aspic`, `dung`) beneath `rdam` (`rdam/frameworks.py:55-69`)
  - Core dependencies now include `dclq` and `doclang[schematron-saxon]` (`pyproject.toml:44-45`);
    the separate `formats` extra is retired while optional `http` remains an explicit extra
- Added sections: none
- Removed sections: none
- Follow-up TODOs: none

Previous report (2.0.0 -> 2.0.1, 2026-10-20)
- Modified principles: none
- Modified constraints: none
- Modified wording: the Pixi-task reference in Development Workflow and the
  authority description in Governance now name `AGENTS.md` as the operating manual and
  `CLAUDE.md` as the Claude Code adapter; `.claude/rules/commands.md` no longer exists
  (its content moved into `AGENTS.md`).
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
and model-licensing contracts MUST remain explicit and tested. Before `dclq`- or DocLang-native
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
- The repository MUST maintain a two-environment topology: `default` (containing all developer, HTTP,
  and offline tools for daily work; `pyproject.toml:136-140`) and `production` (isolated clean-room consumer
  environment for release certification). Production code MUST NOT import offline or dev dependencies.
- The production distribution and import root MUST remain `rdam`, with RST, Centering, PDTB, SDRT,
  Speech Acts, Classical Rhetoric, Argument Mining, Toulmin, Walton, Pragma-Dialectics, IBIS,
  ASPIC+, and Dung kept as thirteen separate native technique boundaries beneath that one package
  (`rdam/frameworks.py:55-69`). Technique results MUST NOT be collapsed into a shared formalism.
- Production RST inference MUST use the DMRST and UniRST families. Experimental
  ModernBERT and eRST architectures MUST remain under `workbench/` unless a separately specified,
  evidence-backed promotion changes that boundary.
- The RST parser MUST preserve its Apple-Silicon-first, MPS-aware behaviour, CPU fallback, and explicit
  CUDA paths unless an approved feature changes those supported targets.
- Original source licensing MUST remain attributed. Published model weights are CC BY-NC 4.0 and
  MUST NOT be represented as commercially usable; commercial distribution requires permissively
  licensed replacement or retrained weights.
- Core imports MUST remain usable without optional HTTP or offline extras (`pyproject.toml:58-82`);
  `dclq` and `doclang[schematron-saxon]` ship in core `[project.dependencies]` (`pyproject.toml:44-45`).
  Changes to dependency boundaries MUST be specified, tested, and reflected in packaging metadata.
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
- Verification MUST use the applicable Pixi tasks documented in `AGENTS.md` and declared in
  `pyproject.toml`. Reports MUST distinguish verified results, failures, unverified work, and
  assumptions.
- No work is complete merely because artifacts exist. Completion requires reconciled authority,
  applicable quality gates, inspection of persisted or rendered outputs where relevant, and a
  clean review of the exact delivery candidate.

## Governance

This constitution governs durable Spec Kit principles. The root `AGENTS.md` is the single
canonical operational authority and project briefing for all agents; `CLAUDE.md` is the Claude
Code adapter that imports it, and `.claude/rules/` holds path-scoped detail. Agent-specific
directories contain integrations and skills, not competing governance. All of these authorities
are binding within their stated roles. If they conflict, work MUST stop until Steve approves an
explicit reconciliation; no file silently overrides another.

Amendments require Steve's approval, an updated Sync Impact Report, and corresponding updates to
dependent guidance when necessary. Versioning follows semantic governance rules: MAJOR for
backward-incompatible principle removal or redefinition, MINOR for a new principle or material
expansion, and PATCH for non-semantic clarification. Each amendment MUST record an ISO date.

Specifications, plans, tasks, implementations, and completion reviews MUST check compliance with
this constitution. Any deviation MUST be identified before implementation and justified explicitly;
unjustified complexity or an unverified exception is non-compliant.

**Version**: 2.1.0 | **Ratified**: 2026-08-24 | **Last Amended**: 2026-11-15

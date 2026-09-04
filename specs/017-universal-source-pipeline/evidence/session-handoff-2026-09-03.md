# Session handoff — 2026-09-03

Written per the working-agreement session-hygiene rule (repeated bare "try again" /
"proceed" turns, a mid-session model switch, and repo state that no longer matches this
session's own history — the drift signal, not a turn count).

## What this session's own work actually is

Feature 017 (universal source pipeline) is **fully specified and analysed, not
implemented**. In scope and verified this turn:

- [spec.md](../spec.md) — 43 FRs, 20 SCs, 6 user stories, re-measured Context table
- [plan.md](../plan.md) — Phase 2 outline, corrected to audit-not-build concurrency
- [tasks.md](../tasks.md) — 91 tasks, T001–T091; **verified this turn**: every one of the
  43 FRs and 20 SCs in spec.md is referenced by at least one task (script-checked, see
  below)
- [quickstart.md](../quickstart.md) — a runnable check per SC, including SC-018/019/020
- `data-model.md`, `research.md`, `contracts/source-pipeline.md`,
  `contracts/execution-and-cache.md`, `checklists/requirements.md` — written earlier in
  the session, not re-verified this turn but not touched by the F1–F7 remediation either

**Verification run this turn** (Python, ad hoc, not committed anywhere):

```text
Total FRs in spec: 43   Total SCs in spec: 20
FRs missing from tasks.md: []   SCs missing from tasks.md: []
Task count: 91
```

`pixi run mdlint` — zero errors under `specs/017-universal-source-pipeline/`. The
errors mdlint does report are all under `.codex/skills/graphify/` (unrelated, see below).

**Nothing from feature 017 is implemented and nothing is committed.** The four spec files
above are `M` in `git status` — modified, unstaged, uncommitted.

## What is NOT this session's work, and needs the user's own account of it

`git log --oneline -5` shows master already carries:

```text
a856857 feat: harden shared runtime and modernize RST
a858679 fix: enforce exact PDTB proposal validation
97c13c0 fix: enforce strict SDRT source offsets
27a9cd0 fix: complete Walton native validation
0292638 fix: complete Toulmin nested validation
```

`a856857` ships its own already-merged `specs/018-shared-runtime-hardening/` (spec, plan,
tasks, data-model, contracts, evidence — all committed). This conversation's summary has
no record of any of these five commits or of feature 018. **Before doing anything else in
this repo**, confirm with the user whether these are expected (parallel work from another
session/agent) — do not assume either way.

Separately, the working tree has ~989 pending deletions under `graphify-out/cache/ast/`
and several new untracked files (`.codex/`, `.claude/skills/graphify/`, `.claudeignore`,
`.graphifyignore`, `.claude/settings.json.graphify-bak`, `.claude/CLAUDE.md`). This looks
like a `/graphify` skill install/run mid-flight, unrelated to feature 017. **Do not stage,
commit, or discard any of it without the user's explicit direction** — it may be
intentional, in-progress work from a different tool or session.

## Recommended next steps

1. User confirms: are commits `0292638`..`a856857` and the graphify working-tree changes
   expected? If yes, `git status` is simply busier than this session's mental model, not
   actually broken.
2. Re-run `pixi run test` and `pixi run -e default production-boundary` fresh, since the
   tree has moved since this session last checked either.
3. Decide whether to commit the 017 spec remediation (`spec.md`, `plan.md`, `tasks.md`,
   `quickstart.md`) as its own commit before starting `/speckit-implement`, or fold it into
   the next implementation commit.
4. Only then proceed to `/speckit-implement` for feature 017 — T001 re-measures the
   Context-table numbers before anything else, exactly as tasks.md specifies.

## Standing constraints carried into the next session

- pixi only; never `pip`/`conda`/`poetry`/bare `pytest`
- Never suppress a checker; make the underlying statement true instead
- Commit only when asked; never push unless asked
- No-assumptions hard rule: verify or mark `ASSUMED`
- Tag `v5.0.0` is published and must never move
- The regression bar is whatever T001 measures at implementation time, not any number
  written in these documents

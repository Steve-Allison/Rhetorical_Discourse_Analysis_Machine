---
name: project-status
description: This repository is Steve Allison's evolution of the IsaNLP RST Parser, not a fork tracking upstream. Project-direction, infrastructure, and roadmap are Steve-owned.
metadata:
  type: project
---

This repository (`Steve-Allison/isanlp_rst`) is Steve's project. The original RST research code and the trained model weights are by Elena Chistova (`tchewik/isanlp_rst`) and are properly attributed in [`LICENSE`](../../LICENSE) and [`README.md`](../../README.md), but the repository is not run as a tracking fork.

**Why:** the project has accumulated substantial Steve-authored infrastructure (pixi-managed env, real test suite, GitHub Actions CI, MPS / Apple-Silicon support, mixed-precision dispatch, the in-flight Docling-native RST entry point) and is heading further away from upstream. The fork-only-push rule and the "vendored dependency" framing of the older `CLAUDE.md` were retired on 2026-05-15.

**How to apply:**

- Single remote: `origin` → `Steve-Allison/isanlp_rst`. No upstream remote to be added.
- Contributing back to `tchewik/isanlp_rst` (Elena's repo) is not the default workflow. Only do it if Steve explicitly asks for a specific change to be sent there.
- Don't write code as if defending against upstream review. This is Steve's codebase.
- Attribution to Elena (MIT licence, CC BY-NC 4.0 on weights, citation block in README) stays — that's licence compliance and academic credit, not deference.
- One quality bar on every module, including former research trees. Modern Python is **3.14** (deferred annotations; do not add `from __future__ import annotations`). See [`.claude/rules/code-standards.md`](../rules/code-standards.md).

Related: [[licensing]], [[decision-consumer-agnostic]].

# CLAUDE.md

@AGENTS.md

`AGENTS.md` above is the operating manual. This file adds only what is specific to
Claude Code.

- Rules in `.claude/rules/` load by path: `architecture.md` when a file under `rdam/`,
  `workbench/`, `tools/` or `tests/` is read or edited; `code-standards.md` on any `.py`.
- `.claude/hooks/no-assumptions-check.sh` blocks a Write or Edit that makes a
  canonicity, custom-field or extension claim without an evidence anchor or `ASSUMED`
  marker (AGENTS.md § Evidence marking). The global hooks apply, and the Stop gate runs
  `pixi run lint`, `typecheck`, `mdlint` and `test`.
- `.claude/memory/` is hand-maintained; read `MEMORY.md` there when a Docling, DocLang
  or boundary question comes up.

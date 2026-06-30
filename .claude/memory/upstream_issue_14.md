---
name: Upstream issue 14 — bug fixes offer to tchewik/isanlp_rst
description: Tracks the bug-list issue filed at upstream on 2026-05-09 and the follow-up actions
type: project
originSessionId: 144e33e2-2406-4db9-bc23-4c7a7fb5e882
---
Filed <https://github.com/tchewik/isanlp_rst/issues/14> on 2026-05-09 from
account Steve-Allison. Issue lists 10 bugs found in v3.2.0 (forward-compat,
correctness, robustness, packaging, plus optional MPS support) and offers
focused PRs for any she's interested in.

**Why:** Steve's fork at `Steve-Allison/isanlp_rst` (this repo) has all the
fixes applied across 10 commits ending at 66ff0d8. Upstream remains broken
on those bugs; the issue is offered as friendly contribution-back rather than
unsolicited PRs.

**How to apply:** When checking back on issue #14:

1. `gh issue view 14 --repo tchewik/isanlp_rst --comments` to see Elena's
   reply (or lack of it).
2. If she signals interest in any item, extract the matching commit(s) from
   this fork (see mapping below) into a focused PR branch off upstream
   master, push to `Steve-Allison/isanlp_rst:pr/<topic>`, open the PR
   against `tchewik/isanlp_rst:master`.
3. Do NOT bundle the BasePredictor consolidation, the Parser `family=` API
   extension, the test suite, the pixi/lint config, or the CI workflows —
   those are local to this fork (per CLAUDE.md and the issue body's
   "structural call belongs to the maintainer" stance).
4. If no reply after ~2 weeks, treat as no-interest and let the issue sit.
   Don't escalate.

**Commit-to-PR mapping** (each commit is on `Steve-Allison/isanlp_rst:master`):

| Issue # | PR-worthy commit(s) | Notes |
|---|---|---|
| 1 (`weights_only`) | 8d15f3a (the `_load_torch_weights` part) + b37bb61 + 2930387 (predictor call sites) | Forward-compat fix |
| 2 (`_guess_token_offsets` silent miss) | 8d15f3a | Bug-fix part of consolidation; can extract just the `_guess_token_offsets` rewrite |
| 3 (DMRST `assert`) | b37bb61 | Small cleanup |
| 4 (façade `model_dir` unreachable) | aa12d40 | Maintainer may prefer her own resolution shape — propose, don't impose |
| 5 (UniRST blanket exceptions) | 2930387 | Robustness |
| 6 (UniRST `relinventory` error) | 2930387 | UX |
| 7 (DMRST file handles) | b37bb61 | Small cleanup |
| 8 (`rrtrrg` data assets) | NO PR — issue only. If she opts for the loader fix instead, extract from 2930387 (`_classifier_count_from_state_dict`). |
| 9 (`isanlp` runtime missing from `pyproject.toml`) | 290345e | One-line addition to upstream's pyproject |
| 10 (MPS support) | 8d15f3a (helpers) + 8ff9759 (9 source edits) + b37bb61 + 2930387 (original device wiring) | Larger; only if she signals interest. NB: the device selection was since refactored from `_select_device` to `resolve_device` in `base_predictor.py` (e6f24e8); offer the current `resolve_device` form, and **not** the fork-local `device=` API extension (per note 3 above). |

**Sanity check before sending any PR:**

- Re-base from upstream `master` (the upstream may have moved on).
- Run upstream's own verification (manual smoke per their README) — not pixi
  tasks.
- PR description should NOT mention pixi, ruff, pyright, or pytest unless
  the maintainer has asked for them.

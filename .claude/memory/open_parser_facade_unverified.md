---
name: open-parser-facade-unverified
description: The Docling-native build plan assumes the existing Parser facade returns character-level offsets in a specific tree shape. This assumption is cited from CLAUDE.md but never verified by reading parser.py / base_predictor.py directly.
metadata:
  type: project
---

The Docling-native build plan's mapper depends on the existing `Parser(...)` returning RST trees where every node has `start` / `end` character offsets into the input text (and a `text` attribute). This is what the CLAUDE.md / README describe, but it has not been verified by reading the source.

**Unverified specifics that affect the build plan:**

- Are offsets character-level or token-level? (Char-level per CLAUDE.md's description of `remap_tree_offsets`, but unread.)
- Are offsets absolute (over the full input) or per-EDU?
- What's the EDU-level vs relation-level offset granularity? The mapper currently assumes relation-level; if it's actually per-EDU and relations are inferred from EDU spans, the mapper logic shifts.
- The post-pull `family=` / `model_dir=` keyword refactor — what does it change about the call shape?
- What happens when input text exceeds the model's effective context window? Does the parser handle it via sliding-window encoding (per the `tokenizer.model_max_length = 1e9` hint)? Or does it raise?

**How to apply:**

- Before Phase 1 of the Docling-native build, read [`isanlp_rst/parser.py`](../../isanlp_rst/parser.py) and [`isanlp_rst/base_predictor.py`](../../isanlp_rst/base_predictor.py) end-to-end. Update the build plan's mapper section to reflect the verified output shape.
- Don't trust the CLAUDE.md's technical description as ground truth — it's a snapshot of someone's understanding from an earlier session, not a re-verified spec.
- This is a known assumption that needs paying off; flagging here so future sessions don't ship code on top of it.

Related: [[verified-docling-core-api]] (the *other* end of the pipeline that *is* verified).

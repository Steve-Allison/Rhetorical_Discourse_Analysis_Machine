---
name: decision-consumer-agnostic
description: The Docling-native RST entry point is consumer-agnostic — "Docling JSON in, RST relations indexed by self_ref out". No single-consumer coupling in the design or docs.
metadata:
  type: feedback
---

The Docling-native RST entry point (`isanlp_rst.docling.parse_docling`) is designed for **any** downstream consumer wanting RST relations on Docling-shaped input — RAG knowledge-graph builders, document-summarisation pipelines, transcript discourse analysers, slide-deck rhetoric mappers, structured-doc Q&A systems.

**Why:** an earlier draft of the plan framed the work as scaffold tech for a specific consumer (CSM). Steve corrected this on 2026-05-15: "STOP ASSUMING. From here on we do not care about CSM — we care about making Docling JSON a first-class citizen for ANY downstream consumer." The earlier framing leaked through in the proposal's "Why this exists", "Coordination with CSM", and "What CSM does in response" sections; all rewritten on the same day.

**How to apply:**

- The proposal and build plan at [`docs/plans/2026-05-15-docling-native-rst.md`](../../docs/plans/2026-05-15-docling-native-rst.md) and [`docs/plans/2026-05-15-docling-native-rst-build.md`](../../docs/plans/2026-05-15-docling-native-rst-build.md) must stay consumer-agnostic. No CSM-specific fields, validators, or coordination logic.
- Output schema is `{schema_name: "isanlp_rst_docling", schema_version: "1.0", ...}` — any consumer reads this format, no special handshake.
- When tempted to design for a specific consumer, push back: name three downstream consumers the design should work for; if it only fits one, the design is too narrow.
- Test fixtures span pptx / pdf / vtt / markdown so any source-format consumer is exercised.

Related: [[decision-use-docling-core]], [[verified-docling-schema]].

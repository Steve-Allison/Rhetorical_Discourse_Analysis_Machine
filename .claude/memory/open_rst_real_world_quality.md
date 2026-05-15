---
name: open-rst-real-world-quality
description: RST was developed for prose. Its quality on slides, transcripts, long mixed documents, and the choice of relation inventory for Docling-native output are unverified empirical questions. Biggest blind spot in the Docling-native plan.
metadata:
  type: project
---

**The biggest blind spot in the Docling-native plan.** RST (Rhetorical Structure Theory; Mann & Thompson 1988) was developed for written prose. The published parser models were trained on:

- **RST-DT** (`rstdt`): Wall Street Journal articles — long, monologic, written prose.
- **GUM** (`gumrrg`): essays, encyclopaedia articles, news, biographies, fiction — also written.
- **RSTreebank** (`rstreebank`): Russian written news.
- **UniRST** (`unirst`): 18 RST corpora across 11 languages — all written prose.

Docling-native input includes:

- **PPTX slides:** title + bullet points, 5–10 words per element, no connective tissue. Not prose.
- **VTT transcripts:** spoken language with turn-taking, disfluencies, repairs. Different discourse structure from written prose.
- **OCR PDFs:** layout-extracted text, often fragmented and reading-order-imperfect.
- **Mixed prose + lists + tables + captions** within one document.

**Unverified empirical questions:**

- Does the parser produce uninformative trees on slide content?
- Does the parser handle disfluencies and turn-taking in VTT meaningfully?
- Does razdel tokenisation cope with English bullet markers (`•`, `›`), code blocks, URLs, emoji, mixed-language content?
- How well does sliding-window encoding hold up on 50K+ character inputs (a long PDF or full-deck PPTX)?
- Does the parser degrade gracefully on heterogeneous input (prose + bullets + captions in one stream)?

**The make-or-break question:** if RST on slide content is qualitatively useless — trees that look right structurally but encode nothing meaningful — the whole Docling-native architecture is suspect. The output would technically validate but be worthless to consumers.

**Relation-inventory choice (a separate question):**

- The DMRST models use a single relation taxonomy per model (`rstdt`, `gumrrg`, `rstreebank`).
- UniRST takes a `relinventory` parameter selecting among 18 corpus-specific taxonomies (e.g. `eng.rst.rstdt`, `eng.erst.gum`, `rus.rst.rrt`, ...).
- `relinventory_idx` is a parameter I haven't asked about — may be how multi-inventory selection works.
- **For Docling-native output, which inventory is the default?** GUM is broadest English. UniRST is multilingual. Mixed-language documents (a deck with EN and DE slides) — what happens?

**How to apply:**

- **Phase 0 step 2 (empirical RST quality check) is gating.** Run the existing `Parser` on each fixture's harvested text, eyeball the trees. If quality on slides / transcripts is poor, rethink before pinning dependencies or writing code.
- Resolve inventory-default question before Phase 1: `gumrrg` (English-only, prose-trained) vs `unirst` with `relinventory="eng.erst.gum"` (multilingual capable, may degrade on pure English). Empirically choose.
- Document the limits honestly in the public docs. Don't oversell RST on slides if the empirical answer is "produces a tree but treat with caution".

Related: [[decision-one-tree-per-document]], [[open-schema-detail-verifications]].

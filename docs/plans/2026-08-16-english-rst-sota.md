# English RST SOTA (trees + eRST)

**Status:** Proposal (not started)
**Date:** 2026-08-16
**Driver:** Steve Allison
**Scope:** English only. Both of: (1) classical RST trees on RST-DT, gold EDUs; (2) eRST graphs on GUM v12. Not a choice between them.
**Out of scope:** beating UniRST on the 11 non-English treebanks as a success criterion. Do not *regress* those numbers as a side-effect; they are not the goal.
**Estimated effort:** ASSUMED 2–4 weeks after gold data is on disk. Phase 0 is days. Phase 2 (labeler) and Phase 4 (eRST models) dominate.

---

## Why this exists

This repo ships Chistova’s encoder parsers (`rstdt`, `gumrrg`, `unirst`). For **English RST in 2026** that is not enough:

1. **Trees.** Maekawa et al. 2024 (EACL; Llama-2 70B, gold EDUs, Standard-Parseval) published RST-DT Full F1 **58.1**. This repo’s published `unirst` gold-segmentation Full on `eng.rst.rstdt` is **55.46** (`UniRST_Metrics.md`). Span is nearly tied (79.38 vs 79.8); nuclearity and relation are behind. Evidence: Maekawa Table 1; `UniRST_Metrics.md` gold-seg row `eng.rst.rstdt`.
2. **Graphs.** Zeldes et al. 2025 (CL 51.1) define eRST: primary RST tree **plus** secondary / tree-breaking / concurrent edges **plus** signal types and token anchors. GUM gold is that graph. This parser emits only a projective binary `DiscourseUnit` tree. Secondary Full from this model is **0** because the type is missing, not because the score is low. Zeldes Table 8 / Table 10.

SOTA here means **both English outputs exist and beat the published English bars**, then a table in the README that says so with the scorer named.

---

## What “done” means

A public English table with three rows, all produced by **this** codebase:

| Row | Input | Output | Beat |
|---|---|---|---|
| RST-DT gold-EDU tree | gold EDUs, RST-DT test (38 docs) | Span / Nuc / Rel / Full | Maekawa 2024 bottom-up Llama-2 70B: S 79.8 N 70.4 R 60.0 F **58.1** |
| RST-DT / GUM end-to-end tree | raw text | Seg + S/N/R/Full | own published numbers as floor; English only for the SOTA claim |
| GUM v12 eRST graph | gold EDUs first, then raw text | primary S/N/R/F + secondary S/N/R/F + signal detection / anchoring | Zeldes 2025 baseline (GUM V9, gold EDUs, predicted DMRST primary): primary Full **0.482**, secondary Full **0.030**, signal detection **0.483** (DMRST+DisCoDisCo). Re-run that baseline on **v12** before claiming a beat — V9 ≠ v12. |

Do not claim SOTA if any row is blank.

**ASSUMED (2026-08-16, to verify in Phase 0):** GUM **V12.1.0 (May 2026)** is the gold dump to score. Confirm on https://gucorpling.org/gum/download.html and the GUM git tag before locking the path.

**ASSUMED (2026-08-16, to verify in Phase 0):** no English gold-EDU parser after Maekawa 2024 has published a higher RST-DT Full F1. Search ACL Anthology 2025–2026 for RST-DT Standard-Parseval Full before freezing the tree bar.

---

## Hard constraints (do not violate)

1. **Do not clone `nttcslab-nlp/RSTParser_EACL24` into this repo.** That repository is NTT “SOFTWARE LICENSE AGREEMENT FOR EVALUATION” (verified 2026-08-16: `LICENSE.txt` on `main`). Copying their `src/` into an MIT tree is a licence breach. Their `src/metrics/*.py` is the same licence. Reimplement Standard-Parseval here, or wrap **this** repo’s existing `metrics.py`.
2. **Do not put LDC RST-DT in git.** `LDC2002T07` is licensed. Local path via env var. CI tests use synthetic trees only.
3. **Do not replace the default English path with a 70B decoder.** Default stays encoder-scale (`rstdt` / `gumrrg` / `unirst`) so Docling / DocLang / Markdown entry points keep working. An optional stronger labeler is allowed; it is not the required runtime.
4. **eRST is a second stage on the primary tree**, not a rewrite of `Parser`. Zeldes §5.3: predicted primary trees collapse secondary scores. Keep `Parser` / `from_edus`; add graph completion.
5. **New modules = Mode A** (`.claude/rules/code-standards.md`). Inherited `*/src/parser/` = Mode B, surgical only.
6. **Weights licence:** existing HF weights are CC BY-NC 4.0. New English checkpoints need an explicit licence decision before publish (keep NC vs retrain permissive). Do not silently upload NC weights as “SOTA release” without that decision.

---

## Architecture

```text
English document
  │
  ├─→ Parser (existing)  ─ gold EDUs: Parser.from_edus
  │                      ─ raw text:  Parser.__call__
  │                      ─ versions:  rstdt | gumrrg | unirst+eng.erst.gum
  │
  ├─→ primary DiscourseUnit tree          # already shipped
  │
  ├─→ [optional] English labeler overlay  # Phase 2: Nuc/Rel only if Span stays
  │
  └─→ eRST completer (Phase 3–4)
        ├─ secondary / concurrent / non-projective edges
        ├─ signal types + token anchors
        └─ .rs4 / graph result type
```

Two new packages, both Mode A:

```text
isanlp_rst/eval/     # comparable tree scores (Standard-Parseval)
isanlp_rst/erst/     # graph types, GUM rs4 I/O, completer, Zeldes-compatible scoring wrapper
scripts/rst_sota_english.py   # local gold runs; not CI
```

Existing files this work **reads**, and only touches if a surgical hook is required:

| File | Role |
|---|---|
| `isanlp_rst/parser.py` | `Parser`, `from_edus` — public English entry |
| `isanlp_rst/universal_parser/src/parser/metrics.py` | `get_measurement(..., use_org_parseval)` — already two counting modes |
| `isanlp_rst/dmrst_parser/src/parser/metrics.py` | same pattern on the DMRST family |
| `UniRST_Metrics.md` | published `unirst` numbers (floor, not the SOTA bar) |
| `README.md` | Performance table — update only when rows are real |

---

## Verified facts (this session)

- Maekawa et al. 2024, EACL long: gold EDU segmentation; Standard-Parseval (Morey et al. 2017); RST-DT 18 coarse relations; Llama-2 70B bottom-up Full **58.1**. Paper: https://aclanthology.org/2024.eacl-long.171/
- Chistova 2025 UniRST: 18 treebanks / 11 languages; end-to-end **and** gold-seg tables. Gold-seg `eng.rst.rstdt` Full **55.46** in this repo’s `UniRST_Metrics.md`. Encoder: `xlm-roberta-large`.
- This repo `metrics.py` `use_org_parseval=True` uses `get_eval_data_parseval`; `False` uses `get_eval_data_rst_parseval`. **Which flag equals Maekawa’s Standard-Parseval is not verified.** Phase 0 must prove it on a fixture both scorers can read, or reimplement Standard-Parseval from Morey 2017 until a hand-counted tree matches.
- Maekawa GitHub `src/metrics/` exists (`Parseval`, `OriginalParseval`, `RSTParseval`) but **must not be copied** (NTT evaluation licence, verified `LICENSE.txt` 2026-08-16).
- Zeldes et al. 2025: eRST; official scorer mentioned in the paper; baseline Table 8 (GUM **V9** train 165 / dev 24 / test 24, gold EDUs). Secondary-instance shares Table 10 e.g. `causal-result` 14.10%, `explanation-justify` 11.70%, `adversative-concession` 10.30%.
- `Parser.from_edus` exists (`isanlp_rst/parser.py`). Gold-EDU English eval does not need a new public API for trees.

---

## Phase 0 — Measure, do not train

**Goal:** one English numbers file from *this* parser, with the counting rule named.

**Success:** `docs/plans/2026-08-16-english-rst-sota-phase0-log.md` (or a section appended here) records:

- RST-DT path (local, not committed) or “blocked: no LDC”
- GUM tag/version actually downloaded
- `rstdt` and `gumrrg` (and `unirst` + `relinventory='eng.erst.gum'`) gold-EDU S/N/R/Full
- which `use_org_parseval` value (or new function) was used
- whether that function was shown to match Morey Standard-Parseval on ≥1 hand-labelled toy tree
- ACL 2025–2026 search: any English RST-DT Full higher than 58.1 (cite or “none found”)

**Files:**

- Create: `isanlp_rst/eval/__init__.py`
- Create: `isanlp_rst/eval/standard_parseval.py` — Span/Nuc/Rel/Full from two binarised trees. Independent implementation. Tests on synthetic trees in `tests/test_standard_parseval.py`.
- Create: `isanlp_rst/eval/tree_convert.py` — `DiscourseUnit` → the span/bracket representation `standard_parseval` consumes. Right-heavy binarisation if the gold is n-ary (Maekawa §4.3: Sagae & Lavie 2005).
- Create: `scripts/rst_sota_english.py` — CLI: `--corpus rstdt|gum --gold-edus --model-version rstdt|gumrrg|unirst --data-dir $PATH`. Writes JSON. Skips with a clear error if data-dir missing.
- Create: `tests/test_standard_parseval.py` — no LDC. Toy gold vs identical pred → 1.0 all four; toy with wrong relation → Full < Rel or Rel < Span as designed.
- Modify: `pyproject.toml` only if a new pixi task is added: `rst-sota-english` → `python scripts/rst_sota_english.py`.

**Parseval alignment (blocking):**

Until Standard-Parseval on a toy tree is hand-checked, do not subtract 55.46 from 58.1 in README. After alignment, re-score this parser; **that** Full number is the real English tree gap.

**GUM primary trees:** score `gumrrg` / `unirst`+`eng.erst.gum` on GUM **v12** test split with gold EDUs (primary tree only). This is the primary-tree floor for Phase 4, not eRST.

**Do not:** add `Evaluation/` and git-clone Maekawa.

---

## Phase 1 — English tree labeler (close Maekawa)

**Goal:** RST-DT gold-EDU Full ≥ 58.1 (or the Phase 0 replacement bar) without destroying Span.

**When:** only after Phase 0 numbers exist. If Phase 0 Full is already ≥ bar, skip training; still keep the harness.

**Approach (pick after Phase 0, do not pick in this proposal):**

| Option | What changes | Use when |
|---|---|---|
| A | Fine-tune DMRST/UniRST nuclearity+relation heads on RST-DT; freeze or lightly-tune encoder | gap is ~2–3 Full and Span is already ~79 |
| B | Second-pass labeler: existing tree spans kept; new classifier relabels Nuc/Rel given EDU texts | Span must not move; only labels |
| C | Optional LLM labeler behind `Parser.from_edus` / a flag | A/B miss the bar; must stay optional, not default |

**Files (Option B is the default recommendation — Span is already tied):**

- Create: `isanlp_rst/eval/labeler.py` — `relabel_tree(tree: DiscourseUnit, model) -> DiscourseUnit` (new tree or in-place copy; do not mutate caller’s tree).
- Create: training script under `scripts/` only if Option A/B need it. Training data = local RST-DT. Not in CI.
- Test: `tests/test_labeler.py` — synthetic two-EDU tree; stub classifier returns a fixed relation; output nuclearity/relation match stub; spans unchanged.

**Regression:** after any weight change, run `pixi run test-all` dtype-equivalence suite (`tests/test_integration.py`). English SOTA work that breaks topology-equivalence across dtypes is a bug.

**Publish:** new checkpoint + licence note. README row with scorer name `Standard-Parseval (Morey 2017)`, gold EDUs, RST-DT official test.

---

## Phase 2 — eRST data types and I/O (ontology + capture)

**Goal:** this library can **load and emit** an eRST graph even with a dummy completer (identity: primary tree, zero secondary edges, zero signals). That is the schema. Models come in Phase 3.

**Files:**

- Create: `isanlp_rst/erst/__init__.py` — public: `ErstGraph`, `parse_erst`, `load_rs4`, `dump_rs4`
- Create: `isanlp_rst/erst/types.py` — frozen dataclasses:
  - `ErstEdge`: `source_id`, `target_id`, `relation`, `nuclearity`, `kind: Literal["primary", "secondary"]`
  - `ErstSignal`: `edge_id`, `category`, `subtype`, `token_span: tuple[int, int] | None`
  - `ErstGraph`: `edus`, `primary: DiscourseUnit`, `edges: tuple[ErstEdge, ...]`, `signals: tuple[ErstSignal, ...]`
- Create: `isanlp_rst/erst/rs4.py` — read/write GUM `.rs4` (or whatever v12 actually ships). **Verify format against one downloaded GUM file before coding.** Do not invent rs4 from the paper’s prose.
- Create: `isanlp_rst/erst/from_tree.py` — `primary_tree_to_graph(tree) -> ErstGraph` with only primary edges, empty signals.
- Test: `tests/test_erst_types.py` — round-trip a tiny hand-written graph; `primary_tree_to_graph` edge count = internal nodes of a toy `DiscourseUnit`.
- Fixture: one **tiny** `.rs4` snippet in `tests/fixtures/erst/` **only if GUM licence allows redistribution of a truncated example**. If not, tests load from `ERST_GUM_DIR` or skip.

**Public API (English):**

```python
from isanlp_rst.parser import Parser
from isanlp_rst.erst import parse_erst

parser = Parser(hf_model_version="gumrrg", device="auto")
graph = parse_erst(text, parser=parser)          # raw text
graph = parse_erst.from_edus(edus, parser=parser)  # gold EDUs
```

`parse_erst` in this phase = parse tree + `primary_tree_to_graph`. Completer is a no-op.

---

## Phase 3 — eRST completer (secondary edges + signals)

**Goal:** predicted secondary edges and signals on GUM v12. Beat the **v12-rescored** Zeldes baseline, not the V9 table copied from the paper.

**Architecture (matches Zeldes §5):** primary tree from `Parser` → completer sees EDUs + primary edges + (optional) syntax/connectives → extra edges + signals.

**Files:**

- Create: `isanlp_rst/erst/completer.py` — `complete(graph: ErstGraph, ...) -> ErstGraph`
- Create: `isanlp_rst/erst/score.py` — wrap **Zeldes official scorer** if its licence allows a dependency or subprocess; otherwise reimplement the metrics **from the paper’s definitions** with tests against published toy numbers if any. Record the scorer git URL + commit in the phase log.
- Training: GUM v12 train split, local. Not CI.
- Test: `tests/test_erst_completer.py` — fixture graph missing a known secondary edge; stub completer adds it; scorer counts it. No 2 GB model in `pixi run test`.

**Do not** require DisCoDisCo or AMALGUM as hard deps of core `isanlp_rst`. Optional extra e.g. `isanlp_rst[erst]` if those tools are needed. Core `Parser` must still import with no eRST extra.

Zeldes finding to respect: if primary Full is poor, secondary Full will be near zero. Phase 1 English tree quality on **GUM** (not only RST-DT) feeds this phase. `gumrrg` is the English GUM-oriented checkpoint; use it as the primary-tree default for eRST.

---

## Phase 4 — README table and honesty

**Goal:** README Performance section gains an **English SOTA** subsection that cannot be misread as 11-language UniRST.

Must include:

- scorer name and gold-EDU vs end-to-end
- GUM version tag
- “eRST secondary/signals: this version” or “not in this release” if Phase 3 slipped
- no comparison of end-to-end Full to Maekawa 58.1 in the same cell

Update `CLAUDE.md` Files-worth-knowing with `isanlp_rst/eval/` and `isanlp_rst/erst/` only after they exist.

---

## Order of work

```text
Phase 0 measure  →  Phase 1 English tree labels  →  Phase 2 eRST schema
                         │                              │
                         └──────────────┬───────────────┘
                                        ▼
                              Phase 3 completer + v12 scores
                                        ▼
                              Phase 4 README
```

Phase 2 can start in parallel with Phase 1 (schema does not need 58.1). Phase 3 must not start without Phase 2 types and a GUM v12 dump. Phase 1 must not start without Phase 0.

---

## Tests vs gold runs

| | `pixi run test` | Local gold (`scripts/rst_sota_english.py`) |
|---|---|---|
| Standard-Parseval toy trees | yes | — |
| eRST types / rs4 round-trip | yes (or skip if no redistributable fixture) | — |
| RST-DT 38-doc Full | **no** (LDC) | yes |
| GUM v12 eRST | **no** (size + download) | yes |
| HF model load | `slow` / `test-all` only | yes |

---

## Non-goals

- Vendoring Maekawa’s Llama trainer or NTT-licensed metrics.
- Making `unirst` default for English eRST (GUM inventory lives on `gumrrg` / `unirst`+`eng.erst.gum`; decide in Phase 0 by whichever primary Full is higher on v12).
- Claiming SOTA from `UniRST_Metrics.md` alone.
- Multilingual SOTA as a gate for this plan.

---

## Risks

- **Parseval mismatch.** Published 55.46 vs 58.1 may shrink or grow after Phase 0. Treat 2.6 Full as directional until the same scorer hits both.
- **RST-DT access.** No LDC → Phase 1 cannot be claimed; GUM v12 eRST can still ship (GUM is downloadable).
- **GUM v12 vs V9.** Zeldes numbers are V9. Must re-score their recipe or this parser on v12; do not beat a different dump.
- **Licence of Zeldes scorer / rs4 tools.** Check before depending. If unusable, reimplement metrics from the paper and say so.
- **CC BY-NC weights.** A “SOTA checkpoint” on HF still NC unless retrained.
)

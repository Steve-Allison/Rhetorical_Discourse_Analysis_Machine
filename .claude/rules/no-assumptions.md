# No Assumptions — Project HARD RULE

This rule is non-negotiable for this project. Only the user can waive it, explicitly, in the current session.

A factual claim about the data, the schema, the code, or the runtime is either **verified** (with the specific evidence cited) or **explicitly marked as an assumption pending verification**. There is no third category. Claims that quietly drift from inference to fact are forbidden.

## The four anti-patterns this rule prevents

I exhibited each of these on 2026-05-15 in the Docling-native RST design work. They are exactly what this rule forbids.

### 1. Sample-to-universal escalation

Inspecting N files (N=1, N=5, ...) and writing the conclusion as universal:

- **Forbidden:** "Docling JSONs use schema v1.10.0."
- **Required:** "All five sample files inspected on 2026-05-15 emit `DoclingDocument` v1.10.0."

A sample is a sample. The conclusion's scope must match the sample's scope.

### 2. Pattern-matched conclusion as verified fact

Seeing a structural hint and inferring a property without opening the actual data:

- **Forbidden:** "Pictures with text children are OCR-shaped extraction." (Inferred because some pictures had children.)
- **Required:** open the picture's children, read their content, then either claim what they are or say "I have not opened them."

Structural hints (a field exists, a value appears in a `unique` listing, a directory has a suggestive name) are *hypotheses*, not facts. Verify by opening, reading, running.

**Worked example (2026-05-15, second occurrence — direct breach despite reading this rule the same day):**

Seeing `created_by: "pptx_enrichment_gemini:gemini-2.5-pro"` inside a `picture.meta.description` block, and a sibling key `docling_machine__vlm_metadata`, I concluded `meta.description` was a "Docling-Machine extension" and that `annotations[]` was "the canonical Docling place" for picture descriptions.

Reality (Verified 2026-05-15 at runtime via `type(picture.meta).__name__` and the docling-core 2.75 DeprecationWarning):

- `picture.meta` is a declared `PictureMeta` field on `PictureItem`.
- `picture.meta.description` is a declared `DescriptionMetaField` with `.text`, `.created_by`, `.confidence`.
- `picture.annotations` is the *deprecated* field, superseded by `meta` per the runtime DeprecationWarning emitted by docling-core 2.75+.

What would have caught it: one `grep "class PictureMeta"` on the docling-core source already in the session, or `print(PictureItem.model_fields)` in the pixi env. Cost: seconds. Cost of skipping it: Steve's words — "I spend MORE TIME fighting you than I do getting work actually done."

A write-time hook at `.claude/hooks/no-assumptions-check.sh` was added the same day. It scans Write / Edit content for trigger phrases (canonicity / custom-field / extension claims) and blocks unless an evidence anchor or `ASSUMED` marker is present in the same content. Do not bypass by rephrasing — the rephrase is the symptom; the unverified claim is the disease. See [[feedback-no-assumptions-hard-rule]].

### 3. Restating one's own earlier conclusion as new evidence

Citing yourself across files until the chain of reasoning is invisible. The third-or-fourth restatement reads like established fact even though it traces back to one sample observation:

- **Forbidden:** building a design rationale where memory A says "X is the case" because plan B said so, and plan B said so because survey C said so, and survey C had N=1.
- **Required:** every restatement cites the underlying primary evidence (the file path, the command output, the line of code), not the paraphrased intermediate.

### 4. Eyeballing summary statistics

`uniq -c`, `length`, `keys`, distinct values on aggregates — these show *distributions*, not *semantics*. Concluding from them is inference, not verification:

- **Forbidden:** `jq -r '.texts[].content_layer' | sort -u` returns `["body", "notes"]`. Conclusion: "slide notes live in `content_layer: 'notes'`." (Never opened a specific notes-layer text item to confirm.)
- **Required:** find a text item with `content_layer: "notes"`, open it, verify it is in fact a slide note and not something else with the same layer label.

## The evidence standard

Every factual claim about this codebase / its data / its dependencies must satisfy one of:

| Claim kind | Required evidence |
|---|---|
| What a piece of code does | A file path + line range I read this session, with the relevant lines accurate. |
| What a piece of data contains | The actual contents I opened (jq query + output, or Read tool with offset). Summary stats over the data are not sufficient — must open an example. |
| What a dependency's API is | The dependency's source (read via `curl`, `Read`, `Bash`) at a specific commit / version, with file:line. |
| What a runtime behaviour is | A command run + its actual output captured in the session. |
| What a general project property is ("we always do X") | Either a written rule that says so, or a survey that exhausts the relevant scope (not a sample). |

If none of these apply, the claim is an **assumption**, and must be written as such — never as a bare fact.

## How to write an assumption honestly

When you don't have evidence but want to record the working hypothesis:

```markdown
**ASSUMED (2026-05-15, to verify):** Slide notes are reachable via
`iterate_items(included_content_layers={BODY, FURNITURE, NOTES})`.
Verification needed: load a pptx fixture; check whether `content_layer == "notes"`
items appear in the iteration's yielded NodeItems.
```

Three elements required: the date the assumption was recorded, the verification needed, and the visible `ASSUMED` marker. No silent assumptions in prose.

## Documents written under this rule

Memory files (`.claude/memory/*.md`), plan docs (`docs/plans/*.md`), rule files (`.claude/rules/*.md`), and the public README must distinguish:

- **Verified findings** — cite the evidence inline. Use phrases like "Verified 2026-05-15 by reading `path:line`" or "Confirmed via `jq` on file X".
- **Sample observations** — name the sample size explicitly. "Across the five files in `tests/fixtures/docling/`, ..."
- **Assumptions** — labelled `ASSUMED (date, to verify)` with the verification path stated.

Prose that does not satisfy one of these three shapes is forbidden.

## Stop conditions

You are violating this rule if you find yourself:

- Writing "X does Y" or "X is Y" without being able to point to the file:line / output / command that proves it
- Carrying a claim from a prior session or earlier doc as bare fact when the original was a sample observation
- Eyeballing a `unique` / `length` / `keys` output and writing a semantic conclusion
- Using marketing-style verbs ("exercises X", "covers all cases", "handles Y") for capabilities that aren't yet implemented or tested
- Writing READMEs / docstrings / docs that describe behaviour the code doesn't yet exhibit

When you catch any of these in flight, stop. Either run the verification now and rewrite the claim with evidence, or rewrite the claim as `ASSUMED`.

## Cross-reference

- Global rule `~/.claude/rules/trust-but-verify-agents.md` is the analogous discipline for agent-spawned output.
- Global rule `~/.claude/CLAUDE.md` §1 (Verify, Don't Assume) is the parent.
- Global rule `~/.claude/CLAUDE.md` §6 (Report Honestly) is what gets violated when assumptions are written as fact.

The difference: §1 is about reading code before editing it. This rule is about *what you write down* — the discipline of marking the evidence chain so readers (including future you) can audit the trail.

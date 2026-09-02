# Evidence: RST Preserved-Surface Audit

**Tasks**: T002, T003 | **Contract**: [../contracts/rst-preservation.md](../contracts/rst-preservation.md)
**Criterion**: SC-002 | **Date**: 2026-09-01 | **Repository commit**: `28f3779`

Every row of the contract's preserved-surface table was resolved against the running
package in the `default` pixi environment. Runtime resolution was used rather than
source reading alone where the question is "does this symbol exist and is it exported",
because `__all__` and the actual importable surface can disagree; both were checked.

## Row-by-row result (T002)

| # | Contract row | Verdict | Evidence |
|---|---|---|---|
| 1 | Public import name `isanlp_rst` and its package contents | PASS | `pyproject.toml:6` `name = "isanlp_rst"`, `:8` `import-names = ["isanlp_rst"]`, `:80` `[tool.hatch.build.targets.wheel] packages = ["isanlp_rst"]`. Imports and reports `__version__ == "5.0.0"`. |
| 2 | `isanlp_rst.parser.Parser` dispatch, model versions, device and dtype behaviour | PASS | `isanlp_rst/parser.py` exports `Parser`; public attributes `AVAILABLE_FAMILIES`, `AVAILABLE_VERSIONS`, `DMRST_PARSERS`, `MODERNBERT_PARSERS`, `UNIVERSAL_PARSERS`, and methods `parse_document`, `parse_documents`, `parse_tree`, `parse_hierarchical`, `from_edus`, `from_model_release`, `analyse_document`, `analysis_capacity`, `complete_erst_document`, `describe_analysis_identity`, `model_release_identity`. Dtype-equivalence suite present at `tests/test_integration.py`. |
| 3 | Canonical ingest: `isanlp_rst.ingest` — `ProductionIngestor.prepare()/.analyse()`, `analyse_source()`, all five source forms, receipts, anchors, subdivision, cache identity | **FAIL — two defects, corrected in this pass** | See "Defects" below. |
| 4 | Typed contracts under `isanlp_rst.contracts` and their envelope serializations | PASS | `isanlp_rst/contracts/__init__.py` exports 76 names including `RstAnalysis`, `RstDocument`, `SecondaryRelationEdge`, `DiscourseSignal`, plus the envelope serializations `to_dict`, `to_json`, `analysis_from_dict`, `analysis_from_json`, `document_from_dict`, `document_from_json`, `format_analysis_from_dict`, `format_analysis_from_json`. |
| 5 | `DiscourseUnit` / RS3 serialization, eRST RS4 and signals, rstviewer exports | PASS | `isanlp_rst/annotation_rst.py` `DiscourseUnit` has `to_rs3` and `clear_textfields`. `isanlp_rst/__init__.py:47` exports `RS4Document`, `RS4Reader`, `RS4Writer`, `ErstCapabilityError`; `DiscourseSignal` exported at `:24`. Viewer surface `render`, `to_html`, `to_png`, `to_pdf` all present (`isanlp_rst/__init__.py:121,135,162,193`). |
| 6 | CLI `isanlp-rst` entry point | PASS | `pyproject.toml:40-41` `[project.scripts]` `isanlp-rst = "isanlp_rst.cli:main"`; `isanlp_rst.cli.main` resolves. |
| 7 | Failure algebra and validation rules of all of the above | PASS | `isanlp_rst/ingest/contracts/failure.py` exports `ProductionFailure`, `ProductionIngestError`, `SafeProductionFailureRecord`, `DiagnosticProductionFailureRecord`, `DiagnosticPolicy`; `Retryability` resolves to exactly `retryable`, `not_retryable`, `unknown`, matching [../contracts/capability-declaration.md](../contracts/capability-declaration.md) §Retryability classification. |

**Unmatched in the other direction**: none. No currently supported public RST surface is
absent from the contract table. The audit compared the contract against
`isanlp_rst.__all__` (52 names), `isanlp_rst.contracts.__all__` (76 names),
`isanlp_rst.ingest.__all__` (178 names), `Parser`'s public attributes, and
`[project.scripts]`; every one falls under an existing row.

## Defects found and corrected (row 3)

Both were contract text asserting a surface the code does not have. Fixed forward in the
contract, per the project's fix-forward rule; no code changed.

1. **`analyse_source()` does not exist.** `grep -rl 'analyse_source' isanlp_rst tests scripts docs`
   returns exactly one hit — `docs/plans/2026-09-01-rst-performance-baseline.md` — and no
   Python file. At runtime, `hasattr(isanlp_rst.ingest, "analyse_source")` is `False`.
   The real convenience surface is `ProductionIngestor`'s three public methods:
   `capabilities()` (`isanlp_rst/ingest/service.py:147`), `prepare()` (`:150`), and
   `analyse()` (`:268`). The contract row and `CLAUDE.md`'s Active-roadmap paragraph both
   named the non-existent function; both are corrected.

2. **Six source forms are declared available, not five.** `SourceForm` has six members —
   `text`, `edus`, `markdown`, `docling_json`, `doclang_xml`, `doclang_archive` — and
   `describe_capabilities().semantic.source_forms` reports all six as
   `availability == "available"` with `preparation_supported == True`:

   | source_form | availability | required_extra | preparation_supported |
   |---|---|---|---|
   | `text` | available | — | true |
   | `edus` | available | — | true |
   | `markdown` | available | `formats` | true |
   | `docling_json` | available | `formats` | true |
   | `doclang_xml` | available | `formats` | true |
   | `doclang_archive` | available | `formats` | true |

   The "five" count omits `edus` (pre-segmented elementary discourse units). Because the
   migration's SC-002 equivalence procedure enumerates "all five source forms", the
   undercount would have silently excluded a supported, preparation-capable form from the
   baseline capture. Corrected to six in the contract and in `CLAUDE.md`.

## Equivalence-command verification (T003)

All commands run in this session, in the `default` pixi environment, on this machine.
Before the heavy suites were run, the FR-026 precondition was checked directly:
`ps aux` showed **no** training, workbench, or `modernbert` process — the task-636 run
was not live — so nothing competed for MPS.

| Command | Definition | Result |
|---|---|---|
| `pixi run test` | `pytest -m 'not slow and not stress' -q` | **GREEN** — `827 passed, 41 deselected in 28.24s` |
| `pixi run -e default production-boundary` | `python -m tools.production_boundary --root .` | **GREEN** — `"valid": true`, `"violations": []`, `production_modules: 92`, `scanned_files: 321` |
| `pixi run test-all` | `pyproject.toml:167` — `pytest -q` | **GREEN** — `868 passed in 114.99s` |
| `pixi run production-api-contract` | `pyproject.toml:192` — `pytest tests/ingest/production_ingest tests/production_boundary -q` | **GREEN** — `244 passed in 15.27s` |
| `pixi run smoke-full-mps` (as found) | `pyproject.toml:173` — `python scripts/smoke_test.py --full --device mps` | **FAIL** — `5 failure(s): load:gumrrg, load:rstdt, load:rstreebank, load:rrtrrg, load:unirst`. See defect 3 below. |
| `pixi run smoke` (after fix) | quick, CPU | **PASS** — 8 façade checks + 9 release checks on `modernbert-v1-a52b70fbc1a3` |
| `pixi run smoke-full-mps` (after fix) | full, MPS | **PASS** — both releases (`modernbert-v1-a52b70fbc1a3`, `modernbert-v1-e5ea56cd620f`) load on `mps`/`float32`; all 9 checks each |

The contract's equivalence procedure (§"Equivalence procedure", step 1) is therefore
**executed and green**: the pre-migration baseline commands all pass today.

**Command-form finding**: bare `pixi run production-boundary` fails with
`the task 'production-boundary' is ambiguous` — the task is defined in three environments
(`default`, `production`, `offline`; `pyproject.toml:113` and `:181`). The migration
feature's baseline capture must use the `-e` form. The same applies to `production-smoke`
(`pyproject.toml:114`, `:182`), which `CLAUDE.md` already documents as
`pixi run -e production production-smoke`.

### Defect 3 — the contract-named smoke could never pass (fixed in this pass)

`scripts/smoke_test.py` (last changed 2026-08-17, `3d7c982`) still loaded the five
legacy HF model versions (`gumrrg`, `rstdt`, `rstreebank`, `rrtrrg`, `unirst`) from
`tchewik/isanlp_rst_v3`. `isanlp_rst/parser.py:90-93` (changed 2026-09-01 in `511fb69`,
the Feature 005 completion commit) archives the DMRST and UniRST families from
production and raises `ValueError("Legacy … has been archived from production. Use
family='modernbert'")` before loading anything. Every one of the five loads therefore
failed deterministically — the script tested a surface production no longer has, and
Feature 005's completion did not re-run it. This is precisely the FR-027 hazard: a
completion marker on 005 with a broken contract-named gate behind it.

**Fix**: `scripts/smoke_test.py` rewritten to exercise the production family only —
discovering every ModernBERT release in `models/model-releases` and loading each via
the public `Parser.from_model_release(store, release_id, family="modernbert")` façade
(the same path `tools/production_boundary/installed_acceptance.py:196-202` already
uses). It now also asserts that the archived families are *refused* without loading,
that release identity matches the store, that `parse_document` output serializes
byte-equal after a round-trip (FR-011 serialized-contract compatibility), and that
`erst_graph` is either produced by a validated bundle or refused with
`ErstCapabilityError` — never fabricated. `scripts/cuda_smoke.py` had the identical
defect and received the same fix; `.claude/rules/commands.md`'s description of
`smoke-full` ("all five published models") was corrected with it.

**Known-stale, dormant, not fixed here**: `tools/production_boundary/parity.py` also
loads `gumrrg`/`unirst` (`:13-16`, `:73-77`). It runs only when `clean_install.py` is
given `--parity-baseline` (`clean_install.py:110-120`), which no pixi task passes
(`pyproject.toml:116`, `:196`), and it has no tests. It is dead on every current path and
would fail the same way if revived; regenerating its baseline JSON is a separate piece of
work for the migration feature's baseline capture, recorded here so it is not
rediscovered.

### Defect 4 — the published 5.0.0 artifact pair failed its own contract (rebuilt in this pass)

The preservation contract's equivalence procedure step 4 makes the packaging gate — wheel
built, clean-room install green — precede every other migration completion claim. Run
against the committed `dist/5.0.0` pair, the repo's own validator failed on its first
check:

```text
pixi run validate-production-artifacts
ValueError: wheel lacks required production contract resources: ['isanlp_rst/build-provenance.json']
```

Root cause, reconstructed from git and the artifacts' bytes:

| Fact | Evidence |
|---|---|
| The original pair was published reproducibly | `cc64f81` (2026-08-31) added both artifacts; the sdist's `build-provenance.json` names `source_commit: eb93565`, `build 1.6.0` |
| The wheel was then replaced **alone**, ad hoc | `511fb69` (2026-09-01, "complete Feature 005 … operational certification") changed only the wheel (`492368 -> 491997` bytes). Its members match the `511fb69` tree 6/6 on sampled files; every zip entry carries hatchling's default `2020-02-02` timestamp; no provenance file. That is a plain hatchling build, not `tools/production_boundary/build.py`, which writes provenance (`build.py:233`), sets `SOURCE_DATE_EPOCH` to the commit time, double-builds for reproducibility, and refuses to overwrite (`:184`, `:199`). |
| The pair was split | sdist from `eb93565`, wheel from `511fb69` — `artifacts.py:141` rejects mismatched provenance |
| Both were stale | six commits after `511fb69` changed 11 package files (`cli.py`, `ingest/service.py`, `parser_result.py`, `subdivision.py`, both failure schemas, …); wheel 11 files behind HEAD, sdist 15 |
| No source-release evidence ever existed | `build-production` writes `specs/004-production-api-contract/evidence/source-release.json`; `git log --all` for that path is empty |
| The gate was not re-run | `511fb69`'s message claims *"Certified clean-room wheel installation"*; `production-smoke` never checks provenance, so it passed against a wheel the artifact contract rejects |

**Fix (owner-authorised 2026-09-02, a release action outside 006's scope)**: the pair was
retired in `3613f53`, then rebuilt by `pixi run build-production` from that clean commit
— double build, `"reproducible": true`, provenance `source_commit: 3613f53` in both
artifacts, `source-release.json` written for the first time. `validate-production-artifacts`
now reports `valid: true`, RECORD verified, zero forbidden members, matching provenance.
`pixi run -e production production-smoke` is green (note: that task exercises the
*editable source* in the production environment — 13 distribution members — not the
wheel; the wheel is certified by `production-clean-install`, recorded below).

`pixi run -e production production-clean-install` — the actual wheel certification:
pip-installs the rebuilt wheel into two fresh venvs and runs
`installed_acceptance.py --full` outside the source tree with the network disabled —
**`valid: true`**:

| Venv | `pip check` | Source forms available | Analysis on `modernbert-v1-e5ea56cd620f` | CLI ≡ Python |
|---|---|---|---|---|
| `core` | passed | `text`, `edus` (four format forms correctly `unavailable`, and an unavailable Markdown prepare yields a typed safe failure) | 4 loaded components, 7 validation checks passed | semantic digests equal |
| `formats` | passed | all six `available`, all six prepared with canonical round-trip | 4 loaded components, 7 validation checks passed | semantic digests equal |

Both venvs: `package_version 5.0.0`, `network_disabled`, offline distributions absent,
202 public-surface entries resolved, package imported from `site-packages`, not the
source tree.

This is the third FR-027 finding against Feature 005's completion in one audit pass,
after the fabricated evaluation literal (promotion-gap-audit gap 4) and the smoke script
that could not pass (defect 3).

**Follow-up (2026-09-02, owner-directed)**: the class of defect was removed rather than
patched. `dist/` is now ignored build output; a release is a commit tagged `v<version>`,
`build-production` rebuilds the pair from it (refusing a tag that names another
version, recording the tag in the packaged provenance and in the committed
`reproducible-build.json`), and the smoke scripts moved into
`tests/integration/test_production_smoke.py` so `test-all` runs them. `production-smoke`
was renamed `production-import-check` because it imports the editable source and
certifies no wheel. The 004 distribution contract's never-executed two-machine
sequence is marked superseded; `AGENTS.md` §"no invented release theatre" is the
authority.

**Release evidence observation**: the promoted release
`modernbert-v1-e5ea56cd620f` carries `"evaluation_evidence": "GUM-12.1.0 Parseval
evaluation verified"` — the fabricated fallback literal documented in
[promotion-gap-audit.md](promotion-gap-audit.md) gap 4, now removed from the promotion
code. `modernbert-v1-a52b70fbc1a3` carries a genuine training receipt (run
`20260831_072635_ModernBERT_base_9b5df5`, `test_full_f1: 0.198`).

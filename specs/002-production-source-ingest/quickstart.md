# Quickstart: Production Source Ingest

> **Planning contract**: These commands and APIs describe the completed Feature
> 002 target. They become executable acceptance evidence only after the tasks are
> generated and implemented. Their presence here is not a claim that the current
> code already supports them.

## 1. Build and prove the production package

From the repository root:

```bash
pixi run -e offline build-production
pixi run -e production production-boundary
pixi run -e offline production-ingest-conformance
pixi run -e offline production-ingest-clean-install
```

Target evidence:

- the production wheel builds reproducibly;
- production boundary checks reject reverse imports and non-production payload;
- current Docling and DocLang normative fixtures pass unmodified;
- a clean temporary environment installs the wheel and runs every production
  source family without the repository on `sys.path` or network access.

## 2. Analyse one real source

```python
from pathlib import Path

from isanlp_rst import Parser
from isanlp_rst.ingest import (
    AUTHORED_PROSE_V1,
    ProductionIngestor,
    SourceArtifact,
)


artifact = SourceArtifact.from_path(
    Path("/absolute/path/to/source.md"),
    original_source="local:source.md",
)
parser = Parser.from_release(Path("/absolute/path/to/released-model"))
result = ProductionIngestor(parser=parser).analyse(
    artifact,
    policy=AUTHORED_PROSE_V1,
    cache_dir=Path("/absolute/path/to/local-cache"),
)

Path("result.json").write_text(
    result.model_dump_json(indent=2),
    encoding="utf-8",
)
```

Inspect the result before using the tree:

```python
assert result.receipt.inventory_coverage == 1.0
assert result.receipt.primary_source_coverage == 1.0
assert result.receipt.prepared_text_coverage == 1.0
assert result.receipt.analysis_anchor_coverage == 1.0
```

For an input with no eligible authored discourse,
`result.analysis_status == "empty_primary_discourse"`; the inventory and
dispositions remain complete and no artificial tree is produced.

## 3. Construct explicit plain-text and EDU artifacts

```python
text_artifact = SourceArtifact.from_text(
    "A short discourse. Therefore, it can be analysed.",
    source_name="example.txt",
)

edu_artifact = SourceArtifact.from_edus(
    ["A short discourse.", "Therefore, it can be analysed."],
    source_name="example.edus",
)
```

JSON, ambiguous XML/text, extensionless, and byte sources require an explicit
`SourceForm`; the API will not guess through ambiguity.

## 4. Public-surface checks

The public-surface suite proves that `isanlp_rst.ingest` is the sole source
ingest route and that obsolete format entry points, envelopes, and caches are
absent from the installed package:

```bash
pixi run -e offline production-ingest-public-api
```

The production default is the named `authored_prose_v1` policy.

## 5. Freeze and run the Gold Set

Gold content remains outside the repository. The operator supplies absolute
local paths explicitly:

```bash
pixi run -e offline production-ingest-freeze -- \
  --gold-root "/absolute/private/path/to/gold" \
  --manifest specs/002-production-source-ingest/evidence/gold-manifest.json \
  --model-root "/absolute/path/to/released-model" \
  --output "/absolute/path/to/frozen-run"
```

Run baseline and candidate with identical frozen inputs and model bytes:

```bash
pixi run -e offline production-ingest-candidate -- \
  --freeze "/absolute/path/to/frozen-run/freeze.json" \
  --baseline-wheel "/absolute/path/to/baseline.whl" \
  --candidate-wheel "/absolute/path/to/candidate.whl" \
  --output "/absolute/path/to/candidate-evidence"
```

The runner creates isolated production environments and serializes results. The
repository-only assessor then scores those frozen outputs:

```bash
pixi run -e offline production-ingest-assess -- \
  --freeze "/absolute/path/to/frozen-run/freeze.json" \
  --candidate-evidence "/absolute/path/to/candidate-evidence" \
  --report specs/002-production-source-ingest/evidence/promotion-report.json
```

The assessor reports every source before aggregates and fails on the first
ordered gate family while still recording all safely measurable evidence. It
never changes production results or benchmark expectations.

## 6. Final acceptance sequence

```bash
pixi run -e offline production-ingest-test
pixi run -e offline production-ingest-conformance
pixi run -e offline production-ingest-determinism
pixi run -e offline production-ingest-performance
pixi run -e offline production-ingest-clean-install
pixi run -e production production-boundary
pixi run -e offline lint
pixi run -e offline typecheck
```

Feature 002 is complete only when:

- all commands above have been run and their actual outputs retained;
- the frozen 20-or-more-source Gold Set passes every per-source gate;
- all four coverage measures are 100%;
- all protected RST metrics are non-regressing for every source form;
- structure-boundary violations improve by at least 50%;
- determinism, corruption, cache invalidation, million-character, and clean-wheel
  proofs pass;
- direct inspection records exist for every source;
- the dated SOTA comparison is accurate and bounded;
- no production module or wheel payload contains or imports training,
  development, Gold Set, benchmark, or evaluation harness code.

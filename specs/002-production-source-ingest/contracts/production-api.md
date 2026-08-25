# Contract: Production Ingest API

**Public package**: `isanlp_rst.ingest`

**Result schema**: `isanlp_rst_ingest` version 1

## Public surface

The canonical API accepts a fully materialized `SourceArtifact`. Convenience
constructors perform source reading and identification before analysis; the
analysis service does not reinterpret an artifact later.

```python
from collections.abc import Sequence
from pathlib import Path

from isanlp_rst import Parser
from isanlp_rst.ingest import (
    AUTHORED_PROSE_V1,
    PreparationPolicy,
    ProductionAnalysisResult,
    ProductionIngestor,
    SourceArtifact,
    SourceForm,
)


artifact = SourceArtifact.from_path(
    Path("report.dclg"),
    source_form=SourceForm.DOCLANG_XML,  # optional only when unambiguous
    original_source="local:report.dclg",
)

ingestor = ProductionIngestor(parser=Parser.from_release(Path("model")))
result: ProductionAnalysisResult = ingestor.analyse(
    artifact,
    policy=AUTHORED_PROSE_V1,
    cache_dir=Path(".cache/isanlp-rst/ingest"),
)
```

The implemented constructors are:

```python
SourceArtifact.from_text(
    text: str,
    *,
    source_name: str,
    original_source: str | None = None,
    conversion_provenance: Sequence[ConversionActivity] = (),
) -> SourceArtifact

SourceArtifact.from_edus(
    edus: Sequence[str],
    *,
    source_name: str,
    original_source: str | None = None,
    conversion_provenance: Sequence[ConversionActivity] = (),
) -> SourceArtifact

SourceArtifact.from_path(
    path: Path,
    *,
    source_form: SourceForm | None = None,
    original_source: str | None = None,
    conversion_provenance: Sequence[ConversionActivity] = (),
) -> SourceArtifact

SourceArtifact.from_bytes(
    data: bytes,
    *,
    source_form: SourceForm,
    source_name: str,
    media_type: str,
    original_source: str | None = None,
    conversion_provenance: Sequence[ConversionActivity] = (),
) -> SourceArtifact
```

`from_path` may infer only unambiguous, documented forms: `.md`/`.markdown`,
Docling `.json` after contract identification, `.dclg`/`.dclg.xml`, and `.dclx`.
Ambiguous `.txt`, XML, JSON, extensionless, or byte inputs require an explicit
form. Identification never substitutes for validation.

## Service contract

```python
class ProductionIngestor:
    def __init__(self, *, parser: Parser) -> None: ...

    def prepare(
        self,
        artifact: SourceArtifact,
        *,
        policy: PreparationPolicy = AUTHORED_PROSE_V1,
    ) -> PreparedRstDocument: ...

    def analyse(
        self,
        artifact: SourceArtifact,
        *,
        policy: PreparationPolicy = AUTHORED_PROSE_V1,
        cache_dir: Path | None = None,
    ) -> ProductionAnalysisResult: ...
```

`prepare` executes current source validation, full inventory, policy,
transformation, structure/subdivision planning, and coverage verification. It
does not run the RST parser or write the durable analysis cache.

`analyse` performs the same preparation, computes the complete analytical cache
identity, verifies any cache hit, runs recursive local/macro parsing when
needed, constructs source anchors, verifies the final result, and persists only
a fully valid result.

## Parser capability and model identity

The parser must expose an immutable release identity containing:

- production package and parser implementation versions;
- model manifest digest and digests of every loaded model file;
- tokenizer/segmenter identity;
- relation inventory and eRST mode;
- safe unit capacity expressed in the parser's actual limiting unit.

An injected parser without this identity may analyse in the current process,
but durable caching is disabled and explicitly receipted. Python object identity
is never a model identity.

## Single public ingest surface

`isanlp_rst.ingest` is the only public source-ingest API. The obsolete
`parse_markdown`, `parse_docling`, and `parse_doclang` functions, their result
envelopes, and their independent caches are removed rather than deprecated.
There is no compatibility window and no second ingest path.

Format-specific helpers may exist only as private implementation details used
by `ProductionIngestor`. They do not expose an alternative policy, result
contract, cache, or orchestration route.

## Serialization

`ProductionAnalysisResult.model_dump_json()` emits strict UTF-8 JSON with:

- `schema_name: "isanlp_rst_ingest"`;
- `schema_version: "1.0.0"`;
- explicit null/absence semantics defined by the Pydantic contract;
- canonical semantic subobjects for hashing;
- a separate non-semantic execution receipt.

Deserialization verifies schema compatibility, semantic digest, cache
fingerprint, and payload integrity before returning a result.

## Failure behavior

Failures are typed by `FailureStage` and stable code. Required examples include:

- ambiguous or unsupported source form;
- invalid UTF-8 or malformed source contract;
- current Docling/DocLang validation failure;
- unsafe DocLang archive member;
- unresolved native reference or unreconciled inventory item;
- policy contradiction or unsupported required transformation;
- source/prepared/anchor coverage failure;
- parser capacity contract missing or violated;
- corrupt or identity-contradictory cache entry;
- incomplete local/macro tree or unanchored analysis node.

Messages identify the artifact and failing item/expectation without embedding
private source text unnecessarily. They preserve diagnostic evidence from every
completed stage, including warnings and reconciled counts when available,
without presenting it as a successful result. There is no partial-success
return, silent skip, best-effort tree, or reusable cache write after failure.

## Runtime boundary

The installed production wheel:

- imports no `offline_workbench`, Gold Set, training, corpus, scoring, benchmark,
  or repository tooling module;
- requires no network access and performs no asset retrieval;
- reads only caller-submitted sources, released model files, optional local
  cache entries, and installed package metadata;
- contains no private Gold Set source or labels;
- produces serialized outputs that repository-only promotion tooling may score
  later through the one-way offline-to-production dependency.

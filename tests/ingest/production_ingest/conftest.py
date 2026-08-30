"""Deterministic builders shared by the production-ingest contract tests."""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
import hashlib
from pathlib import Path, PurePosixPath
import re
from types import SimpleNamespace

import pytest

from isanlp_rst.annotation_rst import DiscourseUnit
from isanlp_rst.contracts import (
    DocumentToken,
    Edu,
    NodeKindEnum,
    NuclearityPatternEnum,
    OutputFormalismEnum,
    ProvenanceRecord,
    RstAnalysis,
    RstDocument,
    RstNode,
    PrimaryRelationEdge,
    TextSpan,
)
from isanlp_rst.ingest.contracts import (
    AnalysisPolicy,
    CompositeAnalysisIdentity,
    ParserAnalysisResult,
    ParserCapacity,
    OutputFormalism,
    SemanticVersion,
    SourceArtifact,
    SourceForm,
)
from isanlp_rst.ingest.contracts.preparation import CapacityUnit
from isanlp_rst.ingest.parser_result import (
    build_parser_analysis_result,
    describe_analysis_components,
)
from isanlp_rst.ingest.service import DEFAULT_ANALYSIS_POLICY
from isanlp_rst.model_loading import ModelFile, ModelReleaseIdentity
from isanlp_rst.model_loading import ParserCapacity as ReleaseParserCapacity
from isanlp_rst.transformer_parser.predictor import PredictorAnalysisTrace
from isanlp_rst.transformer_parser.biaffine_decoder import (
    ParsedRstTreeEvidence,
    ParsedRstTreeSpan,
)

type SourceArtifactBuilder = Callable[..., SourceArtifact]
type ParserBuilder = Callable[..., "DeterministicParser"]
type ModelIdentityBuilder = Callable[..., ModelReleaseIdentity]
type CacheDirectoryBuilder = Callable[[str], Path]
type PrivateMarkerBuilder = Callable[[str], "PrivateMarker"]


@dataclass(frozen=True, slots=True)
class PrivateMarker:
    """A recognisable private value and the digest safe for public diagnostics."""

    value: str
    sha256: str


@dataclass(frozen=True, slots=True)
class DeterministicParser:
    """Small immutable parser double with stable capacity and model identity."""

    analysis_capacity: ParserCapacity
    model_release_identity: ModelReleaseIdentity

    @property
    def predictor(self) -> SimpleNamespace:
        return SimpleNamespace(
            _device="cpu",
            model=SimpleNamespace(raw_relation_inventory=("same-unit",)),
            loaded_release_files=self.model_release_identity.files,
        )

    @property
    def erst_checkpoint(self) -> None:
        return None

    def analyse_document(
        self,
        document: RstDocument,
        *,
        analysis_policy: AnalysisPolicy | None = None,
    ) -> ParserAnalysisResult:
        edus = document.edus or _sentence_edus(document.text)
        tokens = tuple(
            DocumentToken(
                token_id=index,
                text=match.group(0),
                start=match.start(),
                end=match.end(),
                sentence_id=_sentence_membership(match.start(), match.end(), edus),
                paragraph_id=0,
            )
            for index, match in enumerate(re.finditer(r"\S+", document.text))
        )
        edus = tuple(
            Edu(
                edu_id=edu.edu_id,
                text=edu.text,
                start=edu.start,
                end=edu.end,
                token_ids=tuple(
                    token.token_id for token in tokens if edu.start <= token.start and token.end <= edu.end
                ),
            )
            for edu in edus
        )
        root = DiscourseUnit(
            id=1,
            text=document.text,
            relation="same-unit",
            nuclearity="N",
            start=0,
            end=len(document.text),
        )
        nodes, edges, decisions = _fixture_tree(document.text, edus)
        analysis = RstAnalysis(
            document_id=document.document_id,
            formalism=OutputFormalismEnum.RST_TREE,
            nodes=nodes,
            primary_edges=edges,
            provenance=ProvenanceRecord(
                producer="deterministic-test-parser",
                software_version="5.0.0",
                source_revision="0" * 40,
                timestamp="2026-01-01T00:00:00+00:00",
            ),
        )
        trace = PredictorAnalysisTrace(
            root_unit=root,
            analysis=analysis,
            tokens=tokens,
            edus=edus,
            sentence_boundaries=tuple(TextSpan(start=edu.start, end=edu.end, text=edu.text) for edu in edus),
            paragraph_boundaries=(TextSpan(start=0, end=len(document.text), text=document.text),),
            structure_decisions=decisions,
            segmentation_source=("presegmented" if document.edus is not None else "deterministic_sentence_boundary_v1"),
            relation_inventory=("same-unit",),
        )
        return build_parser_analysis_result(
            self,
            document,
            trace,
            policy=analysis_policy or DEFAULT_ANALYSIS_POLICY,
            model_analysis=analysis,
            final_analysis=analysis,
            erst_trace=None,
            duration_ms=0.0,
        )

    def parse_document(
        self,
        document: RstDocument,
        output: str = "rst_tree",
    ) -> RstAnalysis:
        policy = AnalysisPolicy.model_validate(
            {
                **DEFAULT_ANALYSIS_POLICY.model_dump(exclude={"semantic_digest"}),
                "output_formalism": OutputFormalism(output),
            }
        )
        return self.analyse_document(document, analysis_policy=policy).analysis

    def describe_analysis_identity(
        self,
        *,
        analysis_policy: AnalysisPolicy,
        segmentation_source: str,
    ) -> CompositeAnalysisIdentity:
        composite, _ = describe_analysis_components(
            self,
            segmentation_source=segmentation_source,
            policy=analysis_policy,
        )
        return composite


@pytest.fixture
def source_artifact_builder() -> SourceArtifactBuilder:
    """Build exact, stable sources without filesystem or clock dependence."""

    def build(
        payload: str | bytes | Sequence[str] = "First sentence. Second sentence.",
        *,
        source_form: SourceForm = SourceForm.TEXT,
        source_name: str = "fixture.txt",
        media_type: str = "text/plain",
    ) -> SourceArtifact:
        if isinstance(payload, bytes):
            return SourceArtifact.from_bytes(
                payload,
                source_form=source_form,
                source_name=source_name,
                media_type=media_type,
            )
        if isinstance(payload, str):
            if source_form is not SourceForm.TEXT:
                return SourceArtifact.from_bytes(
                    payload.encode("utf-8"),
                    source_form=source_form,
                    source_name=source_name,
                    media_type=media_type,
                )
            return SourceArtifact.from_text(payload, source_name=source_name)
        return SourceArtifact.from_edus(tuple(payload), source_name=source_name)

    return build


@pytest.fixture
def model_identity_builder() -> ModelIdentityBuilder:
    """Build a complete immutable identity whose digests never depend on the host."""

    def build(
        *,
        release_id: str = "fixture-release",
        maximum: int = 512,
        manifest_sha256: str = "a" * 64,
        weight_sha256: str = "b" * 64,
    ) -> ModelReleaseIdentity:
        capacity = ReleaseParserCapacity(unit="edu_count", maximum=maximum, source="fixture-parser-v1")
        return ModelReleaseIdentity(
            release_id=release_id,
            manifest_sha256=manifest_sha256,
            runtime_contract="isanlp_rst.parser/fixture-v1",
            architecture="deterministic-fixture",
            files=(
                ModelFile(
                    path=PurePosixPath("model.safetensors"),
                    role="weights",
                    size_bytes=1,
                    sha256=weight_sha256,
                ),
                ModelFile(
                    path=PurePosixPath("relation_inventory.json"),
                    role="relation_inventory",
                    size_bytes=1,
                    sha256="c" * 64,
                ),
            ),
            capacity=capacity,
        )

    return build


@pytest.fixture
def parser_builder(model_identity_builder: ModelIdentityBuilder) -> ParserBuilder:
    """Build a parser double aligned with the requested immutable model identity."""

    def build(
        *,
        release_id: str = "fixture-release",
        maximum: int = 512,
    ) -> DeterministicParser:
        identity = model_identity_builder(release_id=release_id, maximum=maximum)
        return DeterministicParser(
            analysis_capacity=ParserCapacity(
                unit=CapacityUnit.EDU_COUNT,
                maximum=identity.capacity.maximum,
                estimation_algorithm="provider_declared",
                estimation_version=SemanticVersion(root="2.0.0"),
                source=identity.capacity.source,
            ),
            model_release_identity=identity,
        )

    return build


@pytest.fixture
def cache_directory_builder(tmp_path: Path) -> CacheDirectoryBuilder:
    """Create named, isolated cache roots under pytest's managed temporary tree."""

    def build(name: str = "cache") -> Path:
        path = tmp_path / name
        path.mkdir(parents=True, exist_ok=False)
        return path

    return build


@pytest.fixture
def private_marker_builder() -> PrivateMarkerBuilder:
    """Build private sentinels for public-error and persistence leak checks."""

    def build(label: str = "source") -> PrivateMarker:
        value = f"PRIVATE-F004-{label}-7fbd62f4"
        return PrivateMarker(
            value=value,
            sha256=hashlib.sha256(value.encode("utf-8")).hexdigest(),
        )

    return build


def _sentence_edus(text: str) -> tuple[Edu, ...]:
    starts = [0]
    starts.extend(match.end() for match in re.finditer(r"(?<=[.!?])\s+|\n+", text))
    starts.append(len(text))
    result: list[Edu] = []
    for start, end in zip(starts, starts[1:], strict=False):
        raw = text[start:end]
        if not raw.strip():
            continue
        leading = len(raw) - len(raw.lstrip())
        trailing = len(raw) - len(raw.rstrip())
        exact_start = start + leading
        exact_end = end - trailing
        result.append(
            Edu(
                edu_id=len(result) + 1,
                text=text[exact_start:exact_end],
                start=exact_start,
                end=exact_end,
            )
        )
    return tuple(result)


def _sentence_membership(start: int, end: int, edus: tuple[Edu, ...]) -> int:
    for index, edu in enumerate(edus):
        if edu.start <= start and end <= edu.end:
            return index
    raise ValueError("fixture token is outside exact EDU boundaries")


def _fixture_tree(
    text: str,
    edus: tuple[Edu, ...],
) -> tuple[
    tuple[RstNode, ...],
    tuple[PrimaryRelationEdge, ...],
    tuple[ParsedRstTreeEvidence, ...],
]:
    nodes: list[RstNode] = [
        RstNode(
            node_id=edu.edu_id,
            kind=NodeKindEnum.EDU,
            edu_span=(edu.edu_id, edu.edu_id),
            char_span=(edu.start, edu.end),
            text=edu.text,
        )
        for edu in edus
    ]
    edges: list[PrimaryRelationEdge] = []
    decisions: list[ParsedRstTreeEvidence] = []
    next_node_id = len(edus) + 1

    def build(start: int, end: int) -> int:
        nonlocal next_node_id
        if start == end:
            return start + 1
        node_id = next_node_id
        next_node_id += 1
        split = (start + end) // 2
        split_candidates = tuple(range(start, end))
        decisions.append(
            ParsedRstTreeEvidence(
                span=ParsedRstTreeSpan(
                    start=start,
                    end=end,
                    split=split,
                    nuclearity="NN",
                    relation="same-unit",
                    score=1.0,
                ),
                split_candidates=split_candidates,
                split_logits=tuple(1.0 if value == split else 0.0 for value in split_candidates),
                nuclearity_logits=(0.0, 0.0, 1.0),
                relation_logits=(1.0,),
            )
        )
        left_id = build(start, split)
        right_id = build(split + 1, end)
        nodes.append(
            RstNode(
                node_id=node_id,
                kind=NodeKindEnum.MULTINUCLEAR_GROUP,
                edu_span=(start + 1, end + 1),
                char_span=(edus[start].start, edus[end].end),
                text=text[edus[start].start : edus[end].end],
            )
        )
        for child_id in (left_id, right_id):
            edges.append(
                PrimaryRelationEdge(
                    edge_id=f"e_{node_id}_{child_id}",
                    parent_id=node_id,
                    child_id=child_id,
                    relation_raw="same-unit",
                    relation_concept="same-unit",
                    nuclearity=NuclearityPatternEnum.NN,
                    confidence=1.0,
                    calibrated=False,
                )
            )
        return node_id

    build(0, len(edus) - 1)
    return tuple(nodes), tuple(edges), tuple(decisions)

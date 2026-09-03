"""Regression tests for the production Python 3.14 audit's P1 findings."""

from collections.abc import Mapping, MutableMapping
import math
import os
from pathlib import Path
from typing import Any, cast

import networkx as nx
from pydantic import SecretStr
import pytest
import torch
from torch import Tensor, nn

from rdam import Machine, Technique
from rdam.rst.contracts import (
    FormatRstAnalysis,
    NodeKindEnum,
    NuclearityPatternEnum,
    OutputFormalismEnum,
    PrimaryRelationEdge,
    RstAnalysis,
    RstDocument,
    RstNode,
    SecondaryRelationEdge,
)
from rdam.rst.annotation_rst import DiscourseUnit, Exporter
from rdam.rst.dmrst_parser.src.parser.metrics import get_batch_metrics as dmrst_batch_metrics
from rdam.rst.dmrst_parser.src.parser.metrics import get_micro_metrics as dmrst_micro_metrics
from rdam.rst.dmrst_parser.src.parser.parsing_net import ParsingNet as DmrstParsingNet
from rdam.rst.dmrst_parser.src.parser.segmenters import ToNySegmenter as DmrstSegmenter
from rdam.rst.erst.candidates import RelationCompatibilityProfile
from rdam.rst.erst.checkpoint import resolve_default_erst_checkpoint
from rdam.rst.erst.environment import load_repository_environment
from rdam.rst.erst.rs4 import RS4Document
from rdam.rst.graph import to_networkx_graph
from rdam.rst.ingest.public_surface import _documentation_anchor_exists
from rdam.rst.ontology.loader import OntologyLockData
from rdam.rst.rstviewer.main import Rs3ImportError, rs3tohtml
from rdam.rst.universal_parser.src.parser.metrics import get_batch_metrics as unirst_batch_metrics
from rdam.rst.universal_parser.src.parser.metrics import get_micro_metrics as unirst_micro_metrics
from rdam.rst.universal_parser.src.parser.modules import EncoderRNN as UniEncoderRNN
from rdam.rst.universal_parser.src.parser.parsing_net import ParsingNet as UniParsingNet
from rdam.rst.universal_parser.src.parser.segmenters import ToNySegmenter as UniSegmenter
from rdam.rst.utils.serialization import tree_from_dict, tree_to_dict
from rdam.rst.utils.serialization_pydantic import PydanticDiscourseUnit
from rdam.sdrt.graph import (
    ComplexDiscourseUnit,
    ElementaryDiscourseUnit,
    RelationStructure,
    SdrtAnalysis,
    SdrtRelation,
)
from tests.machine.conftest import FakeProvider, echo_result, rst_declaration


def _minimal_analysis() -> RstAnalysis:
    return RstAnalysis(
        document_id="audit",
        formalism=OutputFormalismEnum.ERST_GRAPH,
        nodes=(
            RstNode(1, NodeKindEnum.EDU, (1, 1), (0, 1), "a"),
            RstNode(2, NodeKindEnum.EDU, (2, 2), (2, 3), "b"),
        ),
        primary_edges=(
            PrimaryRelationEdge(
                edge_id="primary",
                parent_id=1,
                child_id=2,
                relation_raw="span",
                relation_concept="Span",
                nuclearity=NuclearityPatternEnum.NN,
            ),
        ),
        secondary_edges=(
            SecondaryRelationEdge(
                edge_id="secondary-1",
                source_id=1,
                target_id=2,
                relation_raw="explanation",
                relation_concept="Explanation",
            ),
            SecondaryRelationEdge(
                edge_id="secondary-2",
                source_id=1,
                target_id=2,
                relation_raw="contrast",
                relation_concept="Contrast",
            ),
        ),
    )


def _dmrst_net(*, classifier_bias: bool = True, segmenter_type: str = "linear") -> DmrstParsingNet:
    return DmrstParsingNet(
        relation_table=["span_NN"],
        transformer=nn.Identity(),
        emb_dim=4,
        hidden_size=4,
        decoder_input_size=4,
        segmenter_type=segmenter_type,
        encoder_document_enc_gru=False,
        encoder_add_first_and_last=False,
        classifier_input_size=4,
        classifier_hidden_size=4,
        classes_number=2,
        classifier_bias=classifier_bias,
        atten_model="Dotproduct",
        token_bilstm_hidden=2,
        cuda_device=torch.device("cpu"),
    )


def _unirst_net(*, classifier_bias: bool = True) -> UniParsingNet:
    return UniParsingNet(
        relation_tables=[["span_NN"]],
        transformer=nn.Identity(),
        emb_dim=4,
        hidden_size=4,
        decoder_input_size=4,
        segmenter_type="linear",
        encoder_document_enc_gru=False,
        encoder_add_first_and_last=False,
        classifier_input_size=4,
        classifier_hidden_size=4,
        classes_numbers=[2],
        classifier_bias=classifier_bias,
        atten_model="Dotproduct",
        token_bilstm_hidden=2,
        cuda_device=torch.device("cpu"),
        separated_segmentation=False,
    )


def test_missing_or_unknown_documentation_anchor_fails_closed() -> None:
    assert not _documentation_anchor_exists("not-a-real-production-api-heading")


def test_default_erst_checkpoint_resolution_is_independent_of_cwd(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ISANLP_RST_ERST_CHECKPOINT", raising=False)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path / "home"))
    first = tmp_path / "first"
    second = tmp_path / "second"
    (first / "models" / "erst_scorer_bundle").mkdir(parents=True)
    (first / "models" / "erst_scorer_bundle" / "manifest.json").write_text("{}", encoding="utf-8")
    second.mkdir()

    monkeypatch.chdir(first)
    from_first = resolve_default_erst_checkpoint()
    monkeypatch.chdir(second)
    from_second = resolve_default_erst_checkpoint()

    assert from_first == from_second


def test_default_repository_environment_uses_stable_user_config_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("RDAM_CONFIG_HOME", raising=False)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path / "home"))

    receipt = load_repository_environment()

    assert receipt.repository_root == (tmp_path / "home" / ".config" / "rdam").resolve()


@pytest.mark.parametrize("segmenter_type", (DmrstSegmenter, UniSegmenter))
def test_sentence_boundaries_change_original_logits(segmenter_type: type[nn.Module]) -> None:
    segmenter: Any = segmenter_type(
        embedding_dim=4,
        use_sentence_boundaries=True,
        use_lstm=False,
        cuda_device=torch.device("cpu"),
    )
    nn.init.zeros_(segmenter.hidden2tag.weight)
    nn.init.zeros_(segmenter.hidden2tag.bias)

    log_probabilities = segmenter(torch.zeros(3, 4), [1])

    assert log_probabilities[1, 0] < -100
    torch.testing.assert_close(log_probabilities[[0, 2]], torch.full((2, 2), -math.log(2.0)))


@pytest.mark.parametrize("batch_metrics", (dmrst_batch_metrics, unirst_batch_metrics))
def test_gold_only_document_keeps_its_per_document_denominator(batch_metrics: Any) -> None:
    gold = "(1:Nucleus=span:1,2:Satellite=elaboration:2)"
    result = batch_metrics([["NONE"]], [gold], [[1]], [[0, 1]], True)

    assert result[5] == 1
    assert result[11] == [1]


@pytest.mark.parametrize("micro_metrics", (dmrst_micro_metrics, unirst_micro_metrics))
def test_empty_metrics_are_defined(micro_metrics: Any) -> None:
    result = micro_metrics(0, 0, 0, 0, 0, 0, 0, 0, 0)
    assert result == ((0.0, 0.0, 0.0),) * 3 + (0.0, (0.0, 0.0, 0.0))


@pytest.mark.parametrize("net_type", (DmrstParsingNet, UniParsingNet))
def test_bert_du_encoding_stops_at_requested_right_boundary(net_type: type[nn.Module]) -> None:
    net: Any = object.__new__(net_type)
    object.__setattr__(net, "rel_classification_kind", "bimpm")
    embeddings = torch.arange(20, dtype=torch.float32).reshape(10, 2)

    left, right = net._encode_du_bert(
        list(range(10)),
        [1, 3, 5, 7, 9],
        left_boundary=1,
        du_break=2,
        right_boundary=3,
        embeddings=embeddings,
    )

    torch.testing.assert_close(left, embeddings[2:6].unsqueeze(0))
    torch.testing.assert_close(right, embeddings[6:8].unsqueeze(0))


class _RecordingTransformer(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.calls: list[Mapping[str, Tensor | None]] = []

    def forward(
        self,
        token_ids: Tensor,
        *,
        entity_ids: Tensor | None = None,
        entity_position_ids: Tensor | None = None,
    ) -> tuple[Tensor]:
        self.calls.append(
            {
                "entity_ids": entity_ids,
                "entity_position_ids": entity_position_ids,
            }
        )
        return (torch.zeros((*token_ids.shape, 4), dtype=torch.float32),)


def test_unirst_final_window_keeps_entity_inputs() -> None:
    transformer = _RecordingTransformer()
    encoder = UniEncoderRNN(
        transformer=transformer,
        word_dim=4,
        hidden_size=4,
        rnn_layers=1,
        dropout=0.0,
        normalize_embeddings=False,
        segmenters=nn.ModuleList(),
        edu_encoding_kind="avg",
        document_enc_gru=False,
        add_first_and_last=False,
        edu_embedding_compression_rate=1.0,
        window_size=200,
        window_padding=10,
        token_bilstm_hidden=0,
        cuda_device=torch.device("cpu"),
    )
    token_ids = torch.arange(520)
    entity_ids = torch.tensor([10, 11, 12])
    entity_positions = torch.tensor([[50, -1], [250, -1], [500, -1]])

    encoder._fixed_sliding_window(token_ids, entity_ids, entity_positions)

    assert len(transformer.calls) == 3
    assert all(call["entity_ids"] is not None for call in transformer.calls)
    final_positions = transformer.calls[-1]["entity_position_ids"]
    assert final_positions is not None
    assert 120 in final_positions


def test_classifier_bias_controls_bilateral_parameters() -> None:
    dmrst = _dmrst_net(classifier_bias=False)
    unirst = _unirst_net(classifier_bias=False)

    assert cast(nn.Linear, dmrst.label_classifier.weight_bilateral).bias is None
    assert cast(nn.Linear, unirst.label_classifiers[0].weight_bilateral).bias is None


def test_dmrst_pointer_segmenter_is_constructible() -> None:
    net = _dmrst_net(segmenter_type="pointer")
    predicted = net.segmenter.test_segment_loss(torch.randn(4, 4), [3])
    assert predicted[-1] == 3


def test_networkx_export_preserves_parallel_relations() -> None:
    graph = to_networkx_graph(_minimal_analysis(), RstDocument(document_id="audit", text="a b"))

    assert isinstance(graph, nx.MultiDiGraph)
    assert set(graph[1][2]) == {"primary", "secondary-1", "secondary-2"}


def test_viewer_raises_the_rs3_import_failure(tmp_path: Path) -> None:
    malformed = tmp_path / "malformed.rs3"
    malformed.write_text("<rst><body /></rst>", encoding="utf-8")

    with pytest.raises(Rs3ImportError, match="No segment elements"):
        rs3tohtml(malformed)


def test_machine_provider_registry_is_read_only() -> None:
    provider = FakeProvider(rst_declaration(), echo_result("rst_tree"))
    machine = Machine([provider])

    with pytest.raises(TypeError):
        cast(MutableMapping[Technique, FakeProvider], machine.providers)[Technique.RST] = provider


def test_frozen_contract_mappings_are_deeply_read_only() -> None:
    analysis = _minimal_analysis()
    format_analysis = FormatRstAnalysis(
        document_analysis=analysis,
        table_analyses={"table": analysis},
        node_map={"node": 1},
    )
    rs4 = RS4Document(relations={"span": "rst"}, sigtypes={"dm": ("dm",)})
    ontology = OntologyLockData(
        release_version="1",
        release_status="released",
        sha256_digest="0" * 64,
        coarse_concepts=(),
        rst_dt_fine_to_coarse={"a": "b"},
        gum_fine_to_coarse={},
        dmrst_gum_model_27={},
        dmrst_rstdt_model_42={},
    )
    compatibility = RelationCompatibilityProfile(
        source_revision="revision",
        inventory_digest="digest",
        by_signal={"dm:dm": ("elaboration",)},
    )

    mappings: tuple[Mapping[Any, Any], ...] = (
        format_analysis.table_analyses,
        format_analysis.node_map,
        rs4.relations,
        rs4.sigtypes,
        ontology.rst_dt_fine_to_coarse,
        compatibility.by_signal,
    )
    for mapping in mappings:
        with pytest.raises(TypeError):
            cast(MutableMapping[Any, Any], mapping)["mutated"] = analysis


def test_capability_discovery_does_not_mutate_environment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from rdam._llm import unavailable_reason

    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    (tmp_path / ".env").write_text(
        'export OPENAI_API_KEY="dotenv-secret" # supported inline comment\n',
        encoding="utf-8",
    )
    before = dict(os.environ)

    assert unavailable_reason("openai:gpt-5.6-sol") is None
    assert dict(os.environ) == before


def test_repository_environment_receipt_still_redacts_explicit_tokens(tmp_path: Path) -> None:
    receipt = load_repository_environment(tmp_path)
    assert receipt.hf_token is None or isinstance(receipt.hf_token, SecretStr)


def _deep_rst_tree(depth: int) -> DiscourseUnit:
    node = DiscourseUnit(id=0, start=0, end=1, text="x")
    for index in range(1, depth + 1):
        right = DiscourseUnit(id=index * 2, start=index, end=index + 1, text="x")
        node = DiscourseUnit(
            id=index * 2 + 1,
            left=node,
            right=right,
            start=0,
            end=index + 1,
            text="x" * (index + 1),
            relation="elaboration",
            nuclearity="NS",
        )
    return node


def test_deep_rst_boundaries_are_iterative_and_round_trip() -> None:
    tree = _deep_rst_tree(1_500)

    payload = tree_to_dict(tree)
    restored = tree_from_dict(payload)
    typed = PydanticDiscourseUnit.from_tree(tree)

    assert restored is not None
    assert typed is not None
    assert typed.to_tree().id == tree.id
    assert Exporter().compile_relation_set(tree).count("elaboration_NS") == 1_500
    tree.clear_textfields()
    tree.fill_textfields("x" * 1_501)
    assert tree.text == "x" * 1_501


def test_tree_serialization_rejects_cycles() -> None:
    tree = DiscourseUnit(id=1)
    tree.left = tree
    with pytest.raises(ValueError, match="acyclic tree"):
        tree_to_dict(tree)


def test_deep_sdrt_cdu_membership_does_not_use_python_recursion() -> None:
    edu = ElementaryDiscourseUnit(unit_id="e0", text="x", start=0, end=1)
    cdus = [ComplexDiscourseUnit(unit_id="c0", members=["e0", "e1"])]
    second_edu = ElementaryDiscourseUnit(unit_id="e1", text="y", start=1, end=2)
    for index in range(1, 1_500):
        cdus.append(ComplexDiscourseUnit(unit_id=f"c{index}", members=[f"c{index - 1}", "e0"]))

    relation = SdrtRelation(
        relation_id="r0",
        source_id="e0",
        target_id="e1",
        label="Narration",
        structural_type=RelationStructure.COORDINATING,
    )
    analysis = SdrtAnalysis(edus=[edu, second_edu], cdus=cdus, relations=[relation])

    assert analysis.cdus[-1].unit_id == "c1499"

"""Secure eRST completion-bundle construction and strict reload tests."""

from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import TypedDict

import pytest
import torch
from isanlp_rst.annotation_rst import DiscourseUnit
from tokenizers import Tokenizer
from tokenizers.models import WordLevel
from tokenizers.pre_tokenizers import Whitespace
from tokenizers.processors import TemplateProcessing
from transformers import BertConfig, PreTrainedTokenizerFast

from isanlp_rst.contracts import (
    CorpusPartition,
    DocumentToken,
    ErstCalibrationState,
    ErstCheckpointBuildSpec,
    ErstCheckpointLicenses,
    ErstCheckpointMetrics,
    ErstCheckpointProvenance,
    ErstCheckpointResearchEvidence,
    ErstCheckpointTestVector,
    ErstCheckpointVerificationReceipt,
    ErstDecoderConfig,
    ErstFeatureSchema,
    ErstGraphComponentConfig,
    NodeKindEnum,
    NuclearityPatternEnum,
    OutputFormalismEnum,
    PrimaryRelationEdge,
    RawRelationInventory,
    RstAnalysis,
    RstDocument,
    RstNode,
    to_json,
)
from isanlp_rst.english.erst.completer import CompleterConfig, ErstCompleter
from isanlp_rst.erst.checkpoint import (
    ErstCheckpointError,
    load_erst_checkpoint_bundle,
    validate_erst_checkpoint_bundle,
)
from isanlp_rst.erst.neural_scorer import NeuralSecondaryEdgeScorer
from isanlp_rst.erst.signals import RuleBasedSignalDetector
from isanlp_rst.parser import Parser
from offline_workbench.promotion.erst import save_erst_checkpoint_bundle

_GIT_REVISION = "a" * 40
_SHA256 = "b" * 64
_RELATIONS = ("adversative-contrast", "elaboration-additional")


class _BundleInputs(TypedDict):
    scorer: NeuralSecondaryEdgeScorer
    build_spec: ErstCheckpointBuildSpec
    signal_detector: RuleBasedSignalDetector
    relation_inventory: RawRelationInventory
    decoder_config: ErstDecoderConfig
    calibration: ErstCalibrationState
    graph_config: ErstGraphComponentConfig
    test_vector: ErstCheckpointTestVector


def _canonical_hash(value: object) -> str:
    encoded = json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode()
    return hashlib.sha256(encoded).hexdigest()


def _tiny_fast_tokenizer() -> PreTrainedTokenizerFast:
    vocabulary = {
        "[PAD]": 0,
        "[UNK]": 1,
        "[CLS]": 2,
        "[SEP]": 3,
        "alpha": 4,
        "however": 5,
        "beta": 6,
        ".": 7,
    }
    backend = Tokenizer(WordLevel(vocab=vocabulary, unk_token="[UNK]"))
    backend.pre_tokenizer = Whitespace()
    backend.post_processor = TemplateProcessing(
        single="[CLS] $A [SEP]",
        special_tokens=(("[CLS]", 2), ("[SEP]", 3)),
    )
    return PreTrainedTokenizerFast(
        tokenizer_object=backend,
        unk_token="[UNK]",
        pad_token="[PAD]",
        cls_token="[CLS]",
        sep_token="[SEP]",
    )


def _tiny_scorer() -> NeuralSecondaryEdgeScorer:
    torch.manual_seed(17)
    config = BertConfig(
        vocab_size=8,
        hidden_size=16,
        num_hidden_layers=1,
        num_attention_heads=2,
        intermediate_size=32,
        max_position_embeddings=256,
    )
    scorer = NeuralSecondaryEdgeScorer(
        model_name_or_path="tiny-bert-test",
        num_struct_features=9,
        proj_dim=8,
        raw_relation_inventory=_RELATIONS,
        device="cpu",
        torch_dtype="float32",
        encoder_config=config,
        tokenizer=_tiny_fast_tokenizer(),
        calibration_temperature=1.25,
    )
    with torch.no_grad():
        scorer.bilinear.weight.zero_()
        scorer.edge_head.weight.zero_()
        assert scorer.edge_head.bias is not None
        scorer.edge_head.bias.fill_(10.0)
        scorer.rel_head.weight.zero_()
        assert scorer.rel_head.bias is not None
        scorer.rel_head.bias.copy_(torch.tensor((5.0, 0.0)))
    scorer.eval()
    return scorer


def _synthetic_test_vector(
    scorer: NeuralSecondaryEdgeScorer,
    signal_detector: RuleBasedSignalDetector,
    decoder_config: ErstDecoderConfig,
) -> ErstCheckpointTestVector:
    document = RstDocument(
        document_id="synthetic-alpha-beta",
        text="Alpha. However beta.",
        tokens=(
            DocumentToken(token_id=1, text="Alpha", start=0, end=5, sentence_id=1),
            DocumentToken(token_id=2, text=".", start=5, end=6, sentence_id=1),
            DocumentToken(token_id=3, text="However", start=7, end=14, sentence_id=2),
            DocumentToken(token_id=4, text="beta", start=15, end=19, sentence_id=2),
            DocumentToken(token_id=5, text=".", start=19, end=20, sentence_id=2),
        ),
        edus=None,
    )
    primary = RstAnalysis(
        document_id=document.document_id,
        formalism=OutputFormalismEnum.RST_TREE,
        nodes=(
            RstNode(
                node_id=1,
                kind=NodeKindEnum.EDU,
                text="Alpha.",
                char_span=(0, 6),
                edu_span=(1, 1),
            ),
            RstNode(
                node_id=2,
                kind=NodeKindEnum.EDU,
                text="However beta.",
                char_span=(7, 20),
                edu_span=(2, 2),
            ),
            RstNode(
                node_id=3,
                kind=NodeKindEnum.ROOT,
                text=document.text,
                char_span=(0, 20),
                edu_span=(1, 2),
            ),
        ),
        primary_edges=(
            PrimaryRelationEdge(
                edge_id="p1",
                parent_id=3,
                child_id=1,
                nuclearity=NuclearityPatternEnum.NS,
                relation_raw="span",
                relation_concept="Span",
            ),
            PrimaryRelationEdge(
                edge_id="p2",
                parent_id=3,
                child_id=2,
                nuclearity=NuclearityPatternEnum.NS,
                relation_raw="elaboration-additional",
                relation_concept="Elaboration",
            ),
        ),
    )
    completer = ErstCompleter(
        config=CompleterConfig(min_confidence_threshold=decoder_config.edge_threshold),
        signal_detector=signal_detector,
        decoder_config=decoder_config,
    )
    expected = completer.complete_graph(document, primary, neural_scorer=scorer)
    assert expected.signals
    assert expected.secondary_edges
    return ErstCheckpointTestVector(
        vector_id="synthetic-alpha-beta-v1",
        document_json=to_json(document),
        primary_analysis_json=to_json(primary),
        expected_analysis_json=to_json(expected),
    )


def _bundle_inputs() -> _BundleInputs:
    signal_detector = RuleBasedSignalDetector()
    scorer = _tiny_scorer()
    relation_inventory = RawRelationInventory(
        corpus_revision=_GIT_REVISION,
        partition=CorpusPartition.TRAIN,
        source_fingerprint="c" * 64,
        ontology_digest="d" * 64,
        labels=_RELATIONS,
        label_counts={relation: 1 for relation in _RELATIONS},
        concept_by_raw={
            "adversative-contrast": "Contrast",
            "elaboration-additional": "Elaboration",
        },
        edge_count=2,
    )
    decoder_config = ErstDecoderConfig(
        edge_threshold=0.6,
        raw_relation_inventory=_RELATIONS,
    )
    structural_hash = "e" * 64
    signal_detector_sha256 = signal_detector.provenance.ruleset_digest
    assert signal_detector_sha256 is not None
    feature_schema = ErstFeatureSchema(
        signal_detector_sha256=signal_detector_sha256,
        candidate_schema_sha256="f" * 64,
        structural_feature_sha256=structural_hash,
        raw_relation_inventory_sha256=relation_inventory.inventory_sha256,
        ontology_mapping_sha256=_canonical_hash(relation_inventory.concept_by_raw),
        decoder_config_sha256=decoder_config.config_sha256,
    )
    build_spec = ErstCheckpointBuildSpec(
        architecture="tiny-bert-bilinear",
        upstream_revisions={"tiny-bert-test": _GIT_REVISION},
        feature_schema=feature_schema,
        research=ErstCheckpointResearchEvidence(
            corpus_revision=_GIT_REVISION,
            corpus_receipt_sha256=_SHA256,
            split_manifest_sha256="1" * 64,
            experiment_protocol_sha256="2" * 64,
            run_receipt_sha256="3" * 64,
        ),
        metrics=ErstCheckpointMetrics(
            span_f=0.4,
            direction_f=0.3,
            relation_f=0.2,
            full_f=0.18,
            ece=0.04,
            brier=0.2,
        ),
        licenses=ErstCheckpointLicenses(
            code_license="MIT",
            base_model_license="test-only",
            annotation_license="CC-BY-4.0",
            underlying_text_policy="private mixed-license GUM text",
            private_only=True,
        ),
        provenance=ErstCheckpointProvenance(
            producer="isanlp_rst.erst.checkpoint",
            producer_version="4.0.0",
            source_revision=_GIT_REVISION,
            created_at=datetime.now(UTC),
            private_hf_repository="steve-allison-sensei/isanlp-rst-erst-v4",
        ),
    )
    return {
        "scorer": scorer,
        "build_spec": build_spec,
        "signal_detector": signal_detector,
        "relation_inventory": relation_inventory,
        "decoder_config": decoder_config,
        "calibration": ErstCalibrationState(
            temperature=1.25,
            edge_threshold=0.6,
            calibrated=True,
            fitted_partition=CorpusPartition.DEV,
        ),
        "graph_config": ErstGraphComponentConfig(
            architecture="none",
            feature_schema_sha256=structural_hash,
            has_learned_state=False,
        ),
        "test_vector": _synthetic_test_vector(scorer, signal_detector, decoder_config),
    }


def _forward(scorer: NeuralSecondaryEdgeScorer) -> dict[str, torch.Tensor]:
    source = scorer.tokenizer(
        ["alpha ."],
        padding=True,
        return_tensors="pt",
        return_offsets_mapping=True,
        return_special_tokens_mask=True,
    )
    target = scorer.tokenizer(
        ["however beta ."],
        padding=True,
        return_tensors="pt",
        return_offsets_mapping=True,
        return_special_tokens_mask=True,
    )
    with torch.inference_mode():
        return scorer(
            src_input_ids=source["input_ids"].to(scorer.dev),
            src_attention_mask=source["attention_mask"].to(scorer.dev),
            src_special_tokens_mask=source["special_tokens_mask"].to(scorer.dev),
            src_offset_mapping=source["offset_mapping"].to(scorer.dev),
            tgt_input_ids=target["input_ids"].to(scorer.dev),
            tgt_attention_mask=target["attention_mask"].to(scorer.dev),
            tgt_special_tokens_mask=target["special_tokens_mask"].to(scorer.dev),
            tgt_offset_mapping=target["offset_mapping"].to(scorer.dev),
            struct_features=torch.zeros((1, 9), dtype=torch.float32, device=scorer.dev),
        )


def _save_bundle(path: Path) -> tuple[NeuralSecondaryEdgeScorer, str]:
    inputs = _bundle_inputs()
    scorer = inputs["scorer"]
    assert isinstance(scorer, NeuralSecondaryEdgeScorer)
    manifest = save_erst_checkpoint_bundle(path, **inputs)
    return scorer, manifest.manifest_sha256


def test_safetensors_bundle_strict_reload_preserves_outputs(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    scorer, manifest_hash = _save_bundle(bundle)
    before = _forward(scorer)

    loaded = load_erst_checkpoint_bundle(bundle, device="cpu")
    after = _forward(loaded.scorer)

    assert loaded.manifest.manifest_sha256 == manifest_hash
    assert loaded.manifest.package_version == "4.0.0"
    assert loaded.graph_config.architecture == "none"
    assert loaded.signal_detector.provenance == RuleBasedSignalDetector().provenance
    assert torch.equal(before["edge_logits"], after["edge_logits"])
    assert torch.equal(before["edge_probs"], after["edge_probs"])
    assert torch.equal(before["rel_logits"], after["rel_logits"])
    assert not list(bundle.rglob("*.pt"))
    assert not list(bundle.rglob("*.bin"))


@pytest.mark.skipif(not torch.backends.mps.is_available(), reason="MPS is unavailable")
def test_checkpoint_cpu_mps_outputs_and_decoded_graphs_are_equivalent(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    _save_bundle(bundle)
    cpu = load_erst_checkpoint_bundle(bundle, device="cpu")
    mps = load_erst_checkpoint_bundle(bundle, device="mps")

    cpu_outputs = _forward(cpu.scorer)
    mps_outputs = _forward(mps.scorer)
    for key in ("edge_logits", "edge_probs", "rel_logits"):
        assert torch.allclose(
            cpu_outputs[key].cpu(),
            mps_outputs[key].cpu(),
            rtol=1e-4,
            atol=1e-5,
        )


def test_parser_erst_graph_uses_validated_completion_bundle(tmp_path: Path) -> None:
    class _Predictor:
        model_dir = "synthetic-primary"

        @staticmethod
        def parse_rst(text: str) -> dict[str, list[DiscourseUnit]]:
            assert text == "Alpha. However beta."
            left = DiscourseUnit(id=1, text="Alpha.", start=0, end=6, relation="span")
            right = DiscourseUnit(
                id=2,
                text="However beta.",
                start=7,
                end=20,
                relation="elaboration-additional",
            )
            root = DiscourseUnit(
                id=3,
                left=left,
                right=right,
                text=text,
                start=0,
                end=20,
                relation="elaboration-additional",
                nuclearity="NS",
            )
            return {"rst": [root]}

        @classmethod
        def parse_from_edus(cls, edus: list[str]) -> dict[str, list[DiscourseUnit]]:
            return cls.parse_rst(" ".join(edus))

    bundle = tmp_path / "bundle"
    _save_bundle(bundle)
    loaded = load_erst_checkpoint_bundle(bundle)
    parser = Parser.__new__(Parser)
    vars(parser)["predictor"] = _Predictor()
    parser.hf_model_version = "synthetic-primary"
    parser.segmenter = None
    parser.erst_checkpoint = loaded

    document = RstDocument(
        document_id="parser-bundle-test",
        text="Alpha. However beta.",
        tokens=(
            DocumentToken(token_id=1, text="Alpha", start=0, end=5, sentence_id=1),
            DocumentToken(token_id=2, text=".", start=5, end=6, sentence_id=1),
            DocumentToken(token_id=3, text="However", start=7, end=14, sentence_id=2),
            DocumentToken(token_id=4, text="beta", start=15, end=19, sentence_id=2),
            DocumentToken(token_id=5, text=".", start=19, end=20, sentence_id=2),
        ),
        edus=None,
    )
    analysis = parser.parse_document(document, output="erst_graph", prime_markers=False)

    assert analysis.formalism == OutputFormalismEnum.ERST_GRAPH
    assert analysis.signals
    assert analysis.secondary_edges
    assert all(edge.calibrated for edge in analysis.secondary_edges)
    assert {edge.relation_raw for edge in analysis.secondary_edges} == {"adversative-contrast"}
    assert {edge.relation_concept for edge in analysis.secondary_edges} == {"Contrast"}


def test_clean_offline_process_verifies_bundle_without_credentials_or_training_data(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    _, manifest_hash = _save_bundle(bundle)
    environment = os.environ.copy()
    environment.pop("HF_TOKEN", None)
    environment.pop("HUGGINGFACEHUB_API_TOKEN", None)
    environment["HF_HUB_OFFLINE"] = "1"
    environment["TRANSFORMERS_OFFLINE"] = "1"

    completed = subprocess.run(
        (
            sys.executable,
            "scripts/verify_erst_checkpoint.py",
            str(bundle),
            "--device",
            "cpu",
        ),
        cwd=Path(__file__).resolve().parents[1],
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )
    receipt = ErstCheckpointVerificationReceipt.model_validate_json(completed.stdout)

    assert receipt.manifest_sha256 == manifest_hash
    assert receipt.device == "cpu"
    assert receipt.signal_count > 0
    assert receipt.secondary_edge_count > 0
    assert receipt.raw_relations == ("adversative-contrast",)


def test_checkpoint_rejects_corruption_and_unlisted_members(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    _save_bundle(bundle)
    state_file = bundle / "scorer/model.safetensors"
    state_file.write_bytes(state_file.read_bytes() + b"corrupt")
    with pytest.raises(ErstCheckpointError, match="size mismatch"):
        validate_erst_checkpoint_bundle(bundle)

    clean_bundle = tmp_path / "clean-bundle"
    _save_bundle(clean_bundle)
    (clean_bundle / "undeclared.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ErstCheckpointError, match="membership mismatch"):
        validate_erst_checkpoint_bundle(clean_bundle)


def test_checkpoint_rejects_pickle_symlink_and_raw_backbone_directory(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    _save_bundle(bundle)
    (bundle / "model.pt").write_bytes(b"pickle-capable")
    with pytest.raises(ErstCheckpointError, match="forbidden artifact"):
        validate_erst_checkpoint_bundle(bundle)

    raw_backbone = tmp_path / "raw-backbone"
    raw_backbone.mkdir()
    BertConfig(vocab_size=8).save_pretrained(raw_backbone)
    with pytest.raises(ErstCheckpointError, match="manifest"):
        load_erst_checkpoint_bundle(raw_backbone)

    symlink_bundle = tmp_path / "symlink-bundle"
    _save_bundle(symlink_bundle)
    (symlink_bundle / "unsafe-link").symlink_to(symlink_bundle / "manifest.json")
    with pytest.raises(ErstCheckpointError, match="symlink"):
        validate_erst_checkpoint_bundle(symlink_bundle)


def test_checkpoint_build_is_fail_closed_and_non_overwriting(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    _save_bundle(bundle)
    with pytest.raises(FileExistsError, match="already exists"):
        save_erst_checkpoint_bundle(bundle, **_bundle_inputs())

    mismatched = _bundle_inputs()
    mismatched["calibration"] = ErstCalibrationState(
        temperature=2.0,
        edge_threshold=0.6,
        calibrated=True,
        fitted_partition=CorpusPartition.DEV,
    )
    with pytest.raises(ErstCheckpointError, match="temperatures differ"):
        save_erst_checkpoint_bundle(tmp_path / "mismatch", **mismatched)

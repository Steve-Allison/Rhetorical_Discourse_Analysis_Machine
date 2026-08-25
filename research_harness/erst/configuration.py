"""Frozen executable configuration for every mandatory eRST system."""

from pydantic import BaseModel, ConfigDict, Field

from research_harness.erst.contracts import MandatoryExperimentSystem
from research_harness.erst.systems.cross_encoder import CrossEncoderConfig
from research_harness.erst.systems.dual_encoder import DualEncoderConfig
from research_harness.erst.systems.signal_rule import SignalRuleConfig
from research_harness.erst.systems.structural import StructuralConfig


class HierarchicalAdapterConfig(BaseModel):
    """XLM-R hierarchical adapter and contrastive objective configuration."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    model_id: str = "FacebookAI/xlm-roberta-large"
    model_revision: str = "c23d21b0620b635a76227c604d44e43a9f0ee389"
    adapter_size: int = Field(default=256, gt=0)
    contrastive_temperature: float = Field(default=0.07, gt=0.0)
    contrastive_weight: float = Field(default=0.2, ge=0.0)
    epochs: int = Field(default=3, gt=0)
    batch_size: int = Field(default=8, gt=0)
    inference_batch_size: int = Field(default=128, gt=0)
    max_length: int = Field(default=256, gt=0)
    learning_rate: float = Field(default=1e-4, gt=0.0)
    edge_threshold: float = Field(default=0.5, ge=0.0, le=1.0)


class GenerativeDecoderConfig(BaseModel):
    """Qwen3 PEFT edge/no-edge decoder configuration."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    model_id: str = "Qwen/Qwen3-4B"
    model_revision: str = "1cfa9a7208912126459214e8b04321603b3df60c"
    lora_rank: int = Field(default=16, gt=0)
    lora_alpha: int = Field(default=32, gt=0)
    lora_dropout: float = Field(default=0.05, ge=0.0, lt=1.0)
    target_modules: tuple[str, ...] = (
        "q_proj",
        "k_proj",
        "v_proj",
        "o_proj",
        "gate_proj",
        "up_proj",
        "down_proj",
    )
    no_edge_label: str = "NO_EDGE"
    epochs: int = Field(default=2, gt=0)
    batch_size: int = Field(default=1, gt=0)
    gradient_accumulation_steps: int = Field(default=16, gt=0)
    max_length: int = Field(default=512, gt=0)
    learning_rate: float = Field(default=2e-4, gt=0.0)
    edge_threshold: float = Field(default=0.5, ge=0.0, le=1.0)


class GraphAttentionConfig(BaseModel):
    """Complete-primary-tree edge-featured graph-attention configuration."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    text_model_id: str = "answerdotai/ModernBERT-large"
    text_model_revision: str = "45bb4654a4d5aaff24dd11d4781fa46d39bf8c13"
    text_batch_size: int = Field(default=32, gt=0)
    max_length: int = Field(default=256, gt=0)
    hidden_size: int = Field(default=256, gt=0)
    attention_heads: int = Field(default=8, gt=0)
    layers: int = Field(default=3, gt=0)
    dropout: float = Field(default=0.1, ge=0.0, lt=1.0)
    epochs: int = Field(default=20, gt=0)
    learning_rate: float = Field(default=1e-3, gt=0.0)
    weight_decay: float = Field(default=1e-4, ge=0.0)
    edge_threshold: float = Field(default=0.5, ge=0.0, le=1.0)
    require_complete_primary_tree: bool = True


class ExperimentConfigurationBundle(BaseModel):
    """Exact typed configuration for all ten mandatory systems."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    existing_dual_encoder: DualEncoderConfig = DualEncoderConfig(
        model_id="microsoft/deberta-v3-base",
        model_revision="8ccc9b6f36199bec6961081d44eb72fb3f7353f3",
    )
    structural_only: StructuralConfig = StructuralConfig()
    text_only: CrossEncoderConfig = CrossEncoderConfig(
        model_id="google/electra-base-discriminator",
        model_revision="1ae76a97c7e84a4e640876a07453fccd636f0667",
        signal_aware=False,
        include_structure_tokens=False,
    )
    electra: CrossEncoderConfig = CrossEncoderConfig(
        model_id="google/electra-base-discriminator",
        model_revision="1ae76a97c7e84a4e640876a07453fccd636f0667",
        signal_aware=True,
        include_structure_tokens=True,
    )
    signal_rule: SignalRuleConfig = SignalRuleConfig()
    modernbert_base: CrossEncoderConfig = CrossEncoderConfig(
        model_id="answerdotai/ModernBERT-base",
        model_revision="8949b909ec900327062f0ebf497f51aef5e6f0c8",
        signal_aware=True,
        include_structure_tokens=True,
        batch_size=16,
        inference_batch_size=512,
    )
    modernbert_large: CrossEncoderConfig = CrossEncoderConfig(
        model_id="answerdotai/ModernBERT-large",
        model_revision="45bb4654a4d5aaff24dd11d4781fa46d39bf8c13",
        signal_aware=True,
        include_structure_tokens=True,
        batch_size=8,
        inference_batch_size=256,
    )
    xlm_r_hidac: HierarchicalAdapterConfig = HierarchicalAdapterConfig()
    qwen3_dedisco: GenerativeDecoderConfig = GenerativeDecoderConfig()
    edge_featured_gat: GraphAttentionConfig = GraphAttentionConfig()

    def for_system(self, system: MandatoryExperimentSystem) -> BaseModel:
        return {
            MandatoryExperimentSystem.EXISTING_DUAL_ENCODER: self.existing_dual_encoder,
            MandatoryExperimentSystem.STRUCTURAL_ONLY: self.structural_only,
            MandatoryExperimentSystem.TEXT_ONLY: self.text_only,
            MandatoryExperimentSystem.ELECTRA: self.electra,
            MandatoryExperimentSystem.SIGNAL_RULE: self.signal_rule,
            MandatoryExperimentSystem.MODERNBERT_BASE: self.modernbert_base,
            MandatoryExperimentSystem.MODERNBERT_LARGE: self.modernbert_large,
            MandatoryExperimentSystem.XLM_R_HIDAC: self.xlm_r_hidac,
            MandatoryExperimentSystem.QWEN3_DEDISCO: self.qwen3_dedisco,
            MandatoryExperimentSystem.EDGE_FEATURED_GAT: self.edge_featured_gat,
        }[system]


__all__ = [
    "ExperimentConfigurationBundle",
    "GenerativeDecoderConfig",
    "GraphAttentionConfig",
    "HierarchicalAdapterConfig",
]

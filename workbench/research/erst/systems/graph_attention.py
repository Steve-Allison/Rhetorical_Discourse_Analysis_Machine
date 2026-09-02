"""Edge-featured graph attention over each complete primary discourse tree."""

from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
from time import perf_counter

from safetensors.torch import save_file
import torch
from torch import nn
import torch.nn.functional as functional
from transformers import AutoModel, AutoTokenizer, PreTrainedModel, PreTrainedTokenizerBase

from rdam.rst.contracts.analysis import PrimaryRelationEdge, RstAnalysis
from rdam.rst.erst.environment import load_repository_environment
from workbench.research.erst.configuration import GraphAttentionConfig
from workbench.research.erst.contracts import AblationName, MandatoryExperimentSystem
from workbench.research.erst.data import CandidateShard, HarnessCandidate, ScreeningCorpusPayload
from workbench.research.erst.runner import (
    ExperimentExecutionError,
    SystemExecutionResult,
    SystemRunContext,
)
from workbench.research.erst.systems.common import CandidateScoreBatch, evaluate_and_write


def _validate_complete_primary_tree(analysis: RstAnalysis) -> None:
    node_ids = {node.node_id for node in analysis.nodes}
    if not node_ids:
        raise ValueError("graph attention requires at least one primary-tree node")
    if any(edge.parent_id not in node_ids or edge.child_id not in node_ids for edge in analysis.primary_edges):
        raise ValueError("primary tree contains an edge to an invented node")
    children = tuple(edge.child_id for edge in analysis.primary_edges)
    roots = node_ids.difference(children)
    if len(analysis.primary_edges) != len(node_ids) - 1 or len(set(children)) != len(children):
        raise ValueError("primary structure is not a complete single-parent tree")
    if len(roots) != 1:
        raise ValueError("primary structure does not have exactly one root")
    descendants: dict[int, list[int]] = defaultdict(list)
    for edge in analysis.primary_edges:
        descendants[edge.parent_id].append(edge.child_id)
    visited: set[int] = set()
    agenda = [next(iter(roots))]
    while agenda:
        node_id = agenda.pop()
        if node_id in visited:
            raise ValueError("primary structure contains a cycle")
        visited.add(node_id)
        agenda.extend(descendants[node_id])
    if visited != node_ids:
        raise ValueError("primary structure is disconnected")


def _edge_feature(edge: PrimaryRelationEdge | None, *, reverse: bool, size: int = 16) -> tuple[float, ...]:
    if edge is None:
        return (1.0, *([0.0] * (size - 1)))
    identity = f"{edge.relation_raw}\0{edge.nuclearity.value}".encode()
    digest = hashlib.sha256(identity).digest()
    hashed = tuple((byte / 127.5) - 1.0 for byte in digest[: size - 2])
    return (0.0, -1.0 if reverse else 1.0, *hashed)


class _EdgeGraphAttentionLayer(nn.Module):
    def __init__(self, hidden_size: int, heads: int, edge_size: int, dropout: float) -> None:
        super().__init__()
        if hidden_size % heads != 0:
            raise ValueError("graph hidden size must be divisible by attention heads")
        self.heads = heads
        self.head_size = hidden_size // heads
        self.query = nn.Linear(hidden_size, hidden_size, bias=False)
        self.key = nn.Linear(hidden_size, hidden_size, bias=False)
        self.value = nn.Linear(hidden_size, hidden_size, bias=False)
        self.edge_key = nn.Linear(edge_size, hidden_size, bias=False)
        self.edge_value = nn.Linear(edge_size, hidden_size, bias=False)
        self.output = nn.Linear(hidden_size, hidden_size)
        self.norm = nn.LayerNorm(hidden_size)
        self.dropout = nn.Dropout(dropout)

    def forward(
        self,
        nodes: torch.Tensor,
        senders: torch.Tensor,
        receivers: torch.Tensor,
        edge_features: torch.Tensor,
    ) -> torch.Tensor:
        node_count = len(nodes)
        query = self.query(nodes).view(node_count, self.heads, self.head_size)
        key = self.key(nodes).view(node_count, self.heads, self.head_size)
        value = self.value(nodes).view(node_count, self.heads, self.head_size)
        edge_key = self.edge_key(edge_features).view(-1, self.heads, self.head_size)
        edge_value = self.edge_value(edge_features).view(-1, self.heads, self.head_size)
        scores = (
            query[receivers] * (key[senders] + edge_key)
        ).sum(dim=-1) / math.sqrt(self.head_size)
        messages = value[senders] + edge_value
        aggregated = torch.zeros_like(query)
        for receiver in torch.unique(receivers).tolist():
            mask = receivers == receiver
            weights = torch.softmax(scores[mask], dim=0)
            aggregated[receiver] = (weights.unsqueeze(-1) * messages[mask]).sum(dim=0)
        updated = self.output(aggregated.reshape(node_count, -1))
        return self.norm(nodes + self.dropout(updated))


class _GraphScorer(nn.Module):
    encoder: PreTrainedModel

    def __init__(
        self,
        *,
        encoder: PreTrainedModel,
        config: GraphAttentionConfig,
        structural_size: int,
        relation_count: int,
    ) -> None:
        super().__init__()
        self.encoder = encoder
        for parameter in encoder.parameters():
            parameter.requires_grad = False
        encoder_size = getattr(encoder.config, "hidden_size", None)
        if not isinstance(encoder_size, int) or encoder_size <= 0:
            raise ValueError("graph text encoder requires a positive hidden size")
        self.node_projection = nn.Linear(encoder_size, config.hidden_size)
        self.layers = nn.ModuleList(
            _EdgeGraphAttentionLayer(config.hidden_size, config.attention_heads, 16, config.dropout)
            for _ in range(config.layers)
        )
        pair_size = config.hidden_size * 4 + structural_size
        self.pair = nn.Sequential(
            nn.Linear(pair_size, config.hidden_size),
            nn.GELU(),
            nn.Dropout(config.dropout),
        )
        self.edge_head = nn.Linear(config.hidden_size, 1)
        self.relation_head = nn.Linear(config.hidden_size, relation_count)

    def encode_text(
        self,
        *,
        input_ids: torch.Tensor,
        attention_mask: torch.Tensor,
    ) -> torch.Tensor:
        with torch.no_grad():
            hidden = self.encoder(input_ids=input_ids, attention_mask=attention_mask).last_hidden_state
            mask = attention_mask.unsqueeze(-1).to(hidden.dtype)
            pooled = (hidden * mask).sum(dim=1) / mask.sum(dim=1).clamp_min(1.0)
        return self.node_projection(pooled)

    def graph(
        self,
        nodes: torch.Tensor,
        senders: torch.Tensor,
        receivers: torch.Tensor,
        edge_features: torch.Tensor,
    ) -> torch.Tensor:
        for layer in self.layers:
            nodes = layer(nodes, senders, receivers, edge_features)
        return nodes

    def score_pairs(
        self,
        nodes: torch.Tensor,
        source_indices: torch.Tensor,
        target_indices: torch.Tensor,
        structural: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        source = nodes[source_indices]
        target = nodes[target_indices]
        pair = torch.cat((source, target, source * target, torch.abs(source - target), structural), dim=-1)
        hidden = self.pair(pair)
        return self.edge_head(hidden).squeeze(-1), self.relation_head(hidden)


class GraphAttentionAdapter:
    """Fuse frozen text representations with every primary-tree edge."""

    system = MandatoryExperimentSystem.EDGE_FEATURED_GAT

    def __init__(
        self,
        *,
        config: GraphAttentionConfig,
        architecture_config_sha256: str,
        repository_root: Path,
    ) -> None:
        self.config = config
        self._architecture_config_sha256 = architecture_config_sha256
        self.repository_root = repository_root.resolve()

    @property
    def architecture_config_sha256(self) -> str:
        return self._architecture_config_sha256

    def _load(
        self,
        *,
        structural_size: int,
        relation_count: int,
        device: torch.device,
    ) -> tuple[PreTrainedTokenizerBase, _GraphScorer]:
        environment = load_repository_environment(self.repository_root)
        token = environment.hf_token.get_secret_value() if environment.hf_token is not None else None
        try:
            tokenizer = AutoTokenizer.from_pretrained(
                self.config.text_model_id,
                revision=self.config.text_model_revision,
                use_fast=True,
                token=token,
            )
            if not tokenizer.is_fast:
                raise ValueError("graph text encoder requires a verified fast tokenizer")
            encoder = AutoModel.from_pretrained(
                self.config.text_model_id,
                revision=self.config.text_model_revision,
                use_safetensors=True,
                token=token,
            )
        except (OSError, RuntimeError, ValueError) as error:
            evidence = json.dumps(
                {
                    "exception_type": type(error).__name__,
                    "model_id": self.config.text_model_id,
                    "model_revision": self.config.text_model_revision,
                },
                sort_keys=True,
            ).encode()
            raise ExperimentExecutionError(
                failure_type="GraphAttentionCompatibilityError",
                message="pinned graph text representation failed its authenticated compatibility load",
                evidence=evidence,
                incompatible=True,
            ) from error
        return tokenizer, _GraphScorer(
            encoder=encoder,
            config=self.config,
            structural_size=structural_size,
            relation_count=relation_count,
        ).to(device)

    def _graph_inputs(
        self,
        *,
        tokenizer: PreTrainedTokenizerBase,
        model: _GraphScorer,
        analysis: RstAnalysis,
        device: torch.device,
        fuse_graph: bool = True,
    ) -> tuple[torch.Tensor, dict[int, int]]:
        if self.config.require_complete_primary_tree:
            _validate_complete_primary_tree(analysis)
        nodes = tuple(sorted(analysis.nodes, key=lambda item: item.node_id))
        node_index = {node.node_id: index for index, node in enumerate(nodes)}
        embeddings: list[torch.Tensor] = []
        model.encoder.eval()
        for start in range(0, len(nodes), self.config.text_batch_size):
            batch = nodes[start : start + self.config.text_batch_size]
            encoded = tokenizer(
                [node.text for node in batch],
                max_length=self.config.max_length,
                padding=True,
                truncation=True,
                return_tensors="pt",
            )
            embeddings.append(
                model.encode_text(
                    input_ids=encoded["input_ids"].to(device),
                    attention_mask=encoded["attention_mask"].to(device),
                )
            )
        projected = torch.cat(embeddings, dim=0)
        sender_ids: list[int] = []
        receiver_ids: list[int] = []
        features: list[tuple[float, ...]] = []
        for edge in analysis.primary_edges:
            parent = node_index[edge.parent_id]
            child = node_index[edge.child_id]
            sender_ids.extend((parent, child))
            receiver_ids.extend((child, parent))
            features.extend((_edge_feature(edge, reverse=False), _edge_feature(edge, reverse=True)))
        for index in range(len(nodes)):
            sender_ids.append(index)
            receiver_ids.append(index)
            features.append(_edge_feature(None, reverse=False))
        graph = (
            model.graph(
                projected,
                torch.tensor(sender_ids, dtype=torch.long, device=device),
                torch.tensor(receiver_ids, dtype=torch.long, device=device),
                torch.tensor(features, dtype=torch.float32, device=device),
            )
            if fuse_graph
            else projected
        )
        return graph, node_index

    @staticmethod
    def _pair_tensors(
        candidates: tuple[HarnessCandidate, ...],
        node_index: dict[int, int],
        device: torch.device,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        try:
            sources = [node_index[item.candidate.source_id] for item in candidates]
            targets = [node_index[item.candidate.target_id] for item in candidates]
        except KeyError as error:
            raise ValueError("graph candidate refers to a node absent from the primary tree") from error
        return (
            torch.tensor(sources, dtype=torch.long, device=device),
            torch.tensor(targets, dtype=torch.long, device=device),
            torch.tensor(
                [item.candidate.structural_features for item in candidates],
                dtype=torch.float32,
                device=device,
            ),
        )

    def execute(self, context: SystemRunContext[ScreeningCorpusPayload]) -> SystemExecutionResult:
        payload = context.data.payload
        relations = payload.raw_relation_inventory.labels
        relation_to_index = {relation: index for index, relation in enumerate(relations)}
        structural_size = len(payload.train_candidates[0].candidate.structural_features)
        if structural_size <= 0:
            raise ValueError("graph attention requires non-empty structural features")
        device = torch.device(context.request.device)
        torch.manual_seed(context.request.seed)
        tokenizer, model = self._load(
            structural_size=structural_size,
            relation_count=len(relations),
            device=device,
        )
        train_by_document: dict[str, list[HarnessCandidate]] = defaultdict(list)
        for candidate in payload.train_candidates:
            train_by_document[candidate.candidate.document_id].append(candidate)
        optimizer = torch.optim.AdamW(
            (parameter for parameter in model.parameters() if parameter.requires_grad),
            lr=self.config.learning_rate,
            weight_decay=self.config.weight_decay,
        )
        generator = torch.Generator(device="cpu").manual_seed(context.request.seed)
        shards = tuple(
            shard for shard in payload.training_shards if shard.document_id in train_by_document
        )
        steps = 0
        final_loss: float | None = None
        model.train()
        for _ in range(self.config.epochs):
            order = torch.randperm(len(shards), generator=generator).tolist()
            for shard_index in order:
                shard = shards[shard_index]
                candidates = tuple(train_by_document[shard.document_id])
                _, analysis = payload.load_analysis(shard)
                graph, node_index = self._graph_inputs(
                    tokenizer=tokenizer,
                    model=model,
                    analysis=analysis,
                    device=device,
                    fuse_graph=context.request.ablation != AblationName.GRAPH_FUSION,
                )
                sources, targets, structural = self._pair_tensors(candidates, node_index, device)
                edge_logits, relation_logits = model.score_pairs(graph, sources, targets, structural)
                edge_targets = torch.tensor(
                    [float(item.candidate.is_gold_edge) for item in candidates],
                    dtype=torch.float32,
                    device=device,
                )
                relation_targets = torch.tensor(
                    [
                        relation_to_index[item.candidate.gold_relation]
                        if item.candidate.gold_relation is not None
                        else -100
                        for item in candidates
                    ],
                    dtype=torch.long,
                    device=device,
                )
                edge_loss = functional.binary_cross_entropy_with_logits(
                    edge_logits,
                    edge_targets,
                    pos_weight=torch.tensor(4.0, device=device),
                )
                positive_mask = relation_targets != -100
                relation_loss = (
                    functional.cross_entropy(
                        relation_logits[positive_mask],
                        relation_targets[positive_mask],
                    )
                    if bool(positive_mask.any().item())
                    else torch.zeros((), device=device)
                )
                loss = edge_loss + relation_loss
                optimizer.zero_grad()
                loss.backward()
                torch.nn.utils.clip_grad_norm_(
                    (parameter for parameter in model.parameters() if parameter.requires_grad),
                    1.0,
                )
                optimizer.step()
                final_loss = float(loss.detach().cpu().item())
                steps += 1
        if steps <= 0 or final_loss is None:
            raise RuntimeError("graph attention completed zero optimization steps")
        checkpoint = context.run_directory / "graph.safetensors"
        trainable_state = {
            name: tensor.detach().cpu().contiguous()
            for name, tensor in model.state_dict().items()
            if not name.startswith("encoder.")
        }
        save_file(trainable_state, checkpoint)
        tokenizer.save_pretrained(context.run_directory / "tokenizer")

        active_shard: CandidateShard | None = None
        active_graph: torch.Tensor | None = None
        active_node_index: dict[int, int] | None = None

        def score_candidates(candidates: tuple[HarnessCandidate, ...]) -> CandidateScoreBatch:
            nonlocal active_shard, active_graph, active_node_index
            document_ids = {item.candidate.document_id for item in candidates}
            if len(document_ids) != 1:
                raise ValueError("graph scorer batch must contain exactly one document")
            document_id = next(iter(document_ids))
            shard = next(
                (item for item in payload.development_shards if item.document_id == document_id),
                None,
            )
            if shard is None:
                raise ValueError("graph scorer received a document outside governed dev data")
            if active_shard != shard:
                _, analysis = payload.load_analysis(shard)
                model.eval()
                with torch.inference_mode():
                    active_graph, active_node_index = self._graph_inputs(
                        tokenizer=tokenizer,
                        model=model,
                        analysis=analysis,
                        device=device,
                        fuse_graph=context.request.ablation != AblationName.GRAPH_FUSION,
                    )
                active_shard = shard
            if active_graph is None or active_node_index is None:
                raise RuntimeError("graph scorer failed to initialize its document graph")
            probabilities: list[float] = []
            relation_rows: list[tuple[float, ...]] = []
            latencies: list[float] = []
            with torch.inference_mode():
                for start in range(0, len(candidates), self.config.text_batch_size):
                    batch = candidates[start : start + self.config.text_batch_size]
                    if device.type == "mps":
                        torch.mps.synchronize()
                    started = perf_counter()
                    sources, targets, structural = self._pair_tensors(
                        batch,
                        active_node_index,
                        device,
                    )
                    edge_logits, relation_logits = model.score_pairs(
                        active_graph,
                        sources,
                        targets,
                        structural,
                    )
                    edge_probabilities = torch.sigmoid(edge_logits)
                    if device.type == "mps":
                        torch.mps.synchronize()
                    latencies.append((perf_counter() - started) * 1000.0)
                    probabilities.extend(float(value) for value in edge_probabilities.cpu().tolist())
                    relation_rows.extend(
                        tuple(float(value) for value in row)
                        for row in relation_logits.cpu().tolist()
                    )
            return CandidateScoreBatch(
                edge_probabilities=tuple(probabilities),
                relation_logits=tuple(relation_rows),
                latency_samples_ms=tuple(latencies),
            )

        return evaluate_and_write(
            payload=payload,
            run_directory=context.run_directory,
            checkpoint_path=checkpoint.name,
            score_candidates=score_candidates,
            edge_threshold=self.config.edge_threshold,
            execution_steps=steps,
            training_loss=final_loss,
            calibration_enabled=context.request.ablation != AblationName.CALIBRATION,
        )


__all__ = ["GraphAttentionAdapter"]

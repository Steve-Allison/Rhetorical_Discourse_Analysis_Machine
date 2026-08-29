import json
import logging
import pickle
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import razdel
import torch
from huggingface_hub import hf_hub_download
from huggingface_hub.errors import EntryNotFoundError
from tqdm import tqdm
from transformers import AutoConfig, AutoModel, AutoTokenizer

from isanlp_rst.base_predictor import BasePredictor, resolve_device, str2bool
from isanlp_rst.utils.du_converter import DUConverter

from .inventory import (
    ensure_unirst_module_aliases,
    import_relation_table_from_legacy_pickle,
    load_relation_inventory_json,
    parse_corpora_config,
    relation_table_from_txt,
)
from .src.parser.data import Data
from .src.parser.parsing_net import ParsingNet
from .src.parser.parsing_net_bottom_up import ParsingNetBottomUp


class PredictorUniRST(BasePredictor):
    def __init__(
        self,
        model_dir: str | None = None,
        hf_model_name: str | None = None,
        hf_model_version: str | None = None,
        relinventory: str | None = None,
        relinventory_idx: int = 0,
        device: str | torch.device | None = None,
        cuda_device: int | None = None,
        dtype: str | torch.dtype | None = None,
    ) -> None:
        ensure_unirst_module_aliases()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        if model_dir is not None and hf_model_name is not None:
            raise ValueError("Pass exactly one of `model_dir` or `hf_model_name`, not both.")

        model_filename = "best_weights.pt"
        config_filename = "config.json"

        if model_dir is not None:
            self.mode = "local"
            self.model_dir = Path(model_dir)
            self.hf_model_name = None
            self.hf_model_version = None
            self.model_file = str(self.model_dir / model_filename)
            self.config_path = str(self.model_dir / config_filename)
        elif hf_model_name is not None:
            self.mode = "hf"
            self.model_dir = None
            self.hf_model_name = hf_model_name
            self.hf_model_version = hf_model_version
            self.model_file = hf_hub_download(
                repo_id=hf_model_name,
                filename=model_filename,
                revision=hf_model_version,
            )
            self.config_path = hf_hub_download(
                repo_id=hf_model_name,
                filename=config_filename,
                revision=hf_model_version,
            )
        else:
            raise ValueError("Pass either `model_dir` or `hf_model_name`.")

        self.config = json.loads(Path(self.config_path).read_text(encoding="utf-8"))
        self.dataset_names = parse_corpora_config(self.config["data"]["corpora"])

        self.relinventory = relinventory
        if self.relinventory is None:
            self.relinventory_idx = relinventory_idx
            if not (0 <= self.relinventory_idx < len(self.dataset_names)):
                raise ValueError(
                    f"relinventory_idx={self.relinventory_idx} is out of bounds for "
                    f"dataset_names ({self.dataset_names})."
                )
        else:
            key = self.relinventory.strip().lower()
            try:
                self.relinventory_idx = self.dataset_names.index(key)
            except ValueError as exc:
                raise ValueError(
                    f"Unknown relinventory {self.relinventory!r}. Available datasets: {self.dataset_names}."
                ) from exc

        self.relation_tables: list[Sequence[str]] = []
        for corpus_name in self.dataset_names:
            relation_table = self._load_inventory(corpus_name)
            if relation_table is None:
                raise FileNotFoundError(
                    f"Could not find relation inventory for corpus '{corpus_name}'. "
                    "Package relation_table_*.txt, data_manager_*.json, "
                    "or a legacy data_manager_*.pickle with the model."
                )
            self.relation_tables.append(relation_table)

        self._device = resolve_device(device, cuda_device)
        self._dtype = self._resolve_dtype(dtype)

        self._load_model()

    @staticmethod
    def _ensure_module_aliases() -> None:
        ensure_unirst_module_aliases()

    def _resolve_resource(self, relative_path: str) -> str | None:
        candidate = Path(relative_path)
        if candidate.is_absolute() and candidate.exists():
            return str(candidate)

        if self.mode == "local":
            if self.model_dir is None:
                return None
            path = self.model_dir / relative_path
            if path.exists():
                return str(path)
            return None

        # HF mode: distinguish "resource not in repo" (silent miss → next
        # candidate / pickle fallback) from network/auth/disk errors (raise).
        if self.hf_model_name is None:
            return None
        try:
            return hf_hub_download(
                repo_id=self.hf_model_name,
                filename=relative_path,
                revision=self.hf_model_version,
            )
        except EntryNotFoundError:
            return None
        except OSError:
            # Network / auth / disk failures must not look like "inventory
            # missing" — re-raise so callers see the real cause.
            raise

    def _corpus_variants(self, corpus_name: str) -> list[str]:
        lower = corpus_name.lower()
        variants = {lower}
        variants.add(lower.replace(".", "_"))
        variants.add(lower.replace("-", "_"))
        if lower.endswith("-tr"):
            variants.add(lower[:-3])
        if lower.endswith("_tr"):
            variants.add(lower[:-3])
        if lower in {"rst-dt-tr", "rst_dt_tr"}:
            variants.add("rst-dt")
            variants.add("rst_dt")
        if lower in {"gum10-tr", "gum10_tr"}:
            variants.add("gum10")
            variants.add("gum")
        return [variant for variant in variants if variant]

    def _unique_candidates(self, filenames: list[str]) -> list[str]:
        candidates: list[str] = []
        for filename in filenames:
            candidates.extend((filename, f"data/{filename}", f"data/dms/{filename}"))
        return list(dict.fromkeys(candidates))

    def _load_inventory(self, corpus_name: str) -> list[str] | None:
        """txt (published) → JSON (native) → legacy pickle (labels only)."""
        return (
            self._load_relation_table(corpus_name)
            or self._load_inventory_json(corpus_name)
            or self._load_legacy_pickle_inventory(corpus_name)
        )

    def _load_legacy_pickle_inventory(self, corpus_name: str) -> list[str] | None:
        filenames = [f"data_manager_{variant}.pickle" for variant in self._corpus_variants(corpus_name)]
        for rel_path in self._unique_candidates(filenames):
            resolved = self._resolve_resource(rel_path)
            if not resolved:
                continue
            try:
                return import_relation_table_from_legacy_pickle(Path(resolved))
            except (pickle.UnpicklingError, EOFError, OSError, ValueError) as exc:
                self.logger.warning("Skipping unreadable data_manager pickle %s: %s", resolved, exc)
                continue
        return None

    def _load_inventory_json(self, corpus_name: str) -> list[str] | None:
        filenames = [f"data_manager_{variant}.json" for variant in self._corpus_variants(corpus_name)]
        for rel_path in self._unique_candidates(filenames):
            resolved = self._resolve_resource(rel_path)
            if not resolved:
                continue
            try:
                return load_relation_inventory_json(Path(resolved))
            except (OSError, json.JSONDecodeError, ValueError) as exc:
                self.logger.warning("Skipping unreadable data_manager JSON %s: %s", resolved, exc)
                continue
        return None

    def _load_relation_table(self, corpus_name: str) -> list[str] | None:
        """Load ``relation_table_<variant>.txt`` using corpus aliases."""
        for variant in self._corpus_variants(corpus_name):
            resolved = self._resolve_resource(f"relation_table_{variant}.txt")
            if not resolved:
                continue
            return relation_table_from_txt(Path(resolved).read_text(encoding="utf-8"))
        return None

    @staticmethod
    def _classifier_count_from_state_dict(state_dict: dict) -> int | None:
        """Count distinct ``label_classifiers.<N>.*`` indices in a state dict.

        Returns ``None`` if the checkpoint has no such keys (older variant,
        DMRST-shaped state dict, etc.) — caller falls back to the configured
        architecture.
        """
        indices = set()
        for key in state_dict.keys():
            if key.startswith("label_classifiers."):
                parts = key.split(".", 2)
                if len(parts) >= 2 and parts[1].isdigit():
                    indices.add(int(parts[1]))
        return (max(indices) + 1) if indices else None

    def _load_model(self) -> None:
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.config["model"]["transformer"]["model_name"],
            use_fast=True,
        )
        self.tokenizer.model_max_length = int(
            1e9
        )  # The parser relies on a sliding window encoding, so we'll suppress the max_len warning this way.

        transformer_config = AutoConfig.from_pretrained(self.config["model"]["transformer"]["model_name"])
        transformer = AutoModel.from_config(transformer_config).to(self._device)

        self.tokenizer.add_tokens(["<P>"])
        transformer.resize_token_embeddings(len(self.tokenizer))

        # Load weights ONCE, up front. The classifier count in the trained
        # checkpoint is the source of truth for the architecture — we use it
        # to allocate the right number of `label_classifiers` so the
        # subsequent `load_state_dict` call cannot mismatch.
        state_dict = self._load_torch_weights(self.model_file, self._device)
        ckpt_n_classifiers = self._classifier_count_from_state_dict(state_dict)

        rel_tables = self.relation_tables
        use_union = str2bool(self.config["model"].get("use_union_relations", False)) and len(rel_tables) > 1

        if use_union:
            union_table: list[str] = []
            label2id: dict[str, int] = {}
            dataset_masks: list[list[bool]] = []
            label_maps: list[list[int]] = []

            for table in rel_tables:
                for lbl in table:
                    key = lbl.lower()
                    if key not in label2id:
                        label2id[key] = len(union_table)
                        union_table.append(key)

            for table in rel_tables:
                mask = [False] * len(union_table)
                mapping_tbl = []
                for lbl in table:
                    uid = label2id[lbl.lower()]
                    mask[uid] = True
                    mapping_tbl.append(uid)
                dataset_masks.append(mask)
                label_maps.append(mapping_tbl)

            self.label_maps = label_maps
            model_relation_tables = rel_tables
            classes_numbers = [len(union_table)]
            dataset2classifier = list(range(len(rel_tables)))
            model_specific_config = {
                "relation_tables": model_relation_tables,
                "relation_vocab": union_table,
                "dataset_masks": dataset_masks,
                "classes_numbers": classes_numbers,
                "dataset2classifier": dataset2classifier,
            }
        else:
            # Non-union path: pick the architecture that matches the
            # checkpoint's classifier count.
            #
            # - If the checkpoint has one classifier per corpus, allocate one
            #   per corpus (no dedup).
            # - If the checkpoint dedupes by relation-table equality (older
            #   training convention), apply that dedup and allocate the
            #   smaller number of classifiers.
            # - If the checkpoint has no classifier keys (legacy variant),
            #   fall back to one-per-corpus, the more general default.
            n_corpora = len(rel_tables)

            if ckpt_n_classifiers is None or ckpt_n_classifiers == n_corpora:
                model_relation_tables = list(rel_tables)
                classes_numbers = [len(t) for t in rel_tables]
                dataset2classifier = list(range(n_corpora))
            elif ckpt_n_classifiers < n_corpora:
                unique_tables: list[Sequence[str]] = []
                mapping: list[int] = []
                for table in rel_tables:
                    for idx, unique in enumerate(unique_tables):
                        if list(table) == list(unique):
                            mapping.append(idx)
                            break
                    else:
                        mapping.append(len(unique_tables))
                        unique_tables.append(table)
                if len(unique_tables) != ckpt_n_classifiers:
                    raise RuntimeError(
                        f"Checkpoint has {ckpt_n_classifiers} label classifier(s) "
                        f"but relation-table dedup produced {len(unique_tables)}. "
                        f"The published model assets likely lack the per-corpus "
                        f"data_manager pickles needed to reconstruct distinct "
                        f"relation tables. Affected corpora: {self.dataset_names}."
                    )
                model_relation_tables = unique_tables
                classes_numbers = [len(t) for t in unique_tables]
                dataset2classifier = mapping
            else:
                raise RuntimeError(
                    f"Checkpoint declares {ckpt_n_classifiers} label classifier(s) "
                    f"but only {n_corpora} corpora are configured "
                    f"({self.dataset_names}). Cannot construct a consistent model."
                )

            self.label_maps = None
            model_specific_config = {
                "relation_tables": model_relation_tables,
                "classes_numbers": classes_numbers,
                "dataset2classifier": dataset2classifier,
            }

        model_config = {
            "transformer": transformer,
            "emb_dim": int(self.config["model"]["transformer"]["emb_size"]),
            # Inherited ParsingNet kwarg name; holds a torch.device (may be mps).
            "cuda_device": self._device,
        }
        model_config.update(model_specific_config)
        model_config.update(self._get_model_configs())

        parser_type = self.config["model"].get("parser_type", "top-down")
        model_cls = ParsingNet if parser_type == "top-down" else ParsingNetBottomUp

        self.model = model_cls(**model_config).to(self._device)
        self.model.load_state_dict(state_dict)
        self.model.eval()

    def _get_model_configs(self) -> dict:
        config: dict = {}

        transformer_cfg = self.config["model"].get("transformer", {})
        segmenter_cfg = self.config["model"].get("segmenter", {})
        model_cfg = self.config.get("model", {})

        if "normalize" in transformer_cfg:
            config["normalize_embeddings"] = transformer_cfg.get("normalize")

        if "window_size" in transformer_cfg:
            config["window_size"] = int(transformer_cfg.get("window_size"))

        if "window_padding" in transformer_cfg:
            config["window_padding"] = int(transformer_cfg.get("window_padding"))

        if "hidden_size" in model_cfg:
            hidden_size = int(model_cfg.get("hidden_size"))
            config["hidden_size"] = hidden_size
            config["decoder_input_size"] = hidden_size
            config["classifier_input_size"] = hidden_size
            config["classifier_hidden_size"] = hidden_size

        if "type" in segmenter_cfg:
            config["segmenter_type"] = segmenter_cfg.get("type")

        if "hidden_dim" in segmenter_cfg:
            config["segmenter_hidden_dim"] = int(segmenter_cfg.get("hidden_dim"))

        if "lstm_num_layers" in segmenter_cfg:
            config["segmenter_lstm_num_layers"] = segmenter_cfg.get("lstm_num_layers")

        if "lstm_dropout" in segmenter_cfg:
            config["segmenter_lstm_dropout"] = segmenter_cfg.get("lstm_dropout")

        if "lstm_bidirectional" in segmenter_cfg:
            config["segmenter_lstm_bidirectional"] = str2bool(segmenter_cfg.get("lstm_bidirectional"))

        if "use_crf" in segmenter_cfg:
            config["segmenter_use_crf"] = str2bool(segmenter_cfg.get("use_crf"))

        if "use_log_crf" in segmenter_cfg:
            config["segmenter_use_log_crf"] = str2bool(segmenter_cfg.get("use_log_crf"))

        if "use_sent_boundaries" in segmenter_cfg:
            config["segmenter_use_sent_boundaries"] = str2bool(segmenter_cfg.get("use_sent_boundaries"))

        if "separated" in segmenter_cfg:
            config["separated_segmentation"] = str2bool(segmenter_cfg.get("separated"))

        if "if_edu_start_loss" in segmenter_cfg:
            config["segmenter_if_edu_start_loss"] = str2bool(segmenter_cfg.get("if_edu_start_loss"))

        if "edu_encoding_kind" in model_cfg:
            config["edu_encoding_kind"] = model_cfg.get("edu_encoding_kind")

        if "du_encoding_kind" in model_cfg:
            config["du_encoding_kind"] = model_cfg.get("du_encoding_kind")

        if "rel_classification_kind" in model_cfg:
            config["rel_classification_kind"] = model_cfg.get("rel_classification_kind")

        if "token_bilstm_hidden" in model_cfg:
            config["token_bilstm_hidden"] = int(model_cfg.get("token_bilstm_hidden"))

        if "use_discriminator" in model_cfg:
            config["use_discriminator"] = str2bool(model_cfg.get("use_discriminator"))

        return config

    def tokenize(self, data: Data) -> Data:
        """Takes word-level tokenized data and converts it to transformer subword inputs."""

        # (word_start_char, word_end_char+1) for each token
        word_offsets = []
        for document in data.input_sentences:
            doc_word_offsets = []
            cur_char = 0
            for word in document:
                doc_word_offsets.append((cur_char, cur_char + len(word)))
                cur_char += len(word) + 1
            word_offsets.append(doc_word_offsets)

        texts = [" ".join(line).strip() for line in data.input_sentences]
        tokens = self.tokenizer(texts, add_special_tokens=False, return_offsets_mapping=True)
        tokens["entity_ids"] = None
        tokens["entity_position_ids"] = None

        # recount edu_breaks for subwords
        subword_edu_breaks = []
        for doc_word_offsets, doc_subword_offsets, edu_breaks in zip(
            word_offsets,
            tokens["offset_mapping"],
            data.edu_breaks,
            strict=True,
        ):
            subword_edu_breaks.append(self._recount_spans(doc_word_offsets, doc_subword_offsets, edu_breaks))

        if self.label_maps:
            if self.relinventory_idx >= len(self.label_maps):
                raise IndexError(
                    f"relinventory_idx={self.relinventory_idx} is out of bounds for relation inventories "
                    f"of size {len(self.label_maps)}"
                )
            mapping = self.label_maps[self.relinventory_idx]
            remapped = [[mapping[idx] for idx in doc] for doc in data.relation_label]
        else:
            remapped = data.relation_label

        return Data(
            input_sentences=tokens["input_ids"],
            entity_ids=tokens["entity_ids"],
            entity_position_ids=tokens["entity_position_ids"],
            sent_breaks=None,
            edu_breaks=subword_edu_breaks,
            decoder_input=data.decoder_input,
            relation_label=remapped,
            parsing_breaks=data.parsing_breaks,
            golden_metric=data.golden_metric,
            parents_index=data.parents_index,
            sibling=data.sibling,
            dataset_index=[self.relinventory_idx] * len(data.input_sentences),
        )

    def get_batches(self, data: Data, size: int) -> list[Data]:
        """Splits a batch into multiple smaller batches of the given size.

        Note: ``data.dataset_index`` must be populated (the predictor's
        ``tokenize`` method does this). Callers passing un-tokenized ``Data``
        with ``dataset_index=None`` will hit a ``ValueError`` here.
        """

        if len(data.input_sentences) < size:
            return [data]

        if data.dataset_index is None:
            raise ValueError("Data.dataset_index is None; call `tokenize` before `get_batches`.")

        _input_sentences = list(self.divide_chunks(data.input_sentences, size))
        _edu_breaks = list(self.divide_chunks(data.edu_breaks, size))
        _decoder_input = list(self.divide_chunks(data.decoder_input, size))
        _relation_label = list(self.divide_chunks(data.relation_label, size))
        _parsing_breaks = list(self.divide_chunks(data.parsing_breaks, size))
        _golden_metric = list(self.divide_chunks(data.golden_metric, size))
        _dataset_index = list(self.divide_chunks(data.dataset_index, size))

        batches = []
        for (
            input_sentences,
            edu_breaks,
            decoder_input,
            relation_label,
            parsing_breaks,
            golden_metric,
            dataset_index,
        ) in tqdm(
            zip(
                _input_sentences,
                _edu_breaks,
                _decoder_input,
                _relation_label,
                _parsing_breaks,
                _golden_metric,
                _dataset_index,
                strict=True,
            ),
            total=len(_input_sentences),
        ):
            batches.append(
                Data(
                    input_sentences=input_sentences,
                    entity_ids=None,
                    entity_position_ids=None,
                    sent_breaks=None,
                    edu_breaks=edu_breaks,
                    decoder_input=decoder_input,
                    relation_label=relation_label,
                    parsing_breaks=parsing_breaks,
                    golden_metric=golden_metric,
                    parents_index=None,
                    sibling=None,
                    dataset_index=dataset_index,
                )
            )

        return batches

    def parse_rst(
        self,
        text: str,
        tokens: Sequence[str] | None = None,
        token_offsets: Sequence[tuple[int, int]] | None = None,
    ) -> dict:
        """Parse text into an RST tree.

        Args:
            text: Original document text.
            tokens: Optional pre-tokenized words to avoid internal tokenization.
            token_offsets: Optional character offsets for the provided tokens.

        Returns:
            A dictionary with token annotations and the predicted RST tree.
        """
        if tokens is not None:
            # Single custom pre-tokenized invocation
            if text is None:
                raise ValueError("`text` must be provided for parsing.")
            if not isinstance(text, str):
                raise TypeError(f"`text` must be a str, got {type(text).__name__}.")
            if not text.strip():
                raise ValueError("`text` must be non-empty (got empty/whitespace-only input).")

            word_tokens = list(tokens)
            offsets = self._guess_token_offsets(text, word_tokens) if token_offsets is None else list(token_offsets)
            offset_positions, original_offsets = self.build_offset_converter_from_words(text, word_tokens, offsets)

            if len(word_tokens) < 3:
                tree = DUConverter.dummy_tree(word_tokens)
                self.remap_tree_offsets(tree, offset_positions, original_offsets, text)
                return {"rst": [tree]}

            data = {
                "input_sentences": [word_tokens],
                "edu_breaks": [[]],
                "decoder_input": [[]],
                "relation_label": [[]],
                "parsing_breaks": [[]],
                "golden_metric": [[]],
            }
            input_data = Data(**data)
            predictions = {
                "tokens": [],
                "spans": [],
                "edu_breaks": [],
                "true_spans": [],
                "true_edu_breaks": [],
            }
            batch = self.tokenize(input_data)
            dataset_index = batch.dataset_index
            if dataset_index is None:
                raise ValueError("Data.dataset_index is None; call `tokenize` before parse.")

            with torch.inference_mode(), self._autocast():
                _, _, span_batch, _, predict_edu_breaks = self.model.testing_loss(
                    batch.input_sentences,
                    batch.sent_breaks,
                    batch.entity_ids,
                    batch.entity_position_ids,
                    batch.edu_breaks,
                    batch.relation_label,
                    batch.parsing_breaks,
                    generate_tree=True,
                    use_pred_segmentation=True,
                    dataset_index=dataset_index,
                )

            predictions["tokens"] += [self.tokenizer.convert_ids_to_tokens(sent) for sent in batch.input_sentences]
            if span_batch is None:
                raise RuntimeError("testing_loss returned no spans with generate_tree=True")
            predictions["spans"] += span_batch
            predictions["edu_breaks"] += predict_edu_breaks
            predictions["true_spans"] += batch.golden_metric
            predictions["true_edu_breaks"] += batch.edu_breaks

            tree = DUConverter(predictions, tokenization_type="default").collect(tokens=data["input_sentences"])[0]
            self.remap_tree_offsets(tree, offset_positions, original_offsets, text)
            return {"rst": [tree]}

        return self.parse_rst_batch([text], batch_size=1)[0]

    def parse_rst_batch(self, texts: Sequence[str], batch_size: int = 16) -> list[dict[str, Any]]:
        """Parses multiple texts in batched forward passes using UniRST.

        Args:
            texts: Sequence of input texts to parse.
            batch_size: Maximum batch size per forward pass.

        Returns:
            list[dict]: List of parser output dictionaries containing ``"rst": [tree]``.
        """
        if not texts:
            return []
        if batch_size <= 0:
            raise ValueError(f"batch_size must be positive, got {batch_size}")

        for idx, text in enumerate(texts):
            if text is None:
                raise ValueError(f"`text` at index {idx} must be provided for parsing.")
            if not isinstance(text, str):
                raise TypeError(f"`text` at index {idx} must be a str, got {type(text).__name__}.")
            if not text.strip():
                raise ValueError(f"`text` at index {idx} must be non-empty (got empty/whitespace-only input).")

        results: list[dict[str, Any]] = [{}] * len(texts)

        for chunk_start in range(0, len(texts), batch_size):
            chunk_texts = list(texts[chunk_start : chunk_start + batch_size])

            model_indices: list[int] = []
            model_input_sentences: list[list[str]] = []
            chunk_offset_positions: list[list[int]] = []
            chunk_original_offsets: list[list[int]] = []

            for local_idx, text in enumerate(chunk_texts):
                global_idx = chunk_start + local_idx
                razdel_tokens = list(razdel.tokenize(text))
                word_tokens = [token.text for token in razdel_tokens]
                offsets = [(token.start, token.stop) for token in razdel_tokens]
                offset_positions, original_offsets = self.build_offset_converter_from_words(text, word_tokens, offsets)

                if len(word_tokens) < 3:
                    tree = DUConverter.dummy_tree(word_tokens)
                    self.remap_tree_offsets(tree, offset_positions, original_offsets, text)
                    results[global_idx] = {"rst": [tree]}
                else:
                    model_indices.append(global_idx)
                    model_input_sentences.append(word_tokens)
                    chunk_offset_positions.append(offset_positions)
                    chunk_original_offsets.append(original_offsets)

            if not model_indices:
                continue

            data = {
                "input_sentences": model_input_sentences,
                "edu_breaks": [[] for _ in model_input_sentences],
                "decoder_input": [[] for _ in model_input_sentences],
                "relation_label": [[] for _ in model_input_sentences],
                "parsing_breaks": [[] for _ in model_input_sentences],
                "golden_metric": [[] for _ in model_input_sentences],
            }
            input_data = Data(**data)
            batch = self.tokenize(input_data)
            dataset_index = batch.dataset_index
            if dataset_index is None:
                raise ValueError("Data.dataset_index is None; call `tokenize` before parse.")

            with torch.inference_mode(), self._autocast():
                _, _, span_batch, _, predict_edu_breaks = self.model.testing_loss(
                    batch.input_sentences,
                    batch.sent_breaks,
                    batch.entity_ids,
                    batch.entity_position_ids,
                    batch.edu_breaks,
                    batch.relation_label,
                    batch.parsing_breaks,
                    generate_tree=True,
                    use_pred_segmentation=True,
                    dataset_index=dataset_index,
                )

            if span_batch is None:
                raise RuntimeError("testing_loss returned no spans with generate_tree=True")

            batch_tokens = [self.tokenizer.convert_ids_to_tokens(sent) for sent in batch.input_sentences]
            predictions = {
                "tokens": batch_tokens,
                "spans": span_batch,
                "edu_breaks": predict_edu_breaks,
                "true_spans": batch.golden_metric,
                "true_edu_breaks": batch.edu_breaks,
            }

            trees = DUConverter(predictions, tokenization_type="default").collect(tokens=data["input_sentences"])

            for g_idx, tree, offset_pos, orig_off in zip(
                model_indices, trees, chunk_offset_positions, chunk_original_offsets, strict=True
            ):
                self.remap_tree_offsets(tree, offset_pos, orig_off, texts[g_idx])
                results[g_idx] = {"rst": [tree]}

        return results

    def parse_from_edus(self, edus: Sequence[str]) -> dict:
        normalized_edus = self._validate_edus(edus)
        text, spans = self._compute_edu_char_spans(normalized_edus)

        razdel_tokens = list(razdel.tokenize(text))
        word_tokens = [token.text for token in razdel_tokens]
        offsets = [(token.start, token.stop) for token in razdel_tokens]

        offset_positions, original_offsets = self.build_offset_converter_from_words(text, word_tokens, offsets)

        if not word_tokens:
            raise ValueError("Unable to tokenize text derived from the provided EDUs.")

        if len(normalized_edus) == 1:
            tree = DUConverter.dummy_tree(word_tokens)
            self.remap_tree_offsets(tree, offset_positions, original_offsets, text)
            leaves: list[str] = []
            self._collect_leaf_texts(tree, leaves)
            if leaves != normalized_edus:
                raise ValueError("Failed to align the provided EDU with the parser output.")
            return {
                "rst": [tree],
            }

        edu_breaks = self._char_spans_to_token_breaks(offsets, spans)

        num_edus = len(edu_breaks)
        relation_placeholder = [[0] * max(num_edus - 1, 0)]
        parsing_placeholder = [[0] * max(num_edus - 1, 0)]

        data = Data(
            input_sentences=[word_tokens],
            edu_breaks=[edu_breaks],
            decoder_input=[[]],
            relation_label=relation_placeholder,
            parsing_breaks=parsing_placeholder,
            golden_metric=[[]],
        )

        predictions = {
            "tokens": [],
            "spans": [],
            "edu_breaks": [],
            "true_spans": [],
            "true_edu_breaks": [],
        }

        batch = self.tokenize(data)
        dataset_index = batch.dataset_index
        if dataset_index is None:
            raise ValueError("Data.dataset_index is None; call `tokenize` before parse.")

        with torch.inference_mode(), self._autocast():
            (
                _,
                _,
                span_batch,
                _,
                _,
            ) = self.model.testing_loss(
                batch.input_sentences,
                batch.sent_breaks,
                batch.entity_ids,
                batch.entity_position_ids,
                batch.edu_breaks,
                batch.relation_label,
                batch.parsing_breaks,
                generate_tree=True,
                use_pred_segmentation=False,
                dataset_index=dataset_index,
            )

        predictions["tokens"] += [self.tokenizer.convert_ids_to_tokens(text) for text in batch.input_sentences]
        if span_batch is None:
            raise RuntimeError("testing_loss returned no spans with generate_tree=True")
        predictions["spans"] += span_batch
        predictions["edu_breaks"] += batch.edu_breaks
        predictions["true_spans"] += batch.golden_metric
        predictions["true_edu_breaks"] += batch.edu_breaks

        tree = DUConverter(predictions, tokenization_type="default").collect(tokens=[word_tokens])[0]
        self.remap_tree_offsets(tree, offset_positions, original_offsets, text)

        leaves: list[str] = []
        self._collect_leaf_texts(tree, leaves)
        if leaves != normalized_edus:
            raise ValueError("The produced segmentation does not match the provided EDUs.")

        return {
            "rst": [tree],
        }

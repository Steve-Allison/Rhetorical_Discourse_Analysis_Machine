from __future__ import annotations

import ast
import builtins
import collections
import json
import logging
import os
import pathlib
import pickle
import sys
import types
from importlib import import_module
from typing import Dict, List, Optional, Sequence, Tuple

import razdel
import torch
from huggingface_hub import hf_hub_download
from huggingface_hub.errors import EntryNotFoundError
from tqdm import tqdm
from transformers import AutoModel, AutoTokenizer, AutoConfig

from isanlp_rst.base_predictor import BasePredictor, resolve_device, str2bool
from isanlp_rst.utils.du_converter import DUConverter
from .data_manager import DataManager  # noqa: F401 - ensure module is registered for pickle
from .src.parser.data import Data
from .src.parser.parsing_net import ParsingNet
from .src.parser.parsing_net_bottom_up import ParsingNetBottomUp


class _RestrictedUnpickler(pickle.Unpickler):
    """Unpickler that only reconstructs inventory leaf types + containers.

    Deliberately does **not** allow arbitrary ``isanlp_rst.*`` callables:
    REDUCE gadgets targeting ``data_manager.collect``,
    ``DataManager.from_pickle``, or ``load_cached`` must be refused.
    ``DataManager`` itself is excluded so ATTR-based ``from_pickle`` gadgets
    cannot be assembled after loading the class.
    """

    _ALLOWED_BUILTINS = frozenset({
        'list', 'dict', 'tuple', 'set', 'frozenset', 'str', 'int', 'float',
        'bool', 'bytes', 'complex', 'NoneType', 'slice', 'object',
    })
    _ALLOWED_COLLECTIONS = frozenset({'defaultdict', 'OrderedDict'})
    _ALLOWED_PATHLIB = frozenset({'Path', 'PosixPath', 'WindowsPath'})
    # Inventory pickles used at inference only need ``ParserInput`` (relation
    # table carrier). Keep the allow-list minimal and explicit.
    _ALLOWED_CLASSES = frozenset({
        ('isanlp_rst.universal_parser.data_manager', 'ParserInput'),
        ('src.universal_parser.data_manager', 'ParserInput'),
    })

    def find_class(self, module: str, name: str):
        if module == 'builtins' and name in self._ALLOWED_BUILTINS:
            if name == 'NoneType':
                return type(None)
            return getattr(builtins, name)
        if module == 'collections' and name in self._ALLOWED_COLLECTIONS:
            return getattr(collections, name)
        if module in ('pathlib', 'pathlib._local') and name in self._ALLOWED_PATHLIB:
            return getattr(pathlib, name)

        if (module, name) in self._ALLOWED_CLASSES:
            return super().find_class(module, name)

        raise pickle.UnpicklingError(
            f'Refused to unpickle {module}.{name} (not on allow-list).'
        )


class PredictorUniRST(BasePredictor):
    _MODULE_ALIASES = {
        'src.universal_parser.data_manager': 'isanlp_rst.universal_parser.data_manager',
        'src.universal_parser.du_converter': 'isanlp_rst.utils.du_converter',
        'src.universal_parser.src.corpus.binary_tree': 'isanlp_rst.universal_parser.src.corpus.binary_tree',
        'src.universal_parser.src.corpus.data': 'isanlp_rst.universal_parser.src.corpus.data',
        'src.universal_parser.src.parser.data': 'isanlp_rst.universal_parser.src.parser.data',
        'src.universal_parser.src.parser.modules': 'isanlp_rst.universal_parser.src.parser.modules',
        'src.universal_parser.src.parser.segmenters': 'isanlp_rst.universal_parser.src.parser.segmenters',
        'src.universal_parser.src.parser.parsing_net': 'isanlp_rst.universal_parser.src.parser.parsing_net',
        'src.universal_parser.src.parser.parsing_net_bottom_up': 'isanlp_rst.universal_parser.src.parser.parsing_net_bottom_up',
        'src.universal_parser.src.parser.metrics': 'isanlp_rst.universal_parser.src.parser.metrics',
        'src.universal_parser.src.parser.training_manager': 'isanlp_rst.universal_parser.src.parser.training_manager',
    }
    _aliases_registered = False

    def __init__(
        self,
        model_dir: Optional[str] = None,
        hf_model_name: Optional[str] = None,
        hf_model_version: Optional[str] = None,
        relinventory: Optional[str] = None,
        relinventory_idx: int = 0,
        device: 'str | torch.device | None' = None,
        cuda_device: 'int | None' = None,
        dtype: 'str | torch.dtype | None' = None,
    ) -> None:
        self._ensure_module_aliases()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        if model_dir is not None and hf_model_name is not None:
            raise ValueError(
                'Pass exactly one of `model_dir` or `hf_model_name`, not both.'
            )

        model_filename = 'best_weights.pt'
        config_filename = 'config.json'

        if model_dir is not None:
            self.mode = 'local'
            self.model_dir = model_dir
            self.hf_model_name = None
            self.hf_model_version = None
            self.model_file = os.path.join(model_dir, model_filename)
            self.config_path = os.path.join(model_dir, config_filename)
        elif hf_model_name is not None:
            self.mode = 'hf'
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
            raise ValueError('Pass either `model_dir` or `hf_model_name`.')

        with open(self.config_path, 'r', encoding='utf8') as f:
            self.config = json.load(f)

        corpora = self.config['data']['corpora']
        if isinstance(corpora, str):
            corpora = ast.literal_eval(corpora)
        self.dataset_names = list(corpora)

        self.relinventory = relinventory
        if self.relinventory is None:
            self.relinventory_idx = relinventory_idx
            if not (0 <= self.relinventory_idx < len(self.dataset_names)):
                raise ValueError(
                    f'relinventory_idx={self.relinventory_idx} is out of bounds for '
                    f'dataset_names ({self.dataset_names}).'
                )
        else:
            key = self.relinventory.strip().lower()
            try:
                self.relinventory_idx = self.dataset_names.index(key)
            except ValueError as exc:
                raise ValueError(
                    f"Unknown relinventory {self.relinventory!r}. "
                    f"Available datasets: {self.dataset_names}."
                ) from exc

        self.data_managers: List[Optional[object]] = []
        self.relation_tables: List[Sequence[str]] = []
        for corpus_name in self.dataset_names:
            # Prefer plain relation_table.txt over unpickling data managers.
            relation_table = self._load_relation_table(corpus_name)
            if relation_table is not None:
                self.data_managers.append(None)
                self.relation_tables.append(relation_table)
                continue
            data_manager = self._load_data_manager(corpus_name)
            self.data_managers.append(data_manager)
            if data_manager is not None:
                self.relation_tables.append(data_manager.relation_table)
            else:
                raise FileNotFoundError(
                    f"Could not find relation inventory for corpus '{corpus_name}'. "
                    'Ensure that relation_table files or data manager pickles are packaged with the model.'
                )

        self._device = resolve_device(device, cuda_device)
        self._dtype = self._resolve_dtype(dtype)

        self._load_model()

    @classmethod
    def _ensure_module_aliases(cls) -> None:
        if cls._aliases_registered:
            return

        cls._aliases_registered = True
        for alias, target in cls._MODULE_ALIASES.items():
            cls._register_alias(alias, target)

    @staticmethod
    def _register_alias(alias: str, target: str) -> None:
        module = import_module(target)
        sys.modules[alias] = module
        parent_name, _, child_name = alias.rpartition('.')
        if parent_name:
            parent = PredictorUniRST._ensure_parent_module(parent_name)
            setattr(parent, child_name, module)

    @staticmethod
    def _ensure_parent_module(name: str):
        if name in sys.modules:
            return sys.modules[name]

        module = types.ModuleType(name)
        sys.modules[name] = module
        parent_name, _, child_name = name.rpartition('.')
        if parent_name:
            parent = PredictorUniRST._ensure_parent_module(parent_name)
            setattr(parent, child_name, module)
        return module

    def _resolve_resource(self, relative_path: str) -> Optional[str]:
        if os.path.isabs(relative_path) and os.path.exists(relative_path):
            return relative_path

        if self.mode == 'local':
            if self.model_dir is None:
                return None
            path = os.path.join(self.model_dir, relative_path)
            if os.path.exists(path):
                return path
            return None

        # HF mode: distinguish "resource not in repo" (silent miss) from
        # network/auth errors (logged but still treated as miss for caller
        # robustness — the caller has fallback paths).
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
        except OSError as exc:
            self.logger.warning(
                'I/O error while resolving %s from HF: %s', relative_path, exc
            )
            return None

    def _corpus_variants(self, corpus_name: str) -> List[str]:
        lower = corpus_name.lower()
        variants = {lower}
        variants.add(lower.replace('.', '_'))
        variants.add(lower.replace('-', '_'))
        if lower.endswith('-tr'):
            variants.add(lower[:-3])
        if lower.endswith('_tr'):
            variants.add(lower[:-3])
        if lower in {'rst-dt-tr', 'rst_dt_tr'}:
            variants.add('rst-dt')
            variants.add('rst_dt')
        if lower in {'gum10-tr', 'gum10_tr'}:
            variants.add('gum10')
            variants.add('gum')
        return [variant for variant in variants if variant]

    def _load_data_manager(self, corpus_name: str):
        candidates = []
        for variant in self._corpus_variants(corpus_name):
            filename = f'data_manager_{variant}.pickle'
            candidates.append(filename)
            candidates.append(os.path.join('data', filename))
            candidates.append(os.path.join('data', 'dms', filename))

        for rel_path in dict.fromkeys(candidates):  # preserve order, drop duplicates
            resolved = self._resolve_resource(rel_path)
            if not resolved:
                continue
            try:
                with open(resolved, 'rb') as f:
                    return _RestrictedUnpickler(f).load()
            except (pickle.UnpicklingError, EOFError, OSError) as exc:
                self.logger.warning(
                    'Skipping unreadable data_manager pickle %s: %s', resolved, exc
                )
                continue
        return None

    def _load_relation_table(self, corpus_name: str) -> Optional[List[str]]:
        lower = corpus_name.lower()
        if lower == 'rst-dt-tr':
            lower = 'rst-dt'
        elif lower == 'gum10-tr':
            lower = 'gum'
        elif lower == 'gum10_tr':
            lower = 'gum'

        filename = f'relation_table_{lower}.txt'
        resolved = self._resolve_resource(filename)
        if not resolved:
            return None

        with open(resolved, 'r', encoding='utf8') as f:
            return [line.strip() for line in f if line.strip()]

    @staticmethod
    def _classifier_count_from_state_dict(state_dict) -> Optional[int]:
        """Count distinct ``label_classifiers.<N>.*`` indices in a state dict.

        Returns ``None`` if the checkpoint has no such keys (older variant,
        DMRST-shaped state dict, etc.) — caller falls back to the configured
        architecture.
        """
        indices = set()
        for key in state_dict.keys():
            if key.startswith('label_classifiers.'):
                parts = key.split('.', 2)
                if len(parts) >= 2 and parts[1].isdigit():
                    indices.add(int(parts[1]))
        return (max(indices) + 1) if indices else None

    def _load_model(self) -> None:
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.config['model']['transformer']['model_name'],
            use_fast=True,
        )
        self.tokenizer.model_max_length = int(1e9)  # The parser relies on a sliding window encoding, so we'll suppress the max_len warning this way.

        transformer_config = AutoConfig.from_pretrained(self.config['model']['transformer']['model_name'])
        transformer = AutoModel.from_config(transformer_config).to(self._device)

        self.tokenizer.add_tokens(['<P>'])
        transformer.resize_token_embeddings(len(self.tokenizer))

        # Load weights ONCE, up front. The classifier count in the trained
        # checkpoint is the source of truth for the architecture — we use it
        # to allocate the right number of `label_classifiers` so the
        # subsequent `load_state_dict` call cannot mismatch.
        state_dict = self._load_torch_weights(self.model_file, self._device)
        ckpt_n_classifiers = self._classifier_count_from_state_dict(state_dict)

        rel_tables = self.relation_tables
        use_union = (
            str2bool(self.config['model'].get('use_union_relations', False))
            and len(rel_tables) > 1
        )

        if use_union:
            union_table: List[str] = []
            label2id: Dict[str, int] = {}
            dataset_masks: List[List[bool]] = []
            label_maps: List[List[int]] = []

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
                'relation_tables': model_relation_tables,
                'relation_vocab': union_table,
                'dataset_masks': dataset_masks,
                'classes_numbers': classes_numbers,
                'dataset2classifier': dataset2classifier,
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
                unique_tables: List[Sequence[str]] = []
                mapping: List[int] = []
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
                        f'Checkpoint has {ckpt_n_classifiers} label classifier(s) '
                        f'but relation-table dedup produced {len(unique_tables)}. '
                        f'The published model assets likely lack the per-corpus '
                        f'data_manager pickles needed to reconstruct distinct '
                        f'relation tables. Affected corpora: {self.dataset_names}.'
                    )
                model_relation_tables = unique_tables
                classes_numbers = [len(t) for t in unique_tables]
                dataset2classifier = mapping
            else:
                raise RuntimeError(
                    f'Checkpoint declares {ckpt_n_classifiers} label classifier(s) '
                    f'but only {n_corpora} corpora are configured '
                    f'({self.dataset_names}). Cannot construct a consistent model.'
                )

            self.label_maps = None
            model_specific_config = {
                'relation_tables': model_relation_tables,
                'classes_numbers': classes_numbers,
                'dataset2classifier': dataset2classifier,
            }

        model_config = {
            'transformer': transformer,
            'emb_dim': int(self.config['model']['transformer']['emb_size']),
            # Inherited ParsingNet kwarg name; holds a torch.device (may be mps).
            'cuda_device': self._device,
        }
        model_config.update(model_specific_config)
        model_config.update(self._get_model_configs())

        parser_type = self.config['model'].get('parser_type', 'top-down')
        model_cls = ParsingNet if parser_type == 'top-down' else ParsingNetBottomUp

        self.model = model_cls(**model_config).to(self._device)
        self.model.load_state_dict(state_dict)
        self.model.eval()

    def _get_model_configs(self) -> dict:
        config: dict = {}

        transformer_cfg = self.config['model'].get('transformer', {})
        segmenter_cfg = self.config['model'].get('segmenter', {})
        model_cfg = self.config.get('model', {})

        if 'normalize' in transformer_cfg:
            config['normalize_embeddings'] = transformer_cfg.get('normalize')

        if 'window_size' in transformer_cfg:
            config['window_size'] = int(transformer_cfg.get('window_size'))

        if 'window_padding' in transformer_cfg:
            config['window_padding'] = int(transformer_cfg.get('window_padding'))

        if 'hidden_size' in model_cfg:
            hidden_size = int(model_cfg.get('hidden_size'))
            config['hidden_size'] = hidden_size
            config['decoder_input_size'] = hidden_size
            config['classifier_input_size'] = hidden_size
            config['classifier_hidden_size'] = hidden_size

        if 'type' in segmenter_cfg:
            config['segmenter_type'] = segmenter_cfg.get('type')

        if 'hidden_dim' in segmenter_cfg:
            config['segmenter_hidden_dim'] = int(segmenter_cfg.get('hidden_dim'))

        if 'lstm_num_layers' in segmenter_cfg:
            config['segmenter_lstm_num_layers'] = segmenter_cfg.get('lstm_num_layers')

        if 'lstm_dropout' in segmenter_cfg:
            config['segmenter_lstm_dropout'] = segmenter_cfg.get('lstm_dropout')

        if 'lstm_bidirectional' in segmenter_cfg:
            config['segmenter_lstm_bidirectional'] = str2bool(segmenter_cfg.get('lstm_bidirectional'))

        if 'use_crf' in segmenter_cfg:
            config['segmenter_use_crf'] = str2bool(segmenter_cfg.get('use_crf'))

        if 'use_log_crf' in segmenter_cfg:
            config['segmenter_use_log_crf'] = str2bool(segmenter_cfg.get('use_log_crf'))

        if 'use_sent_boundaries' in segmenter_cfg:
            config['segmenter_use_sent_boundaries'] = str2bool(segmenter_cfg.get('use_sent_boundaries'))

        if 'separated' in segmenter_cfg:
            config['separated_segmentation'] = str2bool(segmenter_cfg.get('separated'))

        if 'if_edu_start_loss' in segmenter_cfg:
            config['segmenter_if_edu_start_loss'] = str2bool(segmenter_cfg.get('if_edu_start_loss'))

        if 'edu_encoding_kind' in model_cfg:
            config['edu_encoding_kind'] = model_cfg.get('edu_encoding_kind')

        if 'du_encoding_kind' in model_cfg:
            config['du_encoding_kind'] = model_cfg.get('du_encoding_kind')

        if 'rel_classification_kind' in model_cfg:
            config['rel_classification_kind'] = model_cfg.get('rel_classification_kind')

        if 'token_bilstm_hidden' in model_cfg:
            config['token_bilstm_hidden'] = int(model_cfg.get('token_bilstm_hidden'))

        if 'use_discriminator' in model_cfg:
            config['use_discriminator'] = str2bool(model_cfg.get('use_discriminator'))

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

        texts = [' '.join(line).strip() for line in data.input_sentences]
        tokens = self.tokenizer(texts, add_special_tokens=False, return_offsets_mapping=True)
        tokens['entity_ids'] = None
        tokens['entity_position_ids'] = None

        # recount edu_breaks for subwords
        subword_edu_breaks = []
        for doc_word_offsets, doc_subword_offsets, edu_breaks in zip(
            word_offsets, tokens['offset_mapping'], data.edu_breaks, strict=True,
        ):
            subword_edu_breaks.append(
                self._recount_spans(doc_word_offsets, doc_subword_offsets, edu_breaks)
            )

        if self.label_maps:
            if self.relinventory_idx >= len(self.label_maps):
                raise IndexError(
                    f'relinventory_idx={self.relinventory_idx} is out of bounds for relation inventories '
                    f'of size {len(self.label_maps)}'
                )
            mapping = self.label_maps[self.relinventory_idx]
            remapped = [[mapping[idx] for idx in doc] for doc in data.relation_label]
        else:
            remapped = data.relation_label

        return Data(
            input_sentences=tokens['input_ids'],
            entity_ids=tokens['entity_ids'],
            entity_position_ids=tokens['entity_position_ids'],
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

    def get_batches(self, data: Data, size: int) -> List[Data]:
        """Splits a batch into multiple smaller batches of the given size.

        Note: ``data.dataset_index`` must be populated (the predictor's
        ``tokenize`` method does this). Callers passing un-tokenized ``Data``
        with ``dataset_index=None`` will hit a ``ValueError`` here.
        """

        if len(data.input_sentences) < size:
            return [data]

        if data.dataset_index is None:
            raise ValueError(
                'Data.dataset_index is None; call `tokenize` before `get_batches`.'
            )

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
        tokens: Optional[Sequence[str]] = None,
        token_offsets: Optional[Sequence[Tuple[int, int]]] = None,
    ) -> dict:
        """Parse text into an RST tree.

        Args:
            text: Original document text.
            tokens: Optional pre-tokenized words to avoid internal tokenization.
            token_offsets: Optional character offsets for the provided tokens.

        Returns:
            A dictionary with token annotations and the predicted RST tree.
        """

        if text is None:
            raise ValueError('`text` must be provided for parsing.')
        if not isinstance(text, str):
            raise TypeError(
                f'`text` must be a str, got {type(text).__name__}.'
            )
        if not text.strip():
            raise ValueError('`text` must be non-empty (got empty/whitespace-only input).')

        if tokens is None:
            razdel_tokens = list(razdel.tokenize(text))
            word_tokens = [token.text for token in razdel_tokens]
            offsets: List[Tuple[int, int]] = [(token.start, token.stop) for token in razdel_tokens]
        else:
            word_tokens = list(tokens)
            if token_offsets is None:
                offsets = self._guess_token_offsets(text, word_tokens)
            else:
                offsets = list(token_offsets)

        offset_positions, original_offsets = self.build_offset_converter_from_words(text, word_tokens, offsets)

        if len(word_tokens) < 3:
            tree = DUConverter.dummy_tree(word_tokens)
            self.remap_tree_offsets(tree, offset_positions, original_offsets, text)
            return {
                'rst': [tree],
            }

        data = {
            'input_sentences': [word_tokens],
            'edu_breaks': [[]],
            'decoder_input': [[]],
            'relation_label': [[]],
            'parsing_breaks': [[]],
            'golden_metric': [[]],
        }

        input_data = Data(**data)

        predictions = {
            'tokens': [],
            'spans': [],
            'edu_breaks': [],
            'true_spans': [],
            'true_edu_breaks': [],
        }

        batch = self.tokenize(input_data)

        with torch.inference_mode(), self._autocast():
            (
                _,
                _,
                span_batch,
                _,
                predict_edu_breaks,
            ) = self.model.testing_loss(
                batch.input_sentences,
                batch.sent_breaks,
                batch.entity_ids,
                batch.entity_position_ids,
                batch.edu_breaks,
                batch.relation_label,
                batch.parsing_breaks,
                generate_tree=True,
                use_pred_segmentation=True,
                dataset_index=batch.dataset_index,
            )

        predictions['tokens'] += [self.tokenizer.convert_ids_to_tokens(text) for text in batch.input_sentences]
        predictions['spans'] += span_batch
        predictions['edu_breaks'] += predict_edu_breaks
        predictions['true_spans'] += batch.golden_metric
        predictions['true_edu_breaks'] += batch.edu_breaks

        tree = DUConverter(predictions, tokenization_type='default').collect(tokens=data['input_sentences'])[0]
        self.remap_tree_offsets(tree, offset_positions, original_offsets, text)

        return {
            'rst': [tree],
        }

    def parse_from_edus(self, edus: Sequence[str]) -> dict:
        """Parse text using predefined EDU boundaries."""

        normalized_edus = self._validate_edus(edus)
        text, spans = self._compute_edu_char_spans(normalized_edus)

        razdel_tokens = list(razdel.tokenize(text))
        word_tokens = [token.text for token in razdel_tokens]
        offsets = [(token.start, token.stop) for token in razdel_tokens]

        offset_positions, original_offsets = self.build_offset_converter_from_words(text, word_tokens, offsets)

        if not word_tokens:
            raise ValueError('Unable to tokenize text derived from the provided EDUs.')

        if len(normalized_edus) == 1:
            tree = DUConverter.dummy_tree(word_tokens)
            self.remap_tree_offsets(tree, offset_positions, original_offsets, text)
            leaves: List[str] = []
            self._collect_leaf_texts(tree, leaves)
            if leaves != normalized_edus:
                raise ValueError('Failed to align the provided EDU with the parser output.')
            return {
                'rst': [tree],
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
            'tokens': [],
            'spans': [],
            'edu_breaks': [],
            'true_spans': [],
            'true_edu_breaks': [],
        }

        batch = self.tokenize(data)

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
                dataset_index=batch.dataset_index,
            )

        predictions['tokens'] += [
            self.tokenizer.convert_ids_to_tokens(text) for text in batch.input_sentences
        ]
        predictions['spans'] += span_batch
        predictions['edu_breaks'] += batch.edu_breaks
        predictions['true_spans'] += batch.golden_metric
        predictions['true_edu_breaks'] += batch.edu_breaks

        tree = DUConverter(predictions, tokenization_type='default').collect(tokens=[word_tokens])[0]
        self.remap_tree_offsets(tree, offset_positions, original_offsets, text)

        leaves: List[str] = []
        self._collect_leaf_texts(tree, leaves)
        if leaves != normalized_edus:
            raise ValueError('The produced segmentation does not match the provided EDUs.')

        return {
            'rst': [tree],
        }

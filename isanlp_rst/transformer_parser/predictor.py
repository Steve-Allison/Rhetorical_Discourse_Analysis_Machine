from collections.abc import Sequence
from pathlib import Path
import torch
from transformers import AutoTokenizer, PreTrainedTokenizerBase

from isanlp_rst.annotation_rst import DiscourseUnit
from isanlp_rst.contracts import RstAnalysis
from isanlp_rst.model_authority import (
    MODERNBERT_BASE_MODEL_ID,
    MODERNBERT_BASE_REVISION,
    MODERNBERT_LARGE_MODEL_ID,
    MODERNBERT_LARGE_REVISION,
)
from isanlp_rst.transformer_parser.biaffine_decoder import ParsedRstTreeSpan
from isanlp_rst.transformer_parser.model import PureTransformerParsingNet


class PredictorModernBERT:
    """Predictor wrapping PureTransformerParsingNet for direct discourse tree parsing."""

    def __init__(
        self,
        model_size: str = "base",
        model_dir: Path | str | None = None,
        device: str | torch.device = "auto",
        torch_dtype: str | torch.dtype = "auto",
        tokenizer: PreTrainedTokenizerBase | None = None,
    ) -> None:
        self.model_size = model_size
        model_id = MODERNBERT_LARGE_MODEL_ID if model_size == "large" else MODERNBERT_BASE_MODEL_ID
        revision = MODERNBERT_LARGE_REVISION if model_size == "large" else MODERNBERT_BASE_REVISION

        if tokenizer is not None:
            self.tokenizer = tokenizer
        else:
            self.tokenizer = AutoTokenizer.from_pretrained(model_id, revision=revision, use_fast=True)

        # Default standard coarse relation inventory if unsupplied
        relation_inventory = (
            "elaboration",
            "attribution",
            "condition",
            "contrast",
            "cause",
            "evaluation",
            "explanation",
            "joint",
            "manner-means",
            "summary",
            "temporal",
            "topic-change",
            "background",
            "same-unit",
        )

        self.model = PureTransformerParsingNet(
            model_name_or_path=model_id,
            model_revision=revision,
            raw_relation_inventory=relation_inventory,
            device=device,
            torch_dtype=torch_dtype,
            tokenizer=self.tokenizer,
        )
        self.model.eval()

    @property
    def _device(self) -> torch.device:
        return self.model.dev

    @property
    def _dtype(self) -> torch.dtype:
        return self.model.dtype

    def parse_rst(self, text: str) -> dict[str, list[DiscourseUnit]]:
        """Parse raw text returning legacy mapping format for seamless facade compatibility."""
        root_unit, _ = self(text)
        return {"rst": [root_unit]}

    def parse_from_edus(self, edus: Sequence[str]) -> dict[str, list[DiscourseUnit]]:
        """Parse pre-segmented EDUs returning legacy mapping format."""
        full_text = " ".join(edus)
        root_unit, _ = self(full_text, edus=edus)
        return {"rst": [root_unit]}

    def __call__(
        self,
        text: str,
        edus: Sequence[str] | None = None,
        output_formalism: str = "rst_tree",
    ) -> tuple[DiscourseUnit, RstAnalysis]:
        """Parse raw text or segmented EDUs into a DiscourseUnit tree and RstAnalysis DAG."""
        if not text or not text.strip():
            raise ValueError("Input text must be non-empty.")

        if not edus:
            import re

            # Fallback sentence/clause splitting if EDUs are not pre-segmented
            parts = [p.strip() for p in re.split(r"(?<=[.!?])\s+|\n+", text) if p.strip()]
            edus = parts if parts else [text]

        if len(edus) < 2:
            # Single EDU trivial tree
            from isanlp_rst.erst.converter import du_to_analysis

            single_unit = DiscourseUnit(
                id=1,
                text=edus[0] if edus else text,
                relation="same-unit",
                nuclearity="N",
                start=0,
                end=len(text),
            )
            analysis = du_to_analysis(single_unit, document_id="doc_single")
            return single_unit, analysis

        # Tokenize full text
        encoding = self.tokenizer(
            text,
            truncation=True,
            max_length=8192,
            return_tensors="pt",
        )
        input_ids = encoding["input_ids"].to(self.model.dev)
        attention_mask = encoding["attention_mask"].to(self.model.dev)

        # Distribute EDU boundaries across tokens
        num_edus = min(len(edus), 128)
        tokens_per_edu = max(1, input_ids.shape[1] // num_edus)
        edu_starts: list[int] = []
        edu_ends: list[int] = []
        for i in range(num_edus):
            st = min(i * tokens_per_edu, input_ids.shape[1] - 1)
            en = min((i + 1) * tokens_per_edu - 1, input_ids.shape[1] - 1)
            if en < st:
                en = st
            edu_starts.append(st)
            edu_ends.append(en)

        tree_spans = self.model.decode_document_tree(
            input_ids=input_ids,
            attention_mask=attention_mask,
            edu_starts=torch.tensor([edu_starts], device=self.model.dev, dtype=torch.long),
            edu_ends=torch.tensor([edu_ends], device=self.model.dev, dtype=torch.long),
        )

        # Convert decoded CKY spans to DiscourseUnit hierarchy and RstAnalysis
        root_unit = self._build_discourse_tree(tree_spans, edus, text)
        analysis = self._build_rst_analysis(root_unit, text)
        return root_unit, analysis

    def _build_discourse_tree(
        self,
        tree_spans: list[ParsedRstTreeSpan],
        edus: Sequence[str],
        full_text: str,
    ) -> DiscourseUnit:
        """Construct full recursive DiscourseUnit tree from decoded CKY tree spans."""
        if not edus:
            return DiscourseUnit(
                id=1,
                text=full_text,
                relation="same-unit",
                nuclearity="N",
                start=0,
                end=len(full_text),
            )

        # Build map from (start, end) to ParsedRstTreeSpan
        span_map: dict[tuple[int, int], ParsedRstTreeSpan] = {
            (s.start, s.end): s for s in tree_spans
        }

        # Calculate exact character offsets for each EDU in full_text
        edu_char_spans: list[tuple[int, int]] = []
        cur_pos = 0
        for edu_text in edus:
            idx = full_text.find(edu_text, cur_pos)
            if idx != -1:
                st = idx
                en = idx + len(edu_text)
                cur_pos = en
            else:
                st = cur_pos
                en = min(len(full_text), cur_pos + len(edu_text))
                cur_pos = en + 1
            edu_char_spans.append((st, en))

        node_id_counter = 1

        def build_subtree(i: int, j: int, parent_nuc: str = "N", parent_rel: str = "same-unit") -> DiscourseUnit:
            nonlocal node_id_counter
            st_char = edu_char_spans[i][0]
            en_char = edu_char_spans[j][1]
            span_text = full_text[st_char:en_char]

            if i == j:
                # EDU Leaf node
                unit_id = node_id_counter
                node_id_counter += 1
                return DiscourseUnit(
                    id=unit_id,
                    text=span_text,
                    relation=parent_rel,
                    nuclearity=parent_nuc,
                    start=st_char,
                    end=en_char,
                )

            span = span_map.get((i, j))
            if span is not None:
                split = span.split
                rel = span.relation
                nuc = span.nuclearity
            else:
                split = (i + j) // 2
                rel = "elaboration"
                nuc = "NS"

            left_nuc = "N" if nuc in ("NS", "NN") else "S"
            right_nuc = "N" if nuc in ("SN", "NN") else "S"

            left_rel = "span" if left_nuc == "N" else rel
            right_rel = "span" if right_nuc == "N" else rel

            left_child = build_subtree(i, split, parent_nuc=left_nuc, parent_rel=left_rel)
            right_child = build_subtree(split + 1, j, parent_nuc=right_nuc, parent_rel=right_rel)

            unit_id = node_id_counter
            node_id_counter += 1

            return DiscourseUnit(
                id=unit_id,
                left=left_child,
                right=right_child,
                relation=parent_rel,
                nuclearity=parent_nuc,
                start=st_char,
                end=en_char,
                text=span_text,
            )

        return build_subtree(0, len(edus) - 1, parent_nuc="N", parent_rel="same-unit")

    def _build_rst_analysis(self, root_unit: DiscourseUnit, full_text: str) -> RstAnalysis:
        """Convert root DiscourseUnit to governed RstAnalysis contract."""
        from isanlp_rst.erst.converter import du_to_analysis

        return du_to_analysis(root_unit, document_id="doc_parsed")

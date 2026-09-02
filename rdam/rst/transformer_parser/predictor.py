from collections.abc import Sequence
from dataclasses import dataclass
import json
from pathlib import Path
import re
from safetensors.torch import load_model as load_safetensors_model
import torch
from transformers import AutoConfig, AutoTokenizer, PreTrainedTokenizerBase

from rdam.rst.annotation_rst import DiscourseUnit
from rdam.rst.contracts import DocumentToken, Edu, RstAnalysis, TextSpan
from rdam.rst.model_authority import (
    MODERNBERT_BASE_MODEL_ID,
    MODERNBERT_BASE_REVISION,
    MODERNBERT_LARGE_MODEL_ID,
    MODERNBERT_LARGE_REVISION,
)
from rdam.rst.model_loading.release import (
    ModelFile,
    ModelReleaseError,
    ValidatedModelRelease,
    sha256_file,
)
from rdam.rst.transformer_parser.biaffine_decoder import (
    ParsedRstTreeEvidence,
    ParsedRstTreeSpan,
)
from rdam.rst.transformer_parser.model import PureTransformerParsingNet


class ParserInputLimitError(ValueError):
    """The exact inference substrate exceeds a declared parser limit."""


@dataclass(frozen=True, slots=True)
class PredictorAnalysisTrace:
    """Bounded exact substrate and selected-decision evidence from inference."""

    root_unit: DiscourseUnit
    analysis: RstAnalysis
    tokens: tuple[DocumentToken, ...]
    edus: tuple[Edu, ...]
    sentence_boundaries: tuple[TextSpan, ...]
    paragraph_boundaries: tuple[TextSpan, ...]
    structure_decisions: tuple[ParsedRstTreeEvidence, ...]
    segmentation_source: str
    relation_inventory: tuple[str, ...]


class PredictorModernBERT:
    """Predictor wrapping PureTransformerParsingNet for direct discourse tree parsing."""

    def __init__(
        self,
        model_size: str = "base",
        model_dir: Path | str | None = None,
        device: str | torch.device = "auto",
        torch_dtype: str | torch.dtype = "auto",
        tokenizer: PreTrainedTokenizerBase | None = None,
        validated_release: ValidatedModelRelease | None = None,
    ) -> None:
        self.model_size = model_size
        model_id = MODERNBERT_LARGE_MODEL_ID if model_size == "large" else MODERNBERT_BASE_MODEL_ID
        revision = MODERNBERT_LARGE_REVISION if model_size == "large" else MODERNBERT_BASE_REVISION
        resolved_model = str(Path(model_dir).resolve()) if model_dir is not None else model_id
        resolved_revision = None if model_dir is not None else revision
        local_files_only = model_dir is not None
        self.model_dir = Path(model_dir).resolve() if model_dir is not None else None
        self.loaded_release_files: tuple[ModelFile, ...] = ()
        if validated_release is not None:
            if self.model_dir is None or self.model_dir != validated_release.path:
                raise ModelReleaseError("validated ModernBERT release does not match the runtime model directory")

        if tokenizer is not None:
            self.tokenizer = tokenizer
        else:
            self.tokenizer = AutoTokenizer.from_pretrained(
                resolved_model,
                revision=resolved_revision,
                use_fast=True,
                local_files_only=local_files_only,
            )
        if not getattr(self.tokenizer, "is_fast", False):
            raise ModelReleaseError("ModernBERT production release requires a fast tokenizer")

        relation_inventory = (
            _load_relation_inventory(validated_release)
            if validated_release is not None
            else _DEFAULT_RELATION_INVENTORY
        )
        encoder_config = (
            AutoConfig.from_pretrained(
                resolved_model,
                local_files_only=True,
            )
            if validated_release is not None
            else None
        )

        self.model = PureTransformerParsingNet(
            model_name_or_path=resolved_model,
            model_revision=resolved_revision,
            raw_relation_inventory=relation_inventory,
            device=device,
            torch_dtype=torch_dtype,
            tokenizer=self.tokenizer,
            local_files_only=local_files_only,
            encoder_config=encoder_config,
        )
        if validated_release is not None:
            parser_state = validated_release.one_file_for_role("parser_state")
            try:
                missing, unexpected = load_safetensors_model(
                    self.model,
                    validated_release.path / parser_state.path,
                    strict=True,
                    device=str(self.model.dev),
                )
            except Exception as exc:
                raise ModelReleaseError("ModernBERT parser state failed strict safetensors loading") from exc
            if missing or unexpected:
                raise ModelReleaseError(
                    f"strict ModernBERT parser-state load returned missing={missing}, unexpected={unexpected}"
                )
            self.loaded_release_files = _verify_runtime_files(validated_release)
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
        resolved = _locate_presegmented_edus(full_text, edus)
        root_unit, _ = self(full_text, edus=resolved)
        return {"rst": [root_unit]}

    def __call__(
        self,
        text: str,
        edus: Sequence[Edu] | None = None,
        output_formalism: str = "rst_tree",
    ) -> tuple[DiscourseUnit, RstAnalysis]:
        """Parse raw text or segmented EDUs into a DiscourseUnit tree and RstAnalysis DAG."""
        if not text or not text.strip():
            raise ValueError("Input text must be non-empty.")

        trace = self.analyse_with_evidence(text, edus=edus)
        return trace.root_unit, trace.analysis

    def analyse_with_evidence(
        self,
        text: str,
        *,
        edus: Sequence[Edu] | None = None,
        sentence_boundaries: Sequence[TextSpan] = (),
        paragraph_boundaries: Sequence[TextSpan] = (),
        segmentation_source: str | None = None,
    ) -> PredictorAnalysisTrace:
        """Build an exact, non-truncated inference substrate and selected trace."""

        if not text or not text.strip():
            raise ValueError("Input text must be non-empty.")
        if not getattr(self.tokenizer, "is_fast", False):
            raise ValueError("production parsing requires a fast tokenizer with native offsets")

        resolved_edus = tuple(edus) if edus else _segment_text_exact(text)
        _validate_edus(text, resolved_edus)
        if len(resolved_edus) > 512:
            raise ParserInputLimitError("exact inference substrate exceeds the 512-EDU parser capacity")

        encoding = self.tokenizer(
            text,
            truncation=False,
            return_offsets_mapping=True,
            return_special_tokens_mask=True,
            return_tensors="pt",
        )
        input_ids = encoding["input_ids"]
        attention_mask = encoding["attention_mask"]
        offset_mapping = encoding["offset_mapping"][0].tolist()
        special_tokens_mask = encoding["special_tokens_mask"][0].tolist()
        context_limit = _context_limit(self.model, self.tokenizer)
        if input_ids.shape[1] > context_limit:
            raise ParserInputLimitError(
                f"exact tokenizer output has {input_ids.shape[1]} tokens; limit is {context_limit}"
            )

        resolved_sentences = tuple(sentence_boundaries) or tuple(
            TextSpan(start=edu.start, end=edu.end, text=edu.text) for edu in resolved_edus
        )
        resolved_paragraphs = tuple(paragraph_boundaries) or _paragraph_boundaries(text)
        tokens: list[DocumentToken] = []
        model_index_by_token_id: dict[int, int] = {}
        for model_index, ((start, end), is_special) in enumerate(zip(offset_mapping, special_tokens_mask, strict=True)):
            start, end = _trim_token_offset(text, start, end)
            if is_special or end <= start:
                continue
            token_id = len(tokens)
            tokens.append(
                DocumentToken(
                    token_id=token_id,
                    text=text[start:end],
                    start=start,
                    end=end,
                    sentence_id=_containing_boundary(start, end, resolved_sentences),
                    paragraph_id=_containing_boundary(start, end, resolved_paragraphs),
                )
            )
            model_index_by_token_id[token_id] = model_index
        _validate_token_coverage(text, tokens)

        aligned_edus: list[Edu] = []
        edu_starts: list[int] = []
        edu_ends: list[int] = []
        for order, edu in enumerate(resolved_edus, start=1):
            token_ids = tuple(token.token_id for token in tokens if edu.start <= token.start and token.end <= edu.end)
            if not token_ids:
                raise ValueError(f"EDU {order} has no exact tokenizer-aligned tokens")
            if any(
                token.start < edu.end and token.end > edu.start and token.token_id not in token_ids for token in tokens
            ):
                raise ValueError(f"tokenizer token crosses EDU {order} boundary")
            aligned_edus.append(
                Edu(
                    edu_id=order,
                    text=text[edu.start : edu.end],
                    start=edu.start,
                    end=edu.end,
                    token_ids=token_ids,
                    source_anchors=edu.source_anchors,
                )
            )
            edu_starts.append(model_index_by_token_id[token_ids[0]])
            edu_ends.append(model_index_by_token_id[token_ids[-1]])

        if len(aligned_edus) == 1:
            from rdam.rst.erst.converter import du_to_analysis

            only = aligned_edus[0]
            root_unit = DiscourseUnit(
                id=1,
                text=only.text,
                relation="same-unit",
                nuclearity="N",
                start=only.start,
                end=only.end,
            )
            analysis = du_to_analysis(root_unit, document_id="doc_single")
            structure_decisions: tuple[ParsedRstTreeEvidence, ...] = ()
        else:
            decoded = self.model.decode_document_tree_with_evidence(
                input_ids=input_ids.to(self.model.dev),
                attention_mask=attention_mask.to(self.model.dev),
                edu_starts=torch.tensor([edu_starts], device=self.model.dev, dtype=torch.long),
                edu_ends=torch.tensor([edu_ends], device=self.model.dev, dtype=torch.long),
            )
            tree_spans = [item.span for item in decoded]
            root_unit = self._build_discourse_tree(tree_spans, aligned_edus, text)
            analysis = self._build_rst_analysis(root_unit, text)
            structure_decisions = tuple(decoded)

        return PredictorAnalysisTrace(
            root_unit=root_unit,
            analysis=analysis,
            tokens=tuple(tokens),
            edus=tuple(aligned_edus),
            sentence_boundaries=resolved_sentences,
            paragraph_boundaries=resolved_paragraphs,
            structure_decisions=structure_decisions,
            segmentation_source=segmentation_source
            or ("presegmented" if edus is not None else "deterministic_sentence_boundary_v1"),
            relation_inventory=tuple(self.model.raw_relation_inventory),
        )

    def _build_discourse_tree(
        self,
        tree_spans: list[ParsedRstTreeSpan],
        edus: Sequence[Edu],
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
        span_map: dict[tuple[int, int], ParsedRstTreeSpan] = {(s.start, s.end): s for s in tree_spans}

        node_id_counter = 1

        def build_subtree(i: int, j: int, parent_nuc: str = "N", parent_rel: str = "same-unit") -> DiscourseUnit:
            nonlocal node_id_counter
            st_char = edus[i].start
            en_char = edus[j].end
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
            if span is None:
                raise ValueError(f"decoder omitted required constituent span {(i, j)}")
            split = span.split
            rel = span.relation
            nuc = span.nuclearity

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
        from rdam.rst.erst.converter import du_to_analysis

        return du_to_analysis(root_unit, document_id="doc_parsed")


def _segment_text_exact(text: str) -> tuple[Edu, ...]:
    boundaries = [0]
    boundaries.extend(match.end() for match in re.finditer(r"(?<=[.!?])\s+|\n+", text))
    boundaries.append(len(text))
    edus: list[Edu] = []
    for start, end in zip(boundaries, boundaries[1:], strict=False):
        raw = text[start:end]
        stripped = raw.strip()
        if not stripped:
            continue
        leading = len(raw) - len(raw.lstrip())
        trailing = len(raw) - len(raw.rstrip())
        resolved_start = start + leading
        resolved_end = end - trailing
        edus.append(
            Edu(
                edu_id=len(edus) + 1,
                text=text[resolved_start:resolved_end],
                start=resolved_start,
                end=resolved_end,
            )
        )
    if not edus:
        raise ValueError("non-empty input produced no exact EDUs")
    return tuple(edus)


def _locate_presegmented_edus(text: str, edus: Sequence[str]) -> tuple[Edu, ...]:
    result: list[Edu] = []
    cursor = 0
    for index, value in enumerate(edus, start=1):
        start = text.find(value, cursor)
        if start < 0:
            raise ValueError(f"presegmented EDU {index} cannot be located exactly")
        end = start + len(value)
        result.append(Edu(edu_id=index, text=value, start=start, end=end))
        cursor = end
    return tuple(result)


def _validate_edus(text: str, edus: Sequence[Edu]) -> None:
    previous_end = 0
    for index, edu in enumerate(edus, start=1):
        if edu.start < previous_end or edu.end > len(text) or edu.end <= edu.start:
            raise ValueError(f"EDU {index} has invalid or overlapping exact coordinates")
        if text[edu.start : edu.end] != edu.text:
            raise ValueError(f"EDU {index} text does not match its exact coordinates")
        previous_end = edu.end


def _context_limit(model: PureTransformerParsingNet, tokenizer: PreTrainedTokenizerBase) -> int:
    model_limit = getattr(model.encoder.config, "max_position_embeddings", None)
    tokenizer_limit = getattr(tokenizer, "model_max_length", None)
    valid = [
        value for value in (model_limit, tokenizer_limit, 8192) if isinstance(value, int) and 1 < value < 1_000_000
    ]
    return min(valid)


def _paragraph_boundaries(text: str) -> tuple[TextSpan, ...]:
    result: list[TextSpan] = []
    for match in re.finditer(r"\S(?:[^\r\n]|\r(?!\n))*", text):
        end = match.end()
        while end > match.start() and text[end - 1].isspace():
            end -= 1
        if end > match.start():
            result.append(TextSpan(start=match.start(), end=end, text=text[match.start() : end]))
    return tuple(result) or (TextSpan(start=0, end=len(text), text=text),)


def _containing_boundary(start: int, end: int, boundaries: Sequence[TextSpan]) -> int:
    for index, boundary in enumerate(boundaries):
        if boundary.start <= start and end <= boundary.end:
            return index
    raise ValueError(f"token range {(start, end)} is outside declared structural boundaries")


def _validate_token_coverage(text: str, tokens: Sequence[DocumentToken]) -> None:
    covered = [False] * len(text)
    for token in tokens:
        if text[token.start : token.end] != token.text:
            raise ValueError(f"token {token.token_id} text does not match tokenizer offsets")
        for index in range(token.start, token.end):
            covered[index] = True
    missing = [index for index, character in enumerate(text) if not character.isspace() and not covered[index]]
    if missing:
        raise ValueError(f"tokenizer offsets omit non-whitespace input at character {missing[0]}")


def _trim_token_offset(text: str, start: int, end: int) -> tuple[int, int]:
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    return start, end


_DEFAULT_RELATION_INVENTORY = (
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


def _load_relation_inventory(release: ValidatedModelRelease) -> tuple[str, ...]:
    record = release.one_file_for_role("relation_inventory")
    try:
        payload = json.loads((release.path / record.path).read_bytes())
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ModelReleaseError("ModernBERT relation inventory is not valid JSON") from exc
    if (
        not isinstance(payload, list)
        or not payload
        or any(not isinstance(item, str) or not item for item in payload)
        or len(payload) != len(set(payload))
    ):
        raise ModelReleaseError("ModernBERT relation inventory must be a non-empty unique string array")
    return tuple(payload)


def _verify_runtime_files(release: ValidatedModelRelease) -> tuple[ModelFile, ...]:
    for record in release.manifest.files:
        path = release.path / record.path
        if (
            not path.is_file()
            or path.is_symlink()
            or path.stat().st_size != record.size_bytes
            or sha256_file(path) != record.sha256
        ):
            raise ModelReleaseError(f"ModernBERT runtime member changed after release validation: {record.path}")
    return release.manifest.files


__all__ = [
    "ParserInputLimitError",
    "PredictorAnalysisTrace",
    "PredictorModernBERT",
]

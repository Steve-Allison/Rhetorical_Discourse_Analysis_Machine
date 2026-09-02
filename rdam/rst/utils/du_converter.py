from collections.abc import Mapping, Sequence
from typing import Any

from rdam.rst.annotation_rst import DiscourseUnit


class DUConverter:
    __slots__ = ("du_id", "predictions", "tokenization_type")

    du_id: int
    predictions: Mapping[str, Any]
    tokenization_type: str

    def __init__(self, predictions: Mapping[str, Any], tokenization_type: str = "default") -> None:
        self.predictions = predictions
        assert tokenization_type in ("default", "rubert")
        self.tokenization_type = tokenization_type

        self.du_id = 0

    def collect(self, tokens: Sequence[Sequence[str]] | None = None) -> list[DiscourseUnit]:
        """Takes the model outputs and converts them into isanlp binary trees.

        Returns:
            List of the predictions as isanlp.DiscourseUnit objects.
        """
        data: list[DiscourseUnit] = []
        token_docs = self.predictions["tokens"]
        edu_docs = self.predictions["edu_breaks"]
        span_docs = self.predictions["spans"]
        for i, (doc_tokens, edu_breaks, span_batch) in enumerate(zip(token_docs, edu_docs, span_docs, strict=True)):
            gold_tokens = tokens[i] if tokens else None

            edus = self._lists_to_isanlp_format(
                tokens=doc_tokens,
                edu_breaks=edu_breaks,
                gold_tokens=gold_tokens,
            )
            if len(edus) == 1:
                data.append(edus[0])
                continue

            self.du_id = len(edus)
            rels = self._tree_string_to_list(span_batch[0])
            tree = self.construct_tree(0, edus, rels)
            data.append(tree)

        return data

    @staticmethod
    def fix_segmented_strings(predicted_segments, gold_tokens):
        fixed_segments = []
        start_token = 0

        for segment in predicted_segments:
            segment_len = len("".join(segment.split()))
            if segment_len == 0:
                fixed_segments.append("")
                continue

            n = 0
            accumulated = 0
            while start_token + n < len(gold_tokens) and accumulated < segment_len:
                accumulated += len(gold_tokens[start_token + n])
                n += 1

            fixed_segment = " ".join(gold_tokens[start_token : start_token + n])
            fixed_segments.append(fixed_segment.strip())
            start_token += n

        return fixed_segments

    def _lists_to_isanlp_format(self, tokens, edu_breaks, gold_tokens=None):
        """
        Produces EDUs in isanlp format from the model predictions.

        Args:
            tokens: List of tokens for a document.
            edu_breaks: List of tokens positions with predicted EDU breaks.

        Returns:
            List of the EDUs in isanlp format.
        """

        prev_break = 0
        prev_chr_end = 0
        edus = []
        for i, brk in enumerate(edu_breaks):
            match self.tokenization_type:
                case "default":
                    text = "".join(tokens[prev_break : brk + 1]).replace("▁", " ").strip()
                case "rubert":
                    text = " ".join(tokens[prev_break : brk + 1]).replace(" ##", "")
                case _:
                    raise ValueError(f"Unknown tokenization_type: {self.tokenization_type!r}")

            edu = DiscourseUnit(id=i, text=text, start=prev_chr_end, relation="elementary")
            edu.end = prev_chr_end + len(text)
            prev_chr_end = edu.end + 1
            prev_break = brk + 1
            edus.append(edu)

        if gold_tokens:
            pred_texts = [edu.text for edu in edus]
            gold_texts = self.fix_segmented_strings(pred_texts, gold_tokens)
            fixed_edus = []
            for edu, fixed_text in zip(edus, gold_texts, strict=True):
                edu.text = fixed_text
                fixed_edus.append(edu)
            edus = fixed_edus

        return edus

    @staticmethod
    def _tree_string_to_list(description):
        """
        Parses the tree predictions given in a string format.

        Args:
            description: Tree description as a string.

        Returns:
            List of tuples describing constituents.
        """
        rels = []
        for rel in description.split(" "):
            left, right = rel.split(",")
            left_start, left_label, left_end = left[1:].split(":")
            if ";prob=" in left_label:
                left_label, _ = left_label.split(";prob=", 1)
            entropy = 0.0
            if ";entropy=" in left_label:
                left_label, entropy_str = left_label.split(";entropy=")
                try:
                    entropy = float(entropy_str)
                except ValueError:
                    entropy = 0.0
            right_start, right_label, right_end = right[:-1].split(":")
            nuclearity = left_label[0] + right_label[0]
            relation = left_label.split("=")[1] if nuclearity == "SN" else right_label.split("=")[1]
            rels.append(
                (
                    int(left_start) - 1,
                    int(left_end) - 1,
                    relation,
                    nuclearity,
                    int(right_start) - 1,
                    int(right_end) - 1,
                    entropy,
                )
            )
        return rels

    @staticmethod
    def _get_child(
        start: int,
        end: int,
        rels: Sequence[tuple[Any, ...]],
        span_map: dict[tuple[int, int], int] | None = None,
    ) -> int:
        """Selects the discourse unit description for given constituent.

        Args:
            start: DU start position.
            end: DU end position.
            rels: List of tuples describing all the RST tree constituents.
            span_map: Optional precomputed mapping of (start, end) -> rel index.

        Returns:
            Index of the given DU in the rels list.
        """
        if span_map is not None:
            idx = span_map.get((start, end))
            if idx is not None:
                return idx
            raise ValueError(f"No discourse unit found for span ({start}, {end}).")

        for idx, rel in enumerate(rels):
            left_start, _, _, _, _, right_end, *_ = rel
            if left_start == start and right_end == end:
                return idx
        raise ValueError(f"No discourse unit found for span ({start}, {end}).")

    def construct_tree(
        self,
        root: int,
        edus: Sequence[DiscourseUnit],
        rels: Sequence[tuple[Any, ...]],
        span_map: dict[tuple[int, int], int] | None = None,
    ) -> DiscourseUnit:
        """Constructs the DiscourseUnit binary tree.

        Args:
            root: Index of the root relation in the rels list.
            edus: List of EDUs as DiscourseUnit objects.
            rels: List of tuples describing all the RST tree constituents.
            span_map: Optional precomputed mapping of (start, end) -> rel index.

        Returns:
            Binary DiscourseUnit RST tree.
        """
        if span_map is None:
            span_map = {(rel[0], rel[5]): idx for idx, rel in enumerate(rels)}

        left_start, left_end, relation, nuclearity, right_start, right_end, entropy = rels[root]

        if left_start == left_end:
            left = edus[left_start]
        else:
            left_root = self._get_child(left_start, left_end, rels, span_map=span_map)
            left = self.construct_tree(left_root, edus, rels, span_map=span_map)

        if right_start == right_end:
            right = edus[right_start]
        else:
            right_root = self._get_child(right_start, right_end, rels, span_map=span_map)
            right = self.construct_tree(right_root, edus, rels, span_map=span_map)

        self.du_id += 1
        du = DiscourseUnit(
            id=self.du_id,
            left=left,
            right=right,
            entropy=entropy,
            relation=relation,
            nuclearity=nuclearity,
            start=left.start,
            end=right.end,
            text=left.text + " " + right.text,
        )
        return du

    @staticmethod
    def dummy_tree(tokens):
        return DiscourseUnit(id=0, text=" ".join(tokens), relation="elementary", start=0, end=len(" ".join(tokens)))

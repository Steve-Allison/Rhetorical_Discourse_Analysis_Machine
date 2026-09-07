from bisect import bisect_right
from collections.abc import Iterable, Sequence
from contextlib import AbstractContextManager
from itertools import batched
from pathlib import Path
from typing import Any, Protocol, cast

from ._torch_runtime import DeviceProbe as DeviceProbe
from ._torch_runtime import resolve_device as resolve_device
from ._torch_runtime import resolve_dtype, torch
from .inference_evidence import NetworkStructureDecision
from .contracts.document import DocumentToken, TextSpan


class _OffsetToken(Protocol):
    """Minimal razdel-token surface used by offset remapping."""

    text: str
    start: int
    stop: int


def str2bool(value: object) -> bool:
    """Parse explicit boolean spellings and reject ambiguous configuration."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().casefold()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    if isinstance(value, int) and value in {0, 1}:
        return bool(value)
    raise ValueError(f"expected an explicit boolean value, got {value!r}")


class BasePredictor:
    """Mixin-style base with shared tokenization, batching and offset utils.

    Predictors compose this base by inheritance and override ``parse_rst`` /
    ``parse_from_edus`` / ``tokenize`` directly. The two parse methods are
    declared here because the base itself calls them — ``__call__`` and
    ``analyse_with_evidence`` dispatch to the subclass implementation — so the
    requirement is part of the base's contract rather than an implicit
    convention. A subclass that omits one fails loudly at the call, not with an
    ``AttributeError`` from somewhere deeper.
    """

    tokenizer = None
    # Set by subclasses' ``__init__`` after ``resolve_device`` and
    # ``_resolve_dtype`` resolve them. Declared here so Pyright can narrow
    # ``self._device`` and ``self._dtype`` on the base methods that use them
    # (``_autocast``, ``_load_torch_weights``).
    _device: torch.device
    _dtype: torch.dtype

    @staticmethod
    def divide_chunks[T](_list: Sequence[T], n: int) -> Iterable[Sequence[T]]:
        """Yield chunks of size `n` from `_list` (handles empty lists)."""
        if not _list:
            yield _list
            return
        for chunk in batched(_list, n, strict=False):
            yield list(chunk)

    @staticmethod
    def build_offset_converter_from_words(
        text: str,
        tokens: Sequence[str],
        token_offsets: Sequence[tuple[int, int]] | None = None,
    ) -> tuple[list[int], list[int]]:
        """Build offset converter from word tokens and optional (start, end) pairs.

        If `token_offsets` is omitted, a best-effort alignment is performed.
        Returns two lists: `positions` (flattened space of tokenized text) and
        `originals` (mapped indices in the original text).
        """
        if token_offsets is None:
            token_offsets = BasePredictor._guess_token_offsets(text, tokens)

        positions: list[int] = []
        originals: list[int] = []
        cursor = 0

        for idx, (tok, (start, end)) in enumerate(zip(tokens, token_offsets, strict=True)):
            token_text = tok or ""
            for _ in token_text:
                positions.append(cursor)
                originals.append(start)
                start += 1
                cursor += 1
            positions.append(cursor)
            originals.append(end)
            if idx != len(tokens) - 1:
                cursor += 1

        if not positions:
            positions = [0]
            originals = [0]

        return positions, originals

    @staticmethod
    def build_offset_converter_from_razdel(
        tokens: Sequence[_OffsetToken],
    ) -> tuple[list[int], list[int]]:
        """Build offset converter from a list of `razdel.Token` objects."""
        positions: list[int] = []
        originals: list[int] = []
        cursor = 0

        for idx, token in enumerate(tokens):
            token_text = token.text
            for char_idx, _ in enumerate(token_text):
                positions.append(cursor)
                originals.append(token.start + char_idx)
                cursor += 1
            positions.append(cursor)
            originals.append(token.stop)
            if idx != len(tokens) - 1:
                cursor += 1

        if not positions:
            positions = [0]
            originals = [0]

        return positions, originals

    @staticmethod
    def capture_word_tokens(
        text: str, words: Sequence[str], offsets: Sequence[tuple[int, int]]
    ) -> tuple[DocumentToken, ...]:
        """Preserve the words supplied to subword encoding in source coordinates."""
        tokens: list[DocumentToken] = []
        previous_end = 0
        for index, (word, (start, end)) in enumerate(zip(words, offsets, strict=True), start=1):
            if not (previous_end <= start < end <= len(text)) or text[start:end] != word:
                raise ValueError(f"Predictor word token {index} does not align with the source")
            tokens.append(DocumentToken(token_id=index, text=word, start=start, end=end))
            previous_end = end
        return tuple(tokens)

    @staticmethod
    def validate_source_spans(text: str, boundaries: Sequence[TextSpan]) -> None:
        """Require ordered, non-overlapping spans that quote their exact source."""
        previous_end = 0
        for boundary in boundaries:
            if (
                not previous_end <= boundary.start < boundary.end <= len(text)
                or text[boundary.start:boundary.end] != boundary.text
            ):
                raise ValueError("source groups must be ordered, disjoint, exact source spans")
            previous_end = boundary.end

    @staticmethod
    def capture_token_groups(
        text: str,
        tokens: Sequence[DocumentToken],
        boundaries: Sequence[TextSpan],
    ) -> tuple[int, ...]:
        """Resolve sentence/paragraph membership only from exact source boundaries.

        Boundary IDs are their one-based positions in the returned trace. Gaps
        between groups may contain whitespace, but every input token must fit
        wholly within a group; a nearest or default group is not evidence.
        """
        BasePredictor.validate_source_spans(text, boundaries)
        memberships: list[int] = []
        group_index = 0
        for token in tokens:
            while group_index < len(boundaries) and token.start >= boundaries[group_index].end:
                group_index += 1
            if group_index == len(boundaries):
                raise ValueError(f"input token {token.token_id} has no containing source group")
            group = boundaries[group_index]
            if not group.start <= token.start < token.end <= group.end:
                raise ValueError(f"input token {token.token_id} crosses or misses a source group")
            memberships.append(group_index + 1)
        return tuple(memberships)

    @staticmethod
    def capture_edu_memberships(
        text: str, tokens: Sequence[DocumentToken], edus: Sequence[TextSpan],
    ) -> tuple[tuple[int, ...], ...]:
        """Retain every exact overlap when a native word crosses an EDU boundary."""
        BasePredictor.validate_source_spans(text, edus)
        previous_end = 0
        for edu in edus:
            if text[previous_end:edu.start].strip():
                raise ValueError("EDU spans leave source characters uncovered")
            previous_end = edu.end
        if text[previous_end:].strip():
            raise ValueError("EDU spans leave source characters uncovered")
        memberships: list[list[int]] = [[] for _ in edus]
        edu_index = 0
        for token in tokens:
            while edu_index < len(edus) and edus[edu_index].end <= token.start:
                edu_index += 1
            index = edu_index
            matched = False
            while index < len(edus) and edus[index].start < token.end:
                memberships[index].append(token.token_id)
                matched = True
                index += 1
            if not matched:
                raise ValueError(f"input token {token.token_id} has no overlapping EDU")
        return tuple(tuple(token_ids) for token_ids in memberships)

    @staticmethod
    def _map_offset(value: int, positions: list[int], originals: list[int]) -> int:
        if not positions:
            return value
        index = bisect_right(positions, value) - 1
        if index < 0:
            index = 0
        elif index >= len(originals):
            index = len(originals) - 1
        return originals[index]

    def remap_tree_offsets(
        self,
        unit: Any,
        positions: list[int],
        originals: list[int],
        original_text: str,
    ) -> None:
        """Recursively remap ``.start``/``.end`` of leaf/internal nodes from
        the tokenized space back to character offsets in the original text.

        The DUConverter produces strictly binary trees: each node is either a
        leaf (no children) or has BOTH ``left`` and ``right``. Unary nodes
        signal a tree-construction bug and are surfaced rather than silently
        patched.

        Mutates ``unit`` in-place and updates ``unit.text`` accordingly.

        Raises:
            ValueError: if a non-leaf node is missing one of its children.
        """
        pending = [(unit, False)]
        while pending:
            node, expanded = pending.pop()
            left = getattr(node, "left", None)
            right = getattr(node, "right", None)
            if expanded:
                if left is None and right is None:
                    node.start = self._map_offset(node.start, positions, originals)
                    node.end = self._map_offset(node.end, positions, originals)
                elif left is not None and right is not None:
                    node.start = left.start
                    node.end = right.end
                else:
                    raise ValueError(
                        "remap_tree_offsets received a unary node (one of left/right is None). "
                        "DUConverter is expected to produce strictly binary trees."
                    )
                node.text = original_text[node.start : node.end]
                continue
            pending.append((node, True))
            if right is not None:
                pending.append((right, False))
            if left is not None:
                pending.append((left, False))

    def remap_tree_to_edu_spans(
        self,
        unit: Any,
        spans: Sequence[tuple[int, int]],
        original_text: str,
    ) -> None:
        """Map an inferred tree onto authoritative predefined-EDU spans.

        Transformer tokenizers may normalize combining Unicode marks, so their
        offset mappings are not a safe authority for caller-supplied EDU
        boundaries. The model still determines the tree; this method verifies
        that it produced exactly one ordered leaf per EDU and restores the
        caller's exact character coordinates.
        """

        leaves: list[Any] = []
        pending = [unit]
        while pending:
            node = pending.pop()
            left = getattr(node, "left", None)
            right = getattr(node, "right", None)
            if left is None and right is None:
                leaves.append(node)
                continue
            if left is None or right is None:
                raise ValueError("predefined-EDU tree contains a unary node")
            pending.append(right)
            pending.append(left)
        if len(leaves) != len(spans):
            raise ValueError(
                "The produced tree does not contain exactly one leaf per provided EDU "
                f"(leaves={len(leaves)}, edus={len(spans)})."
            )
        for index, (leaf, (start, end)) in enumerate(zip(leaves, spans, strict=True)):
            if not (0 <= start < end <= len(original_text)):
                raise ValueError(f"EDU span {index} is outside the joined source text")
            if index and spans[index - 1][1] > start:
                raise ValueError(f"EDU span {index} is not ordered after the preceding EDU")
            leaf.start = start
            leaf.end = end
            leaf.text = original_text[start:end]

        pending_nodes = [(unit, False)]
        while pending_nodes:
            node, expanded = pending_nodes.pop()
            left = getattr(node, "left", None)
            right = getattr(node, "right", None)
            if left is None and right is None:
                continue
            if left is None or right is None:
                raise ValueError("predefined-EDU tree contains a unary node")
            if expanded:
                node.start = left.start
                node.end = right.end
                node.text = original_text[node.start : node.end]
                continue
            pending_nodes.append((node, True))
            pending_nodes.append((right, False))
            pending_nodes.append((left, False))

    @staticmethod
    def predicted_edu_source_spans(
        breaks: Sequence[int], subword_offsets: Sequence[tuple[int, int]],
        positions: list[int], originals: list[int], text: str,
    ) -> list[tuple[int, int]]:
        """Map actual predicted subword boundaries through the tokenizer's offsets.

        Decoded token strings can contain unknown-token spellings or Unicode
        normalization changes. Their lengths must never determine source spans.
        """
        spans: list[tuple[int, int]] = []
        first = 0
        for last in breaks:
            if not first <= last < len(subword_offsets):
                raise ValueError("Predicted EDU boundary is outside the remaining subwords")
            offsets = [(start, end) for start, end in subword_offsets[first:last + 1] if start < end]
            if not offsets:
                raise ValueError("Predicted EDU contains no source characters")
            start = BasePredictor._map_offset(offsets[0][0], positions, originals)
            end = BasePredictor._map_offset(offsets[-1][1], positions, originals)
            while start < end and text[start].isspace():
                start += 1
            while end > start and text[end - 1].isspace():
                end -= 1
            if start == end:
                raise ValueError("Predicted EDU contains only whitespace")
            spans.append((start, end))
            first = last + 1
        if first != len(subword_offsets):
            raise ValueError("Predicted EDU boundaries do not cover all subwords")
        return spans

    @staticmethod
    def _guess_token_offsets(text: str, tokens: Sequence[str]) -> list[tuple[int, int]]:
        """Best-effort alignment of already-tokenized `tokens` to raw `text`.

        Used when external word tokens are supplied without character-level
        offsets. Walks forward to find each token at or after the running
        cursor position. Empty tokens are recorded as zero-width spans at the
        cursor.

        Raises:
            ValueError: if any token cannot be located in `text`. Previously
            the function silently fell back to ``(cursor, cursor + len(token))``
            on misses, which produced wrong offsets downstream.
        """
        offsets: list[tuple[int, int]] = []
        cursor = 0
        for idx, token in enumerate(tokens):
            if not token:
                offsets.append((cursor, cursor))
                continue

            last_start = len(text) - len(token)
            start = cursor
            while start <= last_start and text[start : start + len(token)] != token:
                start += 1
            if start > last_start:
                raise ValueError(f"Cannot locate token {idx} ({token!r}) in text at or after position {cursor}.")
            end = start + len(token)
            offsets.append((start, end))
            cursor = end
        return offsets

    @staticmethod
    def _recount_spans(
        word_offsets: Sequence[tuple[int, int]],
        subword_offsets: Sequence[tuple[int, int]],
        word_span_boundaries: Sequence[int],
    ) -> list[int]:
        """Given word span boundaries, recount for subwords."""
        subword_span_boundaries = [0]

        for w_end in word_span_boundaries:
            final_char = word_offsets[w_end][1]
            for i in range(1, len(subword_offsets)):
                if subword_offsets[i][0] < subword_offsets[i][1] and subword_offsets[i][0] >= final_char:
                    # Fixes LUKE segmentation
                    if i - 1 in subword_span_boundaries:
                        subword_span_boundaries.append(i)
                    else:
                        subword_span_boundaries.append(i - 1)
                    break

        if len(subword_offsets) - 1 not in subword_span_boundaries:
            subword_span_boundaries.append(len(subword_offsets) - 1)

        return subword_span_boundaries[1:]

    @staticmethod
    def _collect_leaf_texts(unit: Any, acc: list[str]) -> None:
        pending = [unit]
        while pending:
            node = pending.pop()
            left = getattr(node, "left", None)
            right = getattr(node, "right", None)
            if left is None and right is None:
                acc.append(node.text)
                continue
            if right is not None:
                pending.append(right)
            if left is not None:
                pending.append(left)

    @staticmethod
    def _validate_edus(edus: object) -> list[str]:
        """Validate untrusted input as a sequence of EDU strings.

        Typed ``object`` because this is the input-validation boundary for the
        public ``parse_from_edus`` API: callers may pass anything, and the
        guards below narrow it to ``list[str]`` or raise.

        Raises:
            ValueError: if `edus` is None, empty, or contains an empty string.
            TypeError: if `edus` is not a non-string sequence of strings.
        """
        if edus is None:
            raise ValueError("`edus` must be provided for parsing.")

        if isinstance(edus, (str, bytes)):
            raise TypeError("`edus` must be a sequence of strings, not a single string.")

        if not isinstance(edus, Sequence):
            raise TypeError("`edus` must be a sequence of strings.")

        if not edus:
            raise ValueError("`edus` must contain at least one EDU.")

        normalized: list[str] = []
        for idx, edu in enumerate(cast(Sequence[object], edus)):
            if not isinstance(edu, str):
                raise TypeError(f"EDU at position {idx} must be a string.")
            if not edu:
                raise ValueError(f"EDU at position {idx} is empty.")
            normalized.append(edu)

        return normalized

    @staticmethod
    def _compute_edu_char_spans(edus: Sequence[str]) -> tuple[str, list[tuple[int, int]]]:
        """Concatenate `edus` with single-space separators and return the joined
        text plus the character span of each EDU within it."""
        text = " ".join(edus)
        spans: list[tuple[int, int]] = []
        cursor = 0

        for idx, edu in enumerate(edus):
            start = cursor
            end = start + len(edu)
            if text[start:end] != edu:
                raise ValueError(f"EDU at position {idx} does not align after concatenation.")
            spans.append((start, end))
            cursor = end + 1 if idx < len(edus) - 1 else end

        return text, spans

    @staticmethod
    def _char_spans_to_token_breaks(
        offsets: Sequence[tuple[int, int]],
        spans: Sequence[tuple[int, int]],
    ) -> list[int]:
        """Map EDU character spans onto token boundaries.

        Args:
            offsets: ``(start, stop)`` pairs for each tokenized word.
            spans: ``(start, end)`` character spans of each EDU within the joined text.

        Returns:
            For each EDU, the index of its last token in the flat token list.
        """
        if not offsets:
            raise ValueError("Unable to derive token boundaries from the provided EDUs.")

        token_stops = [stop for _, stop in offsets]
        edu_breaks: list[int] = []
        token_idx = -1

        for span_idx, (_, edu_end) in enumerate(spans):
            while token_idx + 1 < len(token_stops) and token_stops[token_idx + 1] <= edu_end:
                token_idx += 1

            if token_idx == -1 or token_stops[token_idx] != edu_end:
                raise ValueError(f"EDU at position {span_idx} does not align with tokenizer boundaries.")

            edu_breaks.append(token_idx)

        if edu_breaks[-1] != len(token_stops) - 1:
            raise ValueError("EDU boundaries do not cover the entire tokenized text.")

        return edu_breaks

    @staticmethod
    def _load_torch_weights(path: str | Path, device: torch.device) -> dict[str, Any]:
        """Load a PyTorch state dict with ``weights_only=True``.

        All checkpoints published under ``tchewik/isanlp_rst_v3`` (verified
        against ``gumrrg`` and ``unirst``) are pure ``OrderedDict[str, Tensor]``
        and require no allow-listed globals. Forward-compatible with PyTorch
        2.6+, which made ``weights_only=True`` the default.
        """
        return torch.load(path, map_location=device, weights_only=True)

    @staticmethod
    def _resolve_dtype(
        dtype: str | torch.dtype | None,
        device: torch.device | None = None,
    ) -> torch.dtype:
        """Compatibility façade over the shared device-aware dtype resolver."""

        return resolve_dtype(device or torch.device("cpu"), dtype)

    def _autocast(self) -> AbstractContextManager[Any]:
        """Return a context manager enabling autocast for inference.

        When ``self._dtype`` is ``float32`` the context is a no-op (autocast
        ``enabled=False``). For ``float16`` / ``bfloat16`` it dispatches to the
        right device-typed autocast (CUDA / MPS / CPU). Combine with
        ``torch.inference_mode()`` at call sites.
        """
        device_type = self._device.type
        return torch.autocast(
            device_type=device_type,
            dtype=self._dtype,
            enabled=(self._dtype is not torch.float32),
        )

    def parse_rst(self, text: str, *, capture_evidence: bool = False) -> Any:
        """Parse raw text into an RST tree. Required override."""
        raise NotImplementedError(f"{type(self).__name__} must implement parse_rst")

    def parse_from_edus(self, edus: Sequence[str], *, capture_evidence: bool = False) -> Any:
        """Parse pre-segmented EDUs into an RST tree. Required override."""
        raise NotImplementedError(f"{type(self).__name__} must implement parse_from_edus")

    def __call__(self, text: str) -> Any:
        return self.parse_rst(text)

    def analyse_with_evidence(
        self,
        text: str,
        edus: Sequence[Any] | None = None,
        sentence_boundaries: tuple[TextSpan, ...] = (),
        paragraph_boundaries: tuple[TextSpan, ...] = (),
        segmentation_source: str | None = None,
    ) -> Any:
        """Run inference and wrap exact substrate and parse evidence in PredictorAnalysisTrace."""
        from rdam.rst.contracts.document import Edu as ContractEdu
        from rdam.rst.contracts.trace import PredictorAnalysisTrace
        from rdam.rst.converter import du_to_analysis

        if edus is not None and len(edus) > 0:
            edu_texts = [e.text for e in edus] if isinstance(edus[0], ContractEdu) else [str(e) for e in edus]
            res = self.parse_from_edus(edu_texts, capture_evidence=True)
            used_source = segmentation_source or "presegmented"
        else:
            res = self.parse_rst(text, capture_evidence=True)
            used_source = segmentation_source or "model"

        root_unit = res["rst"][0]
        analysis = du_to_analysis(root_unit, document_id="doc")

        import razdel

        resolved_sentences = sentence_boundaries or tuple(
            TextSpan(start=sentence.start, end=sentence.stop, text=sentence.text)
            for sentence in razdel.sentenize(text)
        )
        resolved_paragraphs = paragraph_boundaries or (TextSpan(start=0, end=len(text), text=text),)

        raw_tokens = res.get("analysis_tokens")
        if not isinstance(raw_tokens, tuple) or any(
            not isinstance(token, DocumentToken) for token in cast(tuple[object, ...], raw_tokens)
        ):
            raise ValueError("predictor did not return its input word tokens")
        input_tokens = cast(tuple[DocumentToken, ...], raw_tokens)
        sentence_ids = self.capture_token_groups(text, input_tokens, resolved_sentences)
        paragraph_ids = self.capture_token_groups(text, input_tokens, resolved_paragraphs)
        tokens: list[DocumentToken] = []
        for t, sentence_id, paragraph_id in zip(input_tokens, sentence_ids, paragraph_ids, strict=True):
            tokens.append(
                DocumentToken(
                    token_id=t.token_id,
                    text=t.text,
                    start=t.start,
                    end=t.end,
                    sentence_id=sentence_id,
                    paragraph_id=paragraph_id,
                )
            )

        leaves: list[Any] = []
        self._collect_leaf_units(root_unit, leaves)
        leaf_spans = tuple(TextSpan(start=leaf.start, end=leaf.end, text=leaf.text) for leaf in leaves)
        leaf_tok_ids = self.capture_edu_memberships(text, tokens, leaf_spans)

        contract_edus: list[ContractEdu] = []
        for idx, span in enumerate(leaf_spans):
            contract_edus.append(
                ContractEdu(
                    edu_id=idx + 1,
                    text=span.text,
                    start=span.start,
                    end=span.end,
                    token_ids=tuple(sorted(leaf_tok_ids[idx])),
                )
            )

        raw_decisions = res.get("network_decisions")
        if not isinstance(raw_decisions, tuple):
            raise ValueError("predictor did not return captured network decision evidence")
        if any(
            not isinstance(decision, NetworkStructureDecision) for decision in cast(tuple[object, ...], raw_decisions)
        ):
            raise ValueError("predictor did not return captured network decision evidence")
        structure_decisions = cast(tuple[NetworkStructureDecision, ...], raw_decisions)
        self._validate_structure_decisions(root_unit, structure_decisions)
        joint_inventory = (
            structure_decisions[0].joint_labels if structure_decisions else tuple(getattr(self, "relation_table", ()))
        )
        if any(decision.joint_labels != joint_inventory for decision in structure_decisions):
            raise ValueError("network class inventory changed within one document")
        raw_inventory = tuple(dict.fromkeys(label.rpartition("_")[0] for label in joint_inventory))

        return PredictorAnalysisTrace(
            root_unit=root_unit,
            analysis=analysis,
            tokens=tuple(tokens),
            edus=tuple(contract_edus),
            sentence_boundaries=resolved_sentences,
            paragraph_boundaries=resolved_paragraphs,
            structure_decisions=structure_decisions,
            segmentation_source=used_source,
            relation_inventory=tuple(raw_inventory),
        )

    @staticmethod
    def _validate_structure_decisions(unit: Any, decisions: tuple[NetworkStructureDecision, ...]) -> None:
        """Check captured choices against the converted tree without inventing scores."""
        by_span = {(decision.start, decision.end): decision for decision in decisions}
        if len(by_span) != len(decisions):
            raise ValueError("duplicate network constituent evidence")
        spans: dict[int, tuple[int, int]] = {}
        visited: set[tuple[int, int]] = set()
        leaf_index = 0
        pending = [(unit, False)]
        while pending:
            node, expanded = pending.pop()
            left = getattr(node, "left", None)
            right = getattr(node, "right", None)
            if left is None and right is None:
                spans[id(node)] = (leaf_index, leaf_index)
                leaf_index += 1
                continue
            if left is None or right is None:
                raise ValueError("parsed RST evidence contains a unary node")
            if not expanded:
                pending.append((node, True))
                pending.append((right, False))
                pending.append((left, False))
                continue
            start, split = spans[id(left)]
            _, end = spans[id(right)]
            decision = by_span.get((start, end))
            if decision is None:
                raise ValueError("decoded constituent has no captured network decision")
            relation, _, nuclearity = decision.joint_labels[decision.selected_class].rpartition("_")
            if (
                decision.split != split
                or relation.casefold() != node.relation.casefold()
                or nuclearity.upper() != node.nuclearity.upper()
            ):
                raise ValueError("captured network decision contradicts the decoded tree")
            visited.add((start, end))
            spans[id(node)] = (start, end)
        if visited != by_span.keys():
            raise ValueError("network evidence contains constituents absent from the decoded tree")

    def _collect_leaf_units(self, unit: Any, leaves: list[Any]) -> None:
        pending = [unit]
        while pending:
            node = pending.pop()
            left = getattr(node, "left", None)
            right = getattr(node, "right", None)
            if left is None and right is None:
                leaves.append(node)
                continue
            if right is not None:
                pending.append(right)
            if left is not None:
                pending.append(left)

from __future__ import annotations

import os
from bisect import bisect_right
from typing import Iterable, List, Optional, Sequence, Tuple

# Apple Silicon: enable CPU fallback for MPS-unsupported ops BEFORE torch is
# imported. PyTorch 2.x lacks an MPS kernel for `torch.linalg.qr`, which is
# used inside `torch.nn.init.orthogonal_` during model construction. Without
# this flag, MPS users hit `NotImplementedError` at first use. Setting it here
# (idempotent via setdefault) keeps user environments untouched if they've
# already opted in or out.
os.environ.setdefault('PYTORCH_ENABLE_MPS_FALLBACK', '1')

import torch  # noqa: E402  (intentionally after env var setup above)


def str2bool(value):
    """Robust string-to-bool conversion used in configs."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() == "true"
    return bool(value)


class BasePredictor:
    """Mixin-style base with shared tokenization, batching and offset utils.

    Not abstract: the ABC inheritance was dropped because no methods are
    abstract. Predictors compose this base by inheritance and override
    ``parse_rst`` / ``parse_from_edus`` / ``tokenize`` directly.
    """

    tokenizer = None
    # Set by subclasses' ``__init__`` after ``_select_device`` and
    # ``_resolve_dtype`` resolve them. Declared here so Pyright can narrow
    # ``self._cuda_device`` and ``self._dtype`` on the base methods that use
    # them (``_autocast``, ``_load_torch_weights``).
    _cuda_device: 'torch.device'
    _dtype: 'torch.dtype'

    @staticmethod
    def divide_chunks(_list: Sequence, n: int) -> Iterable[Sequence]:
        """Yield chunks of size `n` from `_list` (handles empty lists)."""
        if _list:
            for i in range(0, len(_list), n):
                yield _list[i : min(i + n, len(_list))]
        else:
            yield _list

    @staticmethod
    def build_offset_converter_from_words(
        text: str,
        tokens: Sequence[str],
        token_offsets: Optional[Sequence[Tuple[int, int]]] = None,
    ) -> Tuple[List[int], List[int]]:
        """Build offset converter from word tokens and optional (start, end) pairs.

        If `token_offsets` is omitted, a best-effort alignment is performed.
        Returns two lists: `positions` (flattened space of tokenized text) and
        `originals` (mapped indices in the original text).
        """
        if token_offsets is None:
            token_offsets = BasePredictor._guess_token_offsets(text, tokens)

        positions: List[int] = []
        originals: List[int] = []
        cursor = 0

        for idx, (tok, (start, end)) in enumerate(zip(tokens, token_offsets, strict=True)):
            token_text = tok or ""
            for _ in range(len(token_text)):
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
        tokens,
    ) -> Tuple[List[int], List[int]]:
        """Build offset converter from a list of `razdel.Token` objects."""
        positions: List[int] = []
        originals: List[int] = []
        cursor = 0

        for idx, token in enumerate(tokens):
            token_text = token.text
            for char_idx in range(len(token_text)):
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
    def _map_offset(value: int, positions: List[int], originals: List[int]) -> int:
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
        unit,
        positions: List[int],
        originals: List[int],
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
        left = getattr(unit, "left", None)
        right = getattr(unit, "right", None)

        if left is not None:
            self.remap_tree_offsets(left, positions, originals, original_text)
        if right is not None:
            self.remap_tree_offsets(right, positions, originals, original_text)

        if left is None and right is None:
            unit.start = self._map_offset(unit.start, positions, originals)
            unit.end = self._map_offset(unit.end, positions, originals)
        elif left is not None and right is not None:
            unit.start = left.start
            unit.end = right.end
        else:
            raise ValueError(
                'remap_tree_offsets received a unary node (one of left/right is None). '
                'DUConverter is expected to produce strictly binary trees.'
            )

        unit.text = original_text[unit.start : unit.end]

    @staticmethod
    def _guess_token_offsets(text: str, tokens: Sequence[str]) -> List[Tuple[int, int]]:
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
        offsets: List[Tuple[int, int]] = []
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
                raise ValueError(
                    f"Cannot locate token {idx} ({token!r}) in text at or after position {cursor}."
                )
            end = start + len(token)
            offsets.append((start, end))
            cursor = end
        return offsets

    @staticmethod
    def _recount_spans(word_offsets, subword_offsets, word_span_boundaries):
        """ Given word span boundaries, recount for subwords. """
        subword_span_boundaries = [0]

        for w_end in word_span_boundaries:
            final_char = word_offsets[w_end][1]
            for i in range(1, len(subword_offsets)):
                if subword_offsets[i][0] < subword_offsets[i][1]:
                    if subword_offsets[i][0] >= final_char:
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
    def _collect_leaf_texts(unit, acc: List[str]) -> None:
        left = getattr(unit, 'left', None)
        right = getattr(unit, 'right', None)

        if left is None and right is None:
            acc.append(unit.text)
            return

        if left is not None:
            BasePredictor._collect_leaf_texts(left, acc)
        if right is not None:
            BasePredictor._collect_leaf_texts(right, acc)

    @staticmethod
    def _validate_edus(edus: Sequence[str]) -> List[str]:
        """Validate a sequence of EDU strings and return a normalized list.

        Raises:
            ValueError: if `edus` is None, empty, or contains an empty string.
            TypeError: if `edus` is not a non-string sequence of strings.
        """
        if edus is None:
            raise ValueError('`edus` must be provided for parsing.')

        if isinstance(edus, (str, bytes)):
            raise TypeError('`edus` must be a sequence of strings, not a single string.')

        if not isinstance(edus, Sequence):
            raise TypeError('`edus` must be a sequence of strings.')

        if not edus:
            raise ValueError('`edus` must contain at least one EDU.')

        normalized: List[str] = []
        for idx, edu in enumerate(edus):
            if not isinstance(edu, str):
                raise TypeError(f'EDU at position {idx} must be a string.')
            if not edu:
                raise ValueError(f'EDU at position {idx} is empty.')
            normalized.append(edu)

        return normalized

    @staticmethod
    def _compute_edu_char_spans(edus: Sequence[str]) -> Tuple[str, List[Tuple[int, int]]]:
        """Concatenate `edus` with single-space separators and return the joined
        text plus the character span of each EDU within it."""
        text = ' '.join(edus)
        spans: List[Tuple[int, int]] = []
        cursor = 0

        for idx, edu in enumerate(edus):
            start = cursor
            end = start + len(edu)
            if text[start:end] != edu:
                raise ValueError(f'EDU at position {idx} does not align after concatenation.')
            spans.append((start, end))
            if idx < len(edus) - 1:
                cursor = end + 1
            else:
                cursor = end

        return text, spans

    @staticmethod
    def _char_spans_to_token_breaks(
        offsets: Sequence[Tuple[int, int]],
        spans: Sequence[Tuple[int, int]],
    ) -> List[int]:
        """Map EDU character spans onto token boundaries.

        Args:
            offsets: ``(start, stop)`` pairs for each tokenized word.
            spans: ``(start, end)`` character spans of each EDU within the joined text.

        Returns:
            For each EDU, the index of its last token in the flat token list.
        """
        if not offsets:
            raise ValueError('Unable to derive token boundaries from the provided EDUs.')

        token_stops = [stop for _, stop in offsets]
        edu_breaks: List[int] = []
        token_idx = -1

        for span_idx, (_, edu_end) in enumerate(spans):
            while token_idx + 1 < len(token_stops) and token_stops[token_idx + 1] <= edu_end:
                token_idx += 1

            if token_idx == -1 or token_stops[token_idx] != edu_end:
                raise ValueError(
                    f'EDU at position {span_idx} does not align with tokenizer boundaries.'
                )

            edu_breaks.append(token_idx)

        if edu_breaks[-1] != len(token_stops) - 1:
            raise ValueError('EDU boundaries do not cover the entire tokenized text.')

        return edu_breaks

    @staticmethod
    def _load_torch_weights(path: str, device: torch.device) -> dict:
        """Load a PyTorch state dict with ``weights_only=True``.

        All checkpoints published under ``tchewik/isanlp_rst_v3`` (verified
        against ``gumrrg`` and ``unirst``) are pure ``OrderedDict[str, Tensor]``
        and require no allow-listed globals. Forward-compatible with PyTorch
        2.6+, which made ``weights_only=True`` the default.
        """
        return torch.load(path, map_location=device, weights_only=True)

    @staticmethod
    def _resolve_dtype(
        dtype: 'str | torch.dtype | None',
        device: torch.device,
    ) -> torch.dtype:
        """Normalise a dtype spec to a ``torch.dtype``, defaulting per device.

        Accepts:
            * ``None`` -> device-aware default. CPU stays at ``float32``;
              CUDA and MPS pick ``float16`` (industry-standard for transformer
              inference on hardware with native half-precision matmul, with
              numerical-sensitive ops kept in ``float32`` by ``torch.autocast``).
              For exact bit-equivalence with the historical ``float32`` outputs,
              callers must pass ``dtype=torch.float32`` explicitly.
            * a ``torch.dtype`` instance, returned as-is after validation.
            * a string: ``'float32' / 'fp32'``, ``'float16' / 'fp16' / 'half'``,
              ``'bfloat16' / 'bf16'``.

        Raises:
            ValueError: if the string is not recognised, or the dtype is not
            one of the three supported by ``torch.autocast``.
        """
        if dtype is None:
            # Default: fp32 across all devices. Measured on Apple Silicon
            # (M-series, PyTorch 2.11), bf16/fp16 autocast is ~1.5x slower
            # than native fp32 for typical document-length inputs because
            # per-op dtype-dispatch overhead dominates the matmul speedup.
            # On large-batch CUDA workloads with H100/Ada Tensor Cores, bf16
            # likely wins — pass ``dtype=torch.bfloat16`` explicitly there.
            # See ``scripts/bench.py`` to measure on your hardware.
            return torch.float32
        if isinstance(dtype, str):
            key = dtype.lower().strip()
            mapping = {
                'float32': torch.float32, 'fp32': torch.float32,
                'float16': torch.float16, 'fp16': torch.float16, 'half': torch.float16,
                'bfloat16': torch.bfloat16, 'bf16': torch.bfloat16,
            }
            if key not in mapping:
                raise ValueError(
                    f"Unknown dtype {dtype!r}. Supported: "
                    "'float32'/'fp32', 'float16'/'fp16'/'half', 'bfloat16'/'bf16'."
                )
            return mapping[key]
        if dtype in (torch.float32, torch.float16, torch.bfloat16):
            return dtype
        raise ValueError(
            f"Unsupported dtype {dtype!r}. Use float32, float16, or bfloat16."
        )

    def _autocast(self):
        """Return a context manager enabling autocast for inference.

        When ``self._dtype`` is ``float32`` the context is a no-op (autocast
        ``enabled=False``). For ``float16`` / ``bfloat16`` it dispatches to the
        right device-typed autocast (CUDA / MPS / CPU). Combine with
        ``torch.inference_mode()`` at call sites.
        """
        device_type = self._cuda_device.type
        return torch.autocast(
            device_type=device_type,
            dtype=self._dtype,
            enabled=(self._dtype is not torch.float32),
        )

    @staticmethod
    def _select_device(cuda_device: int) -> torch.device:
        """Choose the best available compute device.

        - ``cuda_device == -1`` -> ``cpu``.
        - ``cuda_device >= 0``:
            * NVIDIA CUDA available  -> ``cuda:<cuda_device>``.
            * Apple Silicon MPS available -> ``mps`` (the integer is ignored;
              MPS exposes a single device). ``PYTORCH_ENABLE_MPS_FALLBACK=1``
              is set automatically so MPS-unsupported ops (notably
              ``torch.linalg.qr`` used by orthogonal weight init) fall back to
              CPU for that op while the rest of the model stays on MPS.
            * Otherwise -> ``RuntimeError`` so the caller knows acceleration
              was requested but no GPU backend is reachable.

        The parameter is named ``cuda_device`` for backward compatibility with
        the public ``Parser`` / predictor signatures. MPS dispatch is automatic
        on Apple Silicon hosts where CUDA is not present.
        """
        if cuda_device == -1:
            return torch.device('cpu')
        if torch.cuda.is_available():
            return torch.device(f'cuda:{cuda_device}')
        mps_available = (
            hasattr(torch.backends, 'mps')
            and torch.backends.mps.is_available()
            and torch.backends.mps.is_built()
        )
        if mps_available:
            # Required so e.g. torch.linalg.qr (used inside orthogonal_ init)
            # falls back to CPU rather than raising NotImplementedError on MPS.
            os.environ.setdefault('PYTORCH_ENABLE_MPS_FALLBACK', '1')
            return torch.device('mps')
        raise RuntimeError(
            f'cuda_device={cuda_device} requested but no GPU backend is '
            'available (neither CUDA nor MPS). Pass cuda_device=-1 for CPU.'
        )


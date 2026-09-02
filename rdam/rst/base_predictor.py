import os
import warnings
from bisect import bisect_right
from collections.abc import Iterable, Sequence
from contextlib import AbstractContextManager
from dataclasses import dataclass
from itertools import batched
from pathlib import Path
from typing import Any, Protocol

from ._torch_runtime import torch


class _OffsetToken(Protocol):
    """Minimal razdel-token surface used by offset remapping."""

    text: str
    start: int
    stop: int


def str2bool(value: object) -> bool:
    """Robust string-to-bool conversion used in configs."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() == "true"
    return bool(value)


@dataclass(frozen=True, slots=True)
class DeviceProbe:
    """Immutable snapshot of which accelerators the host exposes.

    Production code uses ``DeviceProbe.detect()``. Tests pass explicit
    probes — no monkeypatching of ``torch.cuda`` / MPS backends.
    This project is Apple-Silicon-first; CUDA fields exist so the public
    ``device='cuda*'`` API stays correct without needing NVIDIA CI.
    """

    cuda_available: bool = False
    cuda_device_count: int = 0
    mps_available: bool = False

    @classmethod
    def detect(cls) -> DeviceProbe:
        """Probe the real host (CUDA, then MPS, else CPU-only)."""
        cuda_ok = torch.cuda.is_available()
        return cls(
            cuda_available=cuda_ok,
            cuda_device_count=torch.cuda.device_count() if cuda_ok else 0,
            mps_available=_mps_available(),
        )


def _mps_available() -> bool:
    """True when this host has a usable MPS (Apple Silicon Metal) backend."""
    return hasattr(torch.backends, "mps") and torch.backends.mps.is_available() and torch.backends.mps.is_built()


def _device_from_spec(spec: str, probe: DeviceProbe) -> torch.device:
    """Resolve the string device API to a ``torch.device``.

    ``"auto"`` picks the best available backend (CUDA, else MPS, else CPU) and
    never raises. ``"cpu"`` is always available. ``"mps"`` / ``"cuda"`` /
    ``"cuda:N"`` are explicit requests and raise ``RuntimeError`` if that
    backend is not present on the host (per ``probe``).
    """
    key = spec.strip().lower()
    if key == "cpu":
        return torch.device("cpu")
    if key == "auto":
        if probe.cuda_available:
            return torch.device("cuda:0")
        if probe.mps_available:
            os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")
            return torch.device("mps")
        return torch.device("cpu")
    if key == "mps":
        if not probe.mps_available:
            raise RuntimeError("device='mps' requested but MPS is not available on this host.")
        os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")
        return torch.device("mps")
    if key == "cuda" or key.startswith("cuda:"):
        if not probe.cuda_available:
            raise RuntimeError(f"device={spec!r} requested but CUDA is not available on this host.")
        if key == "cuda":
            return torch.device("cuda:0")
        try:
            index = int(key.split(":", 1)[1])
        except ValueError as exc:
            raise ValueError(f"Invalid CUDA device specifier: {spec!r}") from exc
        if index < 0:
            raise ValueError(f"CUDA device index must be non-negative: {spec!r}")
        if index >= probe.cuda_device_count:
            raise ValueError(f"CUDA device index {index} is out of range (device_count={probe.cuda_device_count}).")
        return torch.device(f"cuda:{index}")
    raise ValueError(f"Unrecognised device {spec!r}. Expected 'auto', 'cpu', 'mps', 'cuda', or 'cuda:N'.")


def _device_from_legacy_int(cuda_device: int, probe: DeviceProbe) -> torch.device:
    """Reproduce the historical ``cuda_device: int`` selection exactly.

    ``-1`` -> CPU. ``>= 0`` -> ``cuda:<n>`` on an NVIDIA host, else ``mps`` on
    Apple Silicon, else ``RuntimeError``. Kept bit-for-bit so the deprecated
    integer path behaves as it always did.
    """
    if isinstance(cuda_device, bool) or not isinstance(cuda_device, int):
        raise ValueError(f"cuda_device must be an int (-1 for CPU, or >= 0 for GPU); got {cuda_device!r}.")
    if cuda_device < -1:
        raise ValueError(f"cuda_device must be -1 (CPU) or >= 0 (GPU); got {cuda_device}.")
    if cuda_device == -1:
        return torch.device("cpu")
    if probe.cuda_available:
        return torch.device(f"cuda:{cuda_device}")
    if probe.mps_available:
        os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")
        return torch.device("mps")
    raise RuntimeError(
        f"cuda_device={cuda_device} requested but no GPU backend is "
        'available (neither CUDA nor MPS). Pass device="cpu" for CPU.'
    )


def resolve_device(
    device: str | torch.device | None = None,
    cuda_device: int | None = None,
    *,
    probe: DeviceProbe | None = None,
) -> torch.device:
    """Resolve the compute device from the string API (or the deprecated int).

    ``device`` is the canonical API:

    - ``"auto"`` (or ``None``) -> CUDA if present, else MPS on Apple Silicon,
      else CPU.
    - ``"cpu"`` -> CPU.
    - ``"mps"`` -> Apple Silicon Metal backend (raises if unavailable).
    - ``"cuda"`` / ``"cuda:N"`` -> a specific NVIDIA device (raises if no CUDA).
    - a ``torch.device`` -> validated with the same availability rules.

    ``cuda_device`` is the deprecated integer shim: ``-1`` -> CPU; ``>= 0`` ->
    the best available accelerator. Passing it emits a ``DeprecationWarning``.
    Passing both ``device`` and ``cuda_device`` is a ``ValueError``.

    ``probe`` injects accelerator availability for tests; production omits it
    and uses ``DeviceProbe.detect()``.
    """
    resolved_probe = probe if probe is not None else DeviceProbe.detect()

    if cuda_device is not None:
        if device is not None:
            raise ValueError("Pass either `device` (preferred) or `cuda_device` (deprecated), not both.")
        resolved_device = _device_from_legacy_int(cuda_device, resolved_probe)
        warnings.warn(
            "`cuda_device` is deprecated and will be removed in a future release; "
            "use `device=` instead (e.g. device='auto'|'cpu'|'mps'|'cuda:0'). "
            "cuda_device=-1 maps to device='cpu'; cuda_device>=0 selects the best "
            "available accelerator.",
            DeprecationWarning,
            stacklevel=2,
        )
        return resolved_device

    if device is None:
        return _device_from_spec("auto", resolved_probe)
    if isinstance(device, torch.device):
        # Same availability rules as the string API — do not silently accept
        # an unavailable backend via passthrough.
        if device.type == "cpu":
            return device
        return _device_from_spec(str(device), resolved_probe)
    return _device_from_spec(device, resolved_probe)


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
                "remap_tree_offsets received a unary node (one of left/right is None). "
                "DUConverter is expected to produce strictly binary trees."
            )

        unit.text = original_text[unit.start : unit.end]

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

        def collect(node: Any) -> None:
            left = getattr(node, "left", None)
            right = getattr(node, "right", None)
            if left is None and right is None:
                leaves.append(node)
                return
            if left is None or right is None:
                raise ValueError("predefined-EDU tree contains a unary node")
            collect(left)
            collect(right)

        collect(unit)
        if len(leaves) != len(spans):
            raise ValueError(
                "The produced tree does not contain exactly one leaf per provided EDU "
                f"(leaves={len(leaves)}, edus={len(spans)})."
            )
        for index, (leaf, (start, end)) in enumerate(zip(leaves, spans, strict=True)):
            if not (0 <= start < end <= len(original_text)):
                raise ValueError(f"EDU span {index} is outside the joined source text")
            if index and spans[index - 1][1] >= start:
                raise ValueError(f"EDU span {index} is not ordered after the preceding EDU")
            leaf.start = start
            leaf.end = end
            leaf.text = original_text[start:end]

        def update_internal(node: Any) -> None:
            left = getattr(node, "left", None)
            right = getattr(node, "right", None)
            if left is None and right is None:
                return
            if left is None or right is None:
                raise ValueError("predefined-EDU tree contains a unary node")
            update_internal(left)
            update_internal(right)
            node.start = left.start
            node.end = right.end
            node.text = original_text[node.start : node.end]

        update_internal(unit)

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
    def _collect_leaf_texts(unit: Any, acc: list[str]) -> None:
        left = getattr(unit, "left", None)
        right = getattr(unit, "right", None)

        if left is None and right is None:
            acc.append(unit.text)
            return

        if left is not None:
            BasePredictor._collect_leaf_texts(left, acc)
        if right is not None:
            BasePredictor._collect_leaf_texts(right, acc)

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
        for idx, edu in enumerate(edus):
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
            if idx < len(edus) - 1:
                cursor = end + 1
            else:
                cursor = end

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
    ) -> torch.dtype:
        """Normalise a dtype spec to a ``torch.dtype``.

        Accepts:
            * ``None`` -> ``float32`` on every device (the default). Measured
              fastest for document-length inputs on Apple Silicon; pass
              ``dtype='bf16'`` explicitly for large-batch CUDA where native
              half-precision matmul wins.
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
                "float32": torch.float32,
                "fp32": torch.float32,
                "float16": torch.float16,
                "fp16": torch.float16,
                "half": torch.float16,
                "bfloat16": torch.bfloat16,
                "bf16": torch.bfloat16,
            }
            if key not in mapping:
                raise ValueError(
                    f"Unknown dtype {dtype!r}. Supported: 'float32'/'fp32', 'float16'/'fp16'/'half', 'bfloat16'/'bf16'."
                )
            return mapping[key]
        if dtype in (torch.float32, torch.float16, torch.bfloat16):
            return dtype
        raise ValueError(f"Unsupported dtype {dtype!r}. Use float32, float16, or bfloat16.")

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

    def parse_rst(self, text: str) -> Any:
        """Parse raw text into an RST tree. Required override."""
        raise NotImplementedError(f"{type(self).__name__} must implement parse_rst")

    def parse_from_edus(self, edus: Sequence[str]) -> Any:
        """Parse pre-segmented EDUs into an RST tree. Required override."""
        raise NotImplementedError(f"{type(self).__name__} must implement parse_from_edus")

    def __call__(self, text: str) -> Any:
        return self.parse_rst(text)

    def analyse_with_evidence(
        self,
        text: str,
        edus: Sequence[Any] | None = None,
        sentence_boundaries: tuple[Any, ...] = (),
        paragraph_boundaries: tuple[Any, ...] = (),
        segmentation_source: str | None = None,
    ) -> Any:
        """Run inference and wrap exact substrate and parse evidence in PredictorAnalysisTrace."""
        from rdam.rst.contracts.document import DocumentToken, Edu as ContractEdu, TextSpan
        from rdam.rst.contracts.trace import PredictorAnalysisTrace
        from rdam.rst.erst.converter import du_to_analysis

        if edus is not None and len(edus) > 0:
            if isinstance(edus[0], ContractEdu):
                edu_texts = [e.text for e in edus]
            else:
                edu_texts = [str(e) for e in edus]
            res = self.parse_from_edus(edu_texts)
            used_source = segmentation_source or "presegmented"
        else:
            res = self.parse_rst(text)
            used_source = segmentation_source or "model"

        root_unit = res["rst"][0]
        analysis = du_to_analysis(root_unit, document_id="doc")

        import razdel

        sentences = list(razdel.sentenize(text))
        if not sentences:
            sentence_spans = [TextSpan(start=0, end=len(text), text=text)]
        else:
            sentence_spans = [
                TextSpan(start=s.start, end=s.stop, text=s.text)
                for s in sentences
            ]

        raw_tokens = list(razdel.tokenize(text))
        tokens: list[DocumentToken] = []
        for idx, t in enumerate(raw_tokens):
            s_id = 1
            for s_idx, s in enumerate(sentence_spans):
                if s.start <= t.start and t.stop <= s.end:
                    s_id = s_idx + 1
                    break
            tokens.append(
                DocumentToken(
                    token_id=idx + 1,
                    text=t.text,
                    start=t.start,
                    end=t.stop,
                    sentence_id=s_id,
                    paragraph_id=1,
                )
            )

        leaves: list[Any] = []
        self._collect_leaf_units(root_unit, leaves)
        contract_edus: list[ContractEdu] = []
        for idx, leaf in enumerate(leaves):
            l_start = leaf.start if getattr(leaf, "start", None) is not None else 0
            l_end = leaf.end if getattr(leaf, "end", None) is not None else len(leaf.text)
            tok_ids = tuple(
                tok.token_id for tok in tokens
                if tok.start >= l_start and tok.end <= l_end
            )
            contract_edus.append(
                ContractEdu(
                    edu_id=idx + 1,
                    text=leaf.text,
                    start=l_start,
                    end=l_end,
                    token_ids=tok_ids,
                )
            )

        resolved_sentences = tuple(sentence_boundaries) if sentence_boundaries else tuple(sentence_spans)
        resolved_paragraphs = tuple(paragraph_boundaries) if paragraph_boundaries else (TextSpan(start=0, end=len(text), text=text),)

        raw_inventory: list[str] = []
        for item in getattr(self, "relation_table", ()):
            base = item.split("_")[0] if "_" in item else item
            if base not in raw_inventory:
                raw_inventory.append(base)

        structure_decisions = tuple(self._collect_structure_decisions(root_unit, tuple(raw_inventory)))

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

    def _collect_structure_decisions(self, unit: Any, rel_table: tuple[str, ...]) -> list[Any]:
        from rdam.rst.contracts.trace import ParsedRstTreeEvidence, ParsedRstTreeSpan

        decisions: list[Any] = []
        curr_edu = 0

        def walk(node: Any) -> tuple[int, int]:
            nonlocal curr_edu
            left = getattr(node, "left", None)
            right = getattr(node, "right", None)
            if left is None and right is None:
                leaf_idx = curr_edu
                curr_edu += 1
                return leaf_idx, leaf_idx

            start_idx = curr_edu
            left_start, left_end = walk(left) if left is not None else (start_idx, start_idx)
            right_start, right_end = walk(right) if right is not None else (curr_edu - 1, curr_edu - 1)
            end_idx = right_end
            split_idx = left_end

            nuc = getattr(node, "nuclearity", "NS") or "NS"
            rel = getattr(node, "relation", "elaboration") or "elaboration"
            if "_" in rel:
                rel = rel.split("_")[0]
            canonical_rel = rel
            for candidate in rel_table:
                if candidate.lower() == rel.lower():
                    canonical_rel = candidate
                    break
            proba = float(getattr(node, "proba", 1.0) or 1.0)

            span = ParsedRstTreeSpan(
                start=start_idx,
                end=end_idx,
                split=split_idx,
                nuclearity=nuc,
                relation=canonical_rel,
                score=proba,
            )
            split_candidates = tuple(range(start_idx, end_idx)) if end_idx > start_idx else (split_idx,)
            split_logits = tuple(1.0 if idx == split_idx else 0.0 for idx in split_candidates)
            nuc_classes = ("NS", "SN", "NN")
            nuc_idx = nuc_classes.index(nuc) if nuc in nuc_classes else 0
            nuclearity_logits = tuple(1.0 if idx == nuc_idx else 0.0 for idx in range(3))

            if canonical_rel in rel_table:
                rel_idx = rel_table.index(canonical_rel)
                relation_logits = tuple(1.0 if idx == rel_idx else 0.0 for idx in range(len(rel_table)))
            else:
                relation_logits = tuple(1.0 if idx == 0 else 0.0 for idx in range(max(1, len(rel_table))))

            decisions.append(
                ParsedRstTreeEvidence(
                    span=span,
                    split_candidates=split_candidates,
                    split_logits=split_logits,
                    nuclearity_logits=nuclearity_logits,
                    relation_logits=relation_logits,
                )
            )
            return start_idx, end_idx

        walk(unit)
        return decisions

    def _collect_leaf_units(self, unit: Any, leaves: list[Any]) -> None:
        if getattr(unit, "left", None) is None and getattr(unit, "right", None) is None:
            leaves.append(unit)
            return
        if getattr(unit, "left", None) is not None:
            self._collect_leaf_units(unit.left, leaves)
        if getattr(unit, "right", None) is not None:
            self._collect_leaf_units(unit.right, leaves)

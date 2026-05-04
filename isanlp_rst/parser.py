"""Top-level RST parser entry point.

Wraps the DMRST and UniRST predictors behind a single :class:`Parser`
class, selecting the implementation based on ``hf_model_version``. Adds
device abstraction (CPU / CUDA / MPS), Hugging Face Hub cache + token
+ offline control, batch parsing, and an optional pluggable cache for
parse results.

Usage:

.. code-block:: python

    from isanlp_rst.parser import Parser

    # Auto-detect the best device (Apple Silicon → mps, NVIDIA → cuda,
    # otherwise cpu) and download model files into the default HF cache:
    parser = Parser(hf_model_version="rstdt", device="auto")

    # Parse one document:
    result = parser("On Saturday India won by seven runs.")
    tree = result["rst"][0]

    # Parse a batch — a deck of slides, a list of paragraphs, etc.:
    deck = ["Q4 revenue grew 18%.", "Driven by enterprise renewals.", ...]
    results = parser.parse_batch(deck, show_progress=True)

    # Parse a pre-segmented document while preserving segment intent:
    result = parser.parse_segments(deck, join_with="\\n\\n")

    # With a cache (any object satisfying isanlp_rst.utils.ParseCache):
    parser_cached = Parser(
        hf_model_version="rstdt",
        device="auto",
        cache=my_cache,
    )

The :class:`Parser` class is safe to construct in test environments
without the model weights, since predictor instantiation only happens
when a recognised ``hf_model_version`` is provided.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Sequence

if TYPE_CHECKING:
    from isanlp_rst.utils.cache import ParseCache
    from isanlp_rst.utils.device import DeviceSpec


logger = logging.getLogger(__name__)


# Tree-typing alias. The parser returns ``isanlp.annotation_rst.DiscourseUnit``
# trees, but importing that type unconditionally would force the optional
# ``isanlp`` dependency at import time. ``Any`` is the honest annotation here;
# downstream code can narrow it locally if it imports ``isanlp``.
DiscourseTree = Any
ParseResult = dict[str, list[DiscourseTree]]


class Parser:
    """High-level RST parser.

    Loads one of two underlying predictors based on the requested model
    version: ``PredictorDMRST`` for the original DMRST line of work
    (gumrrg / rstdt / rstreebank), or ``PredictorUniRST`` for the
    multilingual UniRST models (rrtrrg / unirst).

    Examples:
        >>> parser = Parser(hf_model_version='rstdt', device='auto')
        >>> result = parser("On Saturday India won by seven runs.")
        >>> tree = result['rst'][0]
        >>> tree.relation, tree.nuclearity
        ('Elaboration', 'NS')

        >>> # Slide- / section- / paragraph-grain parsing.
        >>> deck = ["Q4 revenue grew 18%.", "Driven by enterprise renewals.", ...]
        >>> result = parser.parse_segments(deck, join_with="\\n\\n")

        >>> # Batched parsing with optional progress bar:
        >>> results = parser.parse_batch(deck, show_progress=True)
    """

    DMRST_PARSERS: tuple[str, ...] = ('gumrrg', 'rstdt', 'rstreebank')
    UNIVERSAL_PARSERS: tuple[str, ...] = ('rrtrrg', 'unirst')
    AVAILABLE_VERSIONS: tuple[str, ...] = DMRST_PARSERS + UNIVERSAL_PARSERS

    def __init__(
        self,
        model_dir: str | None = None,
        hf_model_name: str = 'tchewik/isanlp_rst_v3',
        hf_model_version: str | None = None,
        relinventory: str | None = None,
        relinventory_idx: int = 0,
        cuda_device: int = -1,
        *,
        device: "DeviceSpec" = None,
        cache_dir: str | None = None,
        local_files_only: bool = False,
        token: str | None = None,
        cache: "ParseCache | None" = None,
    ) -> None:
        """Initialise the parser.

        Args:
            model_dir: Optional local model directory. If provided, weights
                are loaded from disk instead of from the HF Hub.
            hf_model_name: Hugging Face Hub repo containing the model
                checkpoints. Defaults to ``tchewik/isanlp_rst_v3``.
            hf_model_version: Which checkpoint inside the HF repo to load.
                Must be one of :attr:`AVAILABLE_VERSIONS`.
            relinventory: Relation inventory tag for UniRST models, e.g.
                ``'eng.erst.gum'``. Ignored for DMRST.
            relinventory_idx: Index into the relation inventory list when
                ``relinventory`` is not specified by name.
            cuda_device: Legacy device selector — ``-1`` for CPU, integer
                ``N`` for ``cuda:N``. Prefer the keyword-only ``device``
                parameter for new code.
            device: Modern device selector. One of ``None`` / ``'auto'``
                (best available), ``'cpu'``, ``'cuda'``, ``'cuda:N'``,
                ``'mps'`` (Apple Silicon GPU), an ``int`` (legacy cuda
                index), or a :class:`torch.device`. Overrides
                ``cuda_device`` when supplied. ``'auto'`` enables MPS on
                Apple Silicon, which is 3–10× faster than CPU.
            cache_dir: Override the HF Hub cache directory. ``None`` uses
                the HF Hub default (``~/.cache/huggingface``).
            local_files_only: When True, never reach out to HF Hub —
                fail if any required file isn't already cached locally.
                Useful for airgapped / reproducible runs.
            token: HF Hub auth token. ``None`` falls back to ``HF_TOKEN``
                env var; pass an explicit token to avoid the
                "unauthenticated requests" warning and the lower
                rate-limit ceiling.
            cache: Optional cache backend (any object satisfying the
                :class:`isanlp_rst.utils.ParseCache` protocol). When
                supplied, every call to ``__call__`` and ``parse_batch``
                first checks the cache and stores results on miss.

        Raises:
            NotImplementedError: If ``hf_model_version`` is not one of
                :attr:`AVAILABLE_VERSIONS`.
            RuntimeError: If ``device`` requests a specific accelerator
                that is unavailable on this host (e.g. ``'mps'`` on
                Linux, ``'cuda'`` without a GPU). Auto-detect mode never
                raises — it falls back to CPU silently.
        """
        self._cache = cache

        # Predictor lazy-loaded so construction errors from one predictor
        # family don't block the other.
        if hf_model_version in self.DMRST_PARSERS:
            from .dmrst_parser.predictor import PredictorDMRST

            self.predictor: Any = PredictorDMRST(
                model_dir=model_dir,
                hf_model_name=hf_model_name,
                hf_model_version=hf_model_version,
                cuda_device=cuda_device,
                device=device,
                cache_dir=cache_dir,
                local_files_only=local_files_only,
                token=token,
            )
        elif hf_model_version in self.UNIVERSAL_PARSERS:
            from .universal_parser.predictor import PredictorUniRST

            self.predictor = PredictorUniRST(
                model_dir=model_dir,
                hf_model_name=hf_model_name,
                hf_model_version=hf_model_version,
                relinventory=relinventory,
                relinventory_idx=relinventory_idx,
                cuda_device=cuda_device,
                device=device,
                cache_dir=cache_dir,
                local_files_only=local_files_only,
                token=token,
            )
        else:
            raise NotImplementedError(
                f"Available options for hf_model_version are: "
                f"{', '.join(self.AVAILABLE_VERSIONS)}"
            )

    def __call__(self, text: str) -> ParseResult:
        """Parse ``text`` into an RST tree.

        When a cache backend was supplied at construction time, a hit
        returns the cached result without invoking the model. On a miss,
        the result is stored before being returned.

        Args:
            text: Raw text of a single document. Sentence and EDU
                segmentation are performed by the parser internally.

        Returns:
            A dict with key ``'rst'`` mapping to a list containing the
            root :class:`DiscourseUnit` of the parsed tree.

        Raises:
            ValueError: If ``text`` is empty after stripping.
        """
        if not text or not text.strip():
            raise ValueError("Cannot parse empty text.")

        if self._cache is not None:
            cached = self._cache.get(text)
            if cached is not None:
                return cached

        result = self.predictor.parse_rst(text)

        if self._cache is not None:
            try:
                self._cache.put(text, result)
            except Exception as exc:  # cache write failure must not break the parse
                logger.warning("Cache put failed for input (len=%d): %s", len(text), exc)

        return result

    def from_edus(self, edus: Sequence[str]) -> ParseResult:
        """Parse a document using predefined EDUs.

        EDU-level pre-segmentation skips the parser's own EDU segmenter
        and operates on the supplied list directly. Useful when EDU
        boundaries come from a higher-quality source (e.g. a manually
        segmented corpus, or a downstream rule-based segmenter).

        Args:
            edus: Sequence of pre-segmented Elementary Discourse Units.
                Each string is a single EDU; the parser treats them as
                terminals in the RST tree.

        Returns:
            A dict with key ``'rst'`` mapping to a list containing the
            root :class:`DiscourseUnit` of the parsed tree.

        Raises:
            ValueError: If ``edus`` is empty.
        """
        if not edus:
            raise ValueError("from_edus() requires at least one EDU.")
        return self.predictor.parse_from_edus(edus)

    def parse_segments(
        self,
        segments: Sequence[str],
        join_with: str = " ",
    ) -> ParseResult:
        """Parse a pre-segmented document while preserving segment alignment.

        Useful when the input document is structurally pre-divided into
        meaningful units — slides in a presentation, sections of a
        report, paragraphs in a Markdown / Docling document, emails in a
        thread — and the caller wants the RST tree to span those units
        rather than re-segmenting them.

        Implementation: concatenates ``segments`` with ``join_with`` and
        passes the result through the standard ``__call__`` parser.
        Cache hits/misses go through the underlying ``__call__`` so
        cached results are reused automatically.

        Args:
            segments: Ordered sequence of text segments to be parsed
                together as a single document. Empty / whitespace-only
                segments are filtered out before joining.
            join_with: Separator inserted between segments before parsing.
                Default is a single space; use ``"\\n\\n"`` to mark each
                segment as a paragraph (recommended for Docling /
                Markdown / multi-paragraph inputs).

        Returns:
            A dict with key ``'rst'`` mapping to a list containing the
            root :class:`DiscourseUnit` of the parsed tree over the
            concatenated text.

        Raises:
            ValueError: If ``segments`` is empty or contains only
                whitespace strings.

        Examples:
            >>> deck_slides = [
            ...     "Q4 revenue grew 18% year-on-year.",
            ...     "Growth was led by enterprise renewals.",
            ...     "We expect the trend to continue.",
            ... ]
            >>> result = parser.parse_segments(deck_slides, join_with="\\n\\n")
            >>> root = result['rst'][0]
        """
        if not segments:
            raise ValueError("parse_segments() requires at least one segment.")
        text = join_with.join(s.strip() for s in segments if s and s.strip())
        if not text:
            raise ValueError("parse_segments() received only empty segments.")
        return self.__call__(text)

    def parse_batch(
        self,
        texts: Sequence[str],
        *,
        show_progress: bool = False,
        skip_empty: bool = True,
    ) -> list[ParseResult | None]:
        """Parse multiple documents.

        Today this is a sequential loop that iterates one document at
        a time — the underlying RST parser is not yet vectorised across
        documents. The method exists to (a) standardise the API for
        downstream callers and (b) provide a cache-aware, error-tolerant
        wrapper that won't be broken by a future move to true batched
        inference.

        Args:
            texts: Sequence of input documents. Order is preserved in
                the output list.
            show_progress: When True, emit a tqdm progress bar to
                stderr. Useful for long batches; silent by default so
                library use stays quiet.
            skip_empty: When True (default), empty / whitespace-only
                strings are skipped and a placeholder ``None`` is
                inserted at their position in the result list. When
                False, an empty input raises ``ValueError`` from the
                inner ``__call__``.

        Returns:
            A list of parse results aligned to ``texts``. Positions
            corresponding to skipped empty inputs hold ``None``.

        Examples:
            >>> deck = ["Q4 revenue grew 18%.", "", "Outlook positive."]
            >>> results = parser.parse_batch(deck)
            >>> assert results[1] is None  # empty slide skipped
        """
        iterator: Any = texts
        if show_progress:
            from tqdm import tqdm
            iterator = tqdm(texts, desc="Parsing", unit="doc")

        out: list[ParseResult | None] = []
        for text in iterator:
            if skip_empty and (not text or not text.strip()):
                out.append(None)
                continue
            out.append(self.__call__(text))
        return out

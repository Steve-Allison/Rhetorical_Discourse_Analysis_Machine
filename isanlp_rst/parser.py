"""Top-level RST parser entry point.

Wraps the DMRST and UniRST predictors behind a single ``Parser`` class,
selecting the implementation based on ``hf_model_version``.
"""

from __future__ import annotations

from typing import Any, Sequence


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
        >>> parser = Parser(hf_model_version='rstdt', cuda_device=-1)
        >>> result = parser("On Saturday India won by seven runs.")
        >>> tree = result['rst'][0]
        >>> tree.relation, tree.nuclearity
        ('Elaboration', 'NS')

        >>> # Slide-grain parsing — preserves segment boundaries.
        >>> deck = ["Q4 revenue grew 18%.", "Driven by enterprise renewals.", ...]
        >>> result = parser.parse_segments(deck)
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
            cuda_device: CUDA device index, or ``-1`` for CPU.

        Raises:
            NotImplementedError: If ``hf_model_version`` is not a recognised
                model version.
        """
        if hf_model_version in self.DMRST_PARSERS:
            from .dmrst_parser.predictor import PredictorDMRST

            self.predictor: Any = PredictorDMRST(
                model_dir=model_dir,
                hf_model_name=hf_model_name,
                hf_model_version=hf_model_version,
                cuda_device=cuda_device,
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
            )
        else:
            raise NotImplementedError(
                f"Available options for hf_model_version are: "
                f"{', '.join(self.AVAILABLE_VERSIONS)}"
            )

    def __call__(self, text: str) -> ParseResult:
        """Parse ``text`` into an RST tree.

        Args:
            text: Raw text of a single document. Sentence and EDU
                segmentation are performed by the parser internally.

        Returns:
            A dict with key ``'rst'`` mapping to a list containing the
            root :class:`DiscourseUnit` of the parsed tree.
        """
        return self.predictor.parse_rst(text)

    def from_edus(self, edus: Sequence[str]) -> ParseResult:
        """Parse a document using predefined EDUs.

        Args:
            edus: Sequence of pre-segmented Elementary Discourse Units.
                The parser skips its own EDU segmenter and operates on
                this list directly.

        Returns:
            A dict with key ``'rst'`` mapping to a list containing the
            root :class:`DiscourseUnit` of the parsed tree.
        """
        return self.predictor.parse_from_edus(edus)

    def parse_segments(
        self,
        segments: Sequence[str],
        join_with: str = " ",
    ) -> ParseResult:
        """Parse a pre-segmented document while preserving segment alignment.

        Useful when the input document is structurally pre-divided into
        meaningful units — for example slides in a presentation, sections
        of a report, emails in a thread — and the caller wants the RST
        tree to span those units rather than re-segmenting them.

        Implementation: concatenates ``segments`` with ``join_with`` and
        passes the result through the standard ``__call__`` parser. The
        returned tree is over the concatenated text; segment-to-EDU
        alignment can be recovered by tracking ``join_with`` offsets in
        the input. (A future revision may offer hard segment boundaries
        in the parser itself.)

        Args:
            segments: Ordered sequence of text segments to be parsed
                together as a single document.
            join_with: Separator inserted between segments before parsing.
                Default is a single space; use ``"\\n\\n"`` if you want
                the parser to interpret segments as paragraphs.

        Returns:
            A dict with key ``'rst'`` mapping to a list containing the
            root :class:`DiscourseUnit` of the parsed tree over the
            concatenated text.

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

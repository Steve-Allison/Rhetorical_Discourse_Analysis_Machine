import json
from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Any

from isanlp.annotation_rst import DiscourseUnit

from .dmrst_parser.predictor import PredictorDMRST
from .universal_parser.predictor import PredictorUniRST
from .utils.parse_result import ParseFailedError, extract_root_tree

__all__ = ["ParseFailedError", "Parser", "extract_root_tree"]

if TYPE_CHECKING:
    import torch
    from isanlp_rst.contracts import RstAnalysis, RstDocument, TextSpan


class Parser:
    """Public façade for the DMRST and UniRST parser families.

    The family is resolved in priority order:

    1. Explicit ``family='dmrst'|'unirst'`` argument.
    2. ``hf_model_version`` (mapped to a family via ``DMRST_PARSERS`` /
       ``UNIVERSAL_PARSERS``).
    3. ``model_dir`` content auto-detection (UniRST: ``data_manager_*.json``,
       legacy ``data_manager_*.pickle``, ``relation_table_*.txt``, or a
       ``config.json`` with ``data.corpora``; DMRST: ``relation_table.txt``).

    Device selection uses ``device=`` (``"auto"`` by default — CUDA if
    present, else MPS on Apple Silicon, else CPU). The legacy integer
    ``cuda_device=`` is still accepted but deprecated.

    Examples:
        >>> Parser(hf_model_version='gumrrg', device='cpu')               # DMRST
        >>> Parser(hf_model_version='unirst', relinventory='eng.erst.gum') # UniRST
        >>> Parser(model_dir='/path/to/checkpoint', family='dmrst')        # local
    """

    DMRST_PARSERS = ("gumrrg", "rstdt", "rstreebank")
    UNIVERSAL_PARSERS = ("rrtrrg", "unirst")
    AVAILABLE_VERSIONS = DMRST_PARSERS + UNIVERSAL_PARSERS
    AVAILABLE_FAMILIES = ("dmrst", "unirst")
    _DEFAULT_HF_MODEL_NAME = "tchewik/isanlp_rst_v3"

    def __init__(
        self,
        model_dir: str | None = None,
        hf_model_name: str | None = _DEFAULT_HF_MODEL_NAME,
        hf_model_version: str | None = None,
        relinventory: str | None = None,
        relinventory_idx: int = 0,
        device: str | torch.device | None = None,
        cuda_device: int | None = None,
        family: str | None = None,
        dtype: str | torch.dtype | None = None,
        segmenter: Any | None = None,
        segmenter_model: str | None = None,
        erst_scorer: Any | None = None,
        erst_scorer_model: str | None = None,
    ):
        if (
            model_dir is not None
            and hf_model_name is not None
            and hf_model_name != self._DEFAULT_HF_MODEL_NAME
        ):
            raise ValueError(
                "Pass either `model_dir` or `hf_model_name`, not both. "
                "When loading from disk, omit hf_model_name (or leave the default)."
            )

        resolved_family = self._resolve_family(model_dir, hf_model_version, family)

        self.family = resolved_family
        self.hf_model_name = hf_model_name
        self.hf_model_version = hf_model_version
        self.relinventory = relinventory

        # When loading from disk, suppress the default HF repo name so the
        # predictor unambiguously selects local mode.
        effective_hf_name = None if model_dir is not None else hf_model_name

        match resolved_family:
            case "dmrst":
                self.predictor = PredictorDMRST(
                    model_dir=model_dir,
                    hf_model_name=effective_hf_name,
                    hf_model_version=hf_model_version,
                    device=device,
                    cuda_device=cuda_device,
                    dtype=dtype,
                )
            case "unirst":
                self.predictor = PredictorUniRST(
                    model_dir=model_dir,
                    hf_model_name=effective_hf_name,
                    hf_model_version=hf_model_version,
                    relinventory=relinventory,
                    relinventory_idx=relinventory_idx,
                    device=device,
                    cuda_device=cuda_device,
                    dtype=dtype,
                )
            case _:
                raise ValueError(f"Unknown family {resolved_family!r}.")

        if segmenter is not None:
            self.segmenter = segmenter
        elif segmenter_model is not None:
            from isanlp_rst.segmentation.transformer_segmenter import TransformerEduSegmenter

            self.segmenter = TransformerEduSegmenter(
                model_name_or_path=segmenter_model,
                device=device or "auto",
            )
        else:
            self.segmenter = None

        if erst_scorer is not None:
            self.erst_scorer = erst_scorer
        elif erst_scorer_model is not None:
            from isanlp_rst.erst.neural_scorer import NeuralSecondaryEdgeScorer

            self.erst_scorer = NeuralSecondaryEdgeScorer(
                model_name_or_path=erst_scorer_model,
                device=device or "auto",
            )
        else:
            self.erst_scorer = None

    @classmethod
    def _resolve_family(
        cls,
        model_dir: str | None,
        hf_model_version: str | None,
        family: str | None,
    ) -> str:
        if family is not None:
            if family not in cls.AVAILABLE_FAMILIES:
                raise ValueError(
                    f"Unknown family {family!r}. Available: {cls.AVAILABLE_FAMILIES}."
                )
            if hf_model_version is None and model_dir is None:
                raise ValueError(
                    f"family={family!r} requires hf_model_version or model_dir."
                )
            if hf_model_version is not None:
                allowed = (
                    cls.DMRST_PARSERS if family == "dmrst" else cls.UNIVERSAL_PARSERS
                )
                if hf_model_version not in allowed:
                    raise ValueError(
                        f"hf_model_version={hf_model_version!r} is not valid for "
                        f"family={family!r}. Expected one of {allowed}."
                    )
            if model_dir is not None:
                detected = cls._detect_family_from_model_dir(model_dir)
                if detected is not None and detected != family:
                    raise ValueError(
                        f"family={family!r} does not match model_dir signatures "
                        f"(detected {detected!r} from {model_dir!r}). "
                        f"Pass family={detected!r}, or use a matching checkpoint."
                    )
            return family

        if hf_model_version is not None:
            if hf_model_version in cls.DMRST_PARSERS:
                return "dmrst"
            if hf_model_version in cls.UNIVERSAL_PARSERS:
                return "unirst"
            raise ValueError(
                f"Unknown hf_model_version {hf_model_version!r}. "
                f"Available: {cls.AVAILABLE_VERSIONS}."
            )

        if model_dir is not None:
            detected = cls._detect_family_from_model_dir(model_dir)
            if detected is None:
                raise ValueError(
                    f"Cannot auto-detect parser family from model_dir={model_dir!r}. "
                    f"Pass family='dmrst' or family='unirst' explicitly."
                )
            return detected

        raise ValueError(
            "Pass `hf_model_version` or `model_dir` (with `family` for local-disk loading). "
            f"Available versions: {cls.AVAILABLE_VERSIONS}."
        )

    @staticmethod
    def _detect_family_from_model_dir(model_dir: str) -> str | None:
        """Inspect a local checkpoint directory and infer the parser family.

        Returns ``'unirst'``, ``'dmrst'``, or ``None`` if no signature matches.
        Published HuggingFace UniRST layouts still ship
        ``data_manager_*.pickle``; those remain a detection signature. Native
        inventories are ``data_manager_*.json`` or ``relation_table_<corpus>.txt``.
        """
        root = Path(model_dir)
        if Parser._has_unirst_inventory(root):
            return "unirst"

        cfg = Parser._safe_load_json(root / "config.json")
        if cfg is not None and "corpora" in cfg.get("data", {}):
            return "unirst"

        if (root / "relation_table.txt").is_file():
            return "dmrst"

        return None

    @staticmethod
    def _has_unirst_inventory(root: Path) -> bool:
        search_roots = (root, root / "data", root / "data" / "dms")
        patterns = (
            "data_manager_*.pickle",
            "data_manager_*.json",
            "relation_table_*.txt",
        )
        return any(
            path
            for directory in search_roots
            for pattern in patterns
            for path in directory.glob(pattern)
        )

    @staticmethod
    def _safe_load_json(path: Path) -> dict | None:
        """Read ``path`` as JSON. Returns ``None`` if the file is missing,
        unreadable, or contains malformed JSON.
        """
        if not path.is_file():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

    def __call__(self, text: str):
        return self.predictor.parse_rst(text)

    def parse_tree(self, text: str) -> DiscourseUnit:
        """Parse text and return a typed RST root instead of the legacy mapping payload.

        This is the supported boundary for typed consumers. Predictor-internal
        transport remains encapsulated inside this package.
        """
        result = self.predictor.parse_rst(text)
        root = extract_root_tree(result)
        if not isinstance(root, DiscourseUnit):
            raise ParseFailedError(
                "Parser produced an RST root with the wrong runtime type: "
                f"{type(root).__name__}."
            )
        return root

    def from_edus(self, edus: Sequence[str]):
        """Parse a document using predefined EDUs."""
        return self.predictor.parse_from_edus(edus)

    def parse_document(
        self,
        document: RstDocument,
        output: str = "rst_tree",
        prime_markers: bool = True,
    ) -> RstAnalysis:
        """Parse an RstDocument into a typed, ontology-aligned RstAnalysis."""
        import time
        from isanlp_rst.contracts import OutputFormalismEnum, ProvenanceRecord, RstAnalysis, TimingRecord
        from isanlp_rst.english.relations.primer import DiscourseMarkerPrimer
        from isanlp_rst.erst.converter import du_to_analysis

        start_t = time.perf_counter()
        segmenter = getattr(self, "segmenter", None)
        if document.edus is not None:
            raw_res = self.predictor.parse_from_edus([edu.text for edu in document.edus])
        elif segmenter is not None:
            segmented_edus = segmenter.segment(document.text)
            raw_res = self.predictor.parse_from_edus([edu.text for edu in segmented_edus])
        else:
            raw_res = self.predictor.parse_rst(document.text)
        elapsed_ms = (time.perf_counter() - start_t) * 1000.0

        root_unit = extract_root_tree(raw_res)
        base_analysis = du_to_analysis(root_unit, document_id=document.document_id)

        formalism = OutputFormalismEnum(output)
        prov = ProvenanceRecord(
            producer="isanlp_rst.parser",
            software_version="1.0.0",
            model_id=self.hf_model_version or str(getattr(self.predictor, "model_dir", "unknown")),
            ontology_version="4.1.0-discourse",
        )
        timing = TimingRecord(parsing_ms=elapsed_ms, total_ms=elapsed_ms)

        analysis = RstAnalysis(
            document_id=base_analysis.document_id,
            formalism=formalism,
            nodes=base_analysis.nodes,
            primary_edges=base_analysis.primary_edges,
            secondary_edges=base_analysis.secondary_edges,
            signals=base_analysis.signals,
            provenance=prov,
            timing=timing,
            warnings=base_analysis.warnings,
            failure_code=base_analysis.failure_code,
        )

        if prime_markers:
            primer = DiscourseMarkerPrimer()
            analysis = primer.prime_analysis(analysis, document)

        if formalism == OutputFormalismEnum.ERST_GRAPH or output == "erst_graph":
            from isanlp_rst.english.erst.completer import ErstCompleter

            completer = ErstCompleter()
            scorer = getattr(self, "erst_scorer", None)
            analysis = completer.complete_graph(document, analysis, neural_scorer=scorer)

        return analysis

    def parse_hierarchical(
        self,
        document: RstDocument,
        custom_boundaries: Sequence[TextSpan] | None = None,
        output: str = "rst_tree",
    ) -> RstAnalysis:
        """Parse a multi-section or long document using two-stage macro/micro parsing.

        1. Parses each section or paragraph independently as a self-contained local subtree.
        2. Parses the macro-level relationships connecting section root nodes.
        3. Stitches them into a single coherent, valid document RstAnalysis tree.
        """
        from isanlp_rst.hierarchical.stitcher import HierarchicalSectionStitcher

        stitcher = HierarchicalSectionStitcher(parser=self)
        return stitcher.parse_hierarchical(
            document=document,
            custom_boundaries=custom_boundaries,
            output=output,
        )



import json
from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .annotation_rst import DiscourseUnit
from .transformer_parser.predictor import PredictorModernBERT
from .utils.parse_result import ParseFailedError, extract_root_tree

__all__ = ["ParseFailedError", "Parser", "extract_root_tree"]

if TYPE_CHECKING:
    import torch
    from isanlp_rst.contracts import RstAnalysis, RstDocument, TextSpan
    from isanlp_rst.model_loading import ModelReleaseIdentity, ParserCapacity


class Parser:
    """Public façade for Modern pure transformer discourse parsing.

    Modern Pure Transformer Parser is the production default:
        >>> Parser(family="modernbert", device="auto")
        >>> Parser.from_model_release('/models', 'modernbert-v5', family='modernbert')
    """

    MODERNBERT_PARSERS = ("modernbert", "modernbert-base", "modernbert-large")
    DMRST_PARSERS = ("gumrrg", "rstdt", "rstreebank")
    UNIVERSAL_PARSERS = ("rrtrrg", "unirst")
    AVAILABLE_VERSIONS = MODERNBERT_PARSERS + DMRST_PARSERS + UNIVERSAL_PARSERS
    AVAILABLE_FAMILIES = ("modernbert", "dmrst", "unirst")
    _DEFAULT_HF_MODEL_NAME = "answerdotai/ModernBERT-base"
    predictor: Any

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
        erst_scorer_checkpoint: str | Path | None = None,
        _validated_model_release: Any | None = None,
    ):
        if model_dir is not None and hf_model_name is not None and hf_model_name != self._DEFAULT_HF_MODEL_NAME:
            raise ValueError(
                "Pass either `model_dir` or `hf_model_name`, not both. "
                "When loading from disk, omit hf_model_name (or leave the default)."
            )

        resolved_family = self._resolve_family(model_dir, hf_model_version, family)
        if model_dir is not None:
            if _validated_model_release is None:
                from isanlp_rst.model_loading import validate_model_release

                _validated_model_release = validate_model_release(
                    model_dir,
                    expected_runtime_contract=f"isanlp_rst.parser/{resolved_family}-v1",
                )
            if Path(model_dir).resolve() != _validated_model_release.path:
                raise ValueError("validated model release does not match model_dir")

        self.family = resolved_family
        self.hf_model_name = hf_model_name
        self.hf_model_version = hf_model_version
        self.relinventory = relinventory
        self._validated_model_release = _validated_model_release

        match resolved_family:
            case "modernbert":
                model_size = "large" if (hf_model_version == "modernbert-large" or (model_dir and "large" in str(model_dir))) else "base"
                self.predictor = PredictorModernBERT(
                    model_size=model_size,
                    model_dir=model_dir,
                    device=device or "auto",
                    torch_dtype=dtype or "auto",
                )
            case "dmrst" | "unirst":
                raise ValueError(
                    f"Legacy {resolved_family!r} has been archived from production. Use family='modernbert' for production parsing."
                )
            case _:
                raise ValueError(f"Unknown family {resolved_family!r}.")

        if segmenter is not None:
            self.segmenter = segmenter
        elif segmenter_model is not None:
            from isanlp_rst.segmentation.transformer_segmenter import TransformerEduSegmenter

            self.segmenter = TransformerEduSegmenter(
                model_name_or_path=segmenter_model,
                device=self.predictor._device,
            )
        else:
            self.segmenter = None

        from isanlp_rst.erst.checkpoint import load_erst_checkpoint_bundle, resolve_default_erst_checkpoint

        resolved_erst = resolve_default_erst_checkpoint(erst_scorer_checkpoint)
        if resolved_erst is not None:
            self.erst_checkpoint = load_erst_checkpoint_bundle(
                resolved_erst,
                device=self.predictor._device,
            )
        else:
            self.erst_checkpoint = None

    @property
    def analysis_capacity(self) -> ParserCapacity:
        """Return the safe recursive-analysis capacity in the parser's limiting unit."""

        from isanlp_rst.model_loading import ParserCapacity

        return ParserCapacity(unit="edu_count", maximum=512, source="isanlp_rst.parser/recursive-v1")

    @property
    def model_release_identity(self) -> ModelReleaseIdentity | None:
        """Return immutable released-model identity, or ``None`` for mutable/HF construction."""

        release = self._validated_model_release
        if release is None:
            return None
        return release.analysis_identity(self.analysis_capacity)

    @classmethod
    def from_model_release(
        cls,
        store: str | Path,
        release_id: str,
        *,
        family: str,
        relinventory: str | None = None,
        relinventory_idx: int = 0,
        device: str | torch.device | None = None,
        cuda_device: int | None = None,
        dtype: str | torch.dtype | None = None,
        segmenter: Any | None = None,
        segmenter_model: str | None = None,
        erst_scorer_checkpoint: str | Path | None = None,
    ) -> "Parser":
        """Validate and load one immutable child of the production model store."""

        if family not in cls.AVAILABLE_FAMILIES:
            raise ValueError(f"Unknown family {family!r}. Available: {cls.AVAILABLE_FAMILIES}.")
        from isanlp_rst.model_loading import load_model_release

        release = load_model_release(
            store,
            release_id,
            expected_runtime_contract=f"isanlp_rst.parser/{family}-v1",
        )
        return cls(
            model_dir=str(release.path),
            hf_model_name=None,
            family=family,
            relinventory=relinventory,
            relinventory_idx=relinventory_idx,
            device=device,
            cuda_device=cuda_device,
            dtype=dtype,
            segmenter=segmenter,
            segmenter_model=segmenter_model,
            erst_scorer_checkpoint=erst_scorer_checkpoint,
            _validated_model_release=release,
        )

    @classmethod
    def _resolve_family(
        cls,
        model_dir: str | None,
        hf_model_version: str | None,
        family: str | None,
    ) -> str:
        if family is not None:
            if family not in cls.AVAILABLE_FAMILIES:
                raise ValueError(f"Unknown family {family!r}. Available: {cls.AVAILABLE_FAMILIES}.")
            if family == "modernbert":
                return "modernbert"
            if hf_model_version is None and model_dir is None:
                raise ValueError(f"family={family!r} requires hf_model_version or model_dir.")
            if hf_model_version is not None:
                allowed = cls.DMRST_PARSERS if family == "dmrst" else cls.UNIVERSAL_PARSERS
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
            if hf_model_version in cls.MODERNBERT_PARSERS:
                return "modernbert"
            if hf_model_version in cls.DMRST_PARSERS:
                return "dmrst"
            if hf_model_version in cls.UNIVERSAL_PARSERS:
                return "unirst"
            raise ValueError(f"Unknown hf_model_version {hf_model_version!r}. Available: {cls.AVAILABLE_VERSIONS}.")

        if model_dir is not None:
            detected = cls._detect_family_from_model_dir(model_dir)
            if detected is None:
                raise ValueError(
                    f"Cannot auto-detect parser family from model_dir={model_dir!r}. "
                    f"Pass family='dmrst', 'unirst', or 'modernbert' explicitly."
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
        return any(path for directory in search_roots for pattern in patterns for path in directory.glob(pattern))

    @staticmethod
    def _safe_load_json(path: Path) -> dict | None:
        """Read ``path`` as JSON. Returns ``None`` if the file is missing,
        unreadable, or contains malformed JSON.
        """
        if not path.is_file():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except OSError, json.JSONDecodeError:
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
            raise ParseFailedError(f"Parser produced an RST root with the wrong runtime type: {type(root).__name__}.")
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
        from isanlp_rst._provenance import resolve_package_version, resolve_source_revision
        from isanlp_rst.contracts import OutputFormalismEnum, ProvenanceRecord, RstAnalysis, TimingRecord
        from isanlp_rst.english.relations.primer import DiscourseMarkerPrimer
        from isanlp_rst.erst.converter import du_to_analysis

        formalism = OutputFormalismEnum(output)
        erst_checkpoint = getattr(self, "erst_checkpoint", None)
        if formalism == OutputFormalismEnum.ERST_GRAPH and erst_checkpoint is None:
            from isanlp_rst.erst.checkpoint import ErstCapabilityError

            raise ErstCapabilityError(
                "output='erst_graph' requires a validated completion bundle via "
                "Parser(erst_scorer_checkpoint=...)"
            )

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

        prov = ProvenanceRecord(
            producer="isanlp_rst.parser",
            software_version=resolve_package_version(),
            source_revision=resolve_source_revision(),
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
            from isanlp_rst.english.erst.completer import CompleterConfig, ErstCompleter

            if erst_checkpoint is None:
                raise RuntimeError("validated eRST checkpoint disappeared during parsing")
            completer = ErstCompleter(
                config=CompleterConfig(
                    min_confidence_threshold=erst_checkpoint.decoder_config.edge_threshold,
                ),
                signal_detector=erst_checkpoint.signal_detector,
                decoder_config=erst_checkpoint.decoder_config,
            )
            analysis = completer.complete_graph(
                document,
                analysis,
                neural_scorer=erst_checkpoint.scorer,
            )

        return analysis

    def parse_documents(
        self,
        documents: Sequence[RstDocument],
        batch_size: int = 16,
        output: str = "rst_tree",
        prime_markers: bool = True,
    ) -> list[RstAnalysis]:
        """Parse a sequence of documents in high-throughput batches.

        Args:
            documents: Sequence of RstDocument instances to parse.
            batch_size: Maximum batch size per forward pass.
            output: Formalism alias ('rst_tree' or 'erst_graph').
            prime_markers: Whether to apply lexical discourse marker priming.

        Returns:
            list[RstAnalysis]: Analyzed discourse results corresponding to the input documents.
        """
        import time
        from isanlp_rst._provenance import resolve_package_version, resolve_source_revision
        from isanlp_rst.contracts import OutputFormalismEnum, ProvenanceRecord, RstAnalysis, TimingRecord
        from isanlp_rst.erst.checkpoint import ErstCapabilityError
        from isanlp_rst.erst.converter import du_to_analysis
        from isanlp_rst.relations.primer import DiscourseMarkerPrimer

        if not documents:
            return []
        if batch_size <= 0:
            raise ValueError(f"batch_size must be positive, got {batch_size}")

        formalism = OutputFormalismEnum(output)
        erst_checkpoint = getattr(self, "erst_checkpoint", None)
        if formalism == OutputFormalismEnum.ERST_GRAPH and erst_checkpoint is None:
            raise ErstCapabilityError(
                "output='erst_graph' requires a validated completion bundle via "
                "Parser(erst_scorer_checkpoint=...)"
            )

        segmenter = getattr(self, "segmenter", None)
        parse_rst_batch_fn = getattr(self.predictor, "parse_rst_batch", None)

        if (
            all(doc.edus is None for doc in documents)
            and segmenter is None
            and parse_rst_batch_fn is not None
        ):
            start_t = time.perf_counter()
            texts = [doc.text for doc in documents]
            batch_raw_res: list[dict[str, Any]] = parse_rst_batch_fn(texts, batch_size=batch_size)
            elapsed_ms = ((time.perf_counter() - start_t) * 1000.0) / max(1, len(documents))

            results: list[RstAnalysis] = []
            for doc, raw_res in zip(documents, batch_raw_res, strict=True):
                root_unit = extract_root_tree(raw_res)
                base_analysis = du_to_analysis(root_unit, document_id=doc.document_id)

                prov = ProvenanceRecord(
                    producer="isanlp_rst.parser",
                    software_version=resolve_package_version(),
                    source_revision=resolve_source_revision(),
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
                    analysis = primer.prime_analysis(analysis, doc)

                if formalism == OutputFormalismEnum.ERST_GRAPH:
                    from isanlp_rst.english.erst.completer import CompleterConfig, ErstCompleter

                    if erst_checkpoint is None:
                        raise RuntimeError("validated eRST checkpoint disappeared during parsing")
                    completer = ErstCompleter(
                        config=CompleterConfig(
                            min_confidence_threshold=erst_checkpoint.decoder_config.edge_threshold,
                        ),
                        signal_detector=erst_checkpoint.signal_detector,
                        decoder_config=erst_checkpoint.decoder_config,
                    )
                    analysis = completer.complete_graph(
                        doc,
                        analysis,
                        neural_scorer=erst_checkpoint.scorer,
                    )

                results.append(analysis)
            return results

        return [
            self.parse_document(
                doc,
                output=output,
                prime_markers=prime_markers,
            )
            for doc in documents
        ]

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

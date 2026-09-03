import json
from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import torch

from .annotation_rst import DiscourseUnit
from .dmrst_parser.predictor import PredictorDMRST
from .universal_parser.predictor import PredictorUniRST
from .utils.parse_result import ParseFailedError, extract_root_tree

__all__ = ["ParseFailedError", "Parser", "extract_root_tree"]

if TYPE_CHECKING:
    from rdam.rst.contracts import RstAnalysis, RstDocument, TextSpan
    from rdam.rst.ingest.contracts.analysis import AnalysisPolicy, ParserAnalysisResult
    from rdam.rst.ingest.contracts.inference import CompositeAnalysisIdentity
    from rdam.rst.model_loading import ModelReleaseIdentity, ParserCapacity


class Parser:
    """Public façade for the DMRST and UniRST discourse parser families.

    Examples:
        >>> Parser()                                                        # DMRST (gumrrg, default)
        >>> Parser(hf_model_version='gumrrg', device='auto')               # DMRST
        >>> Parser(hf_model_version='unirst', relinventory='eng.erst.gum') # UniRST
        >>> Parser.from_model_release('/models', 'gumrrg-v3', family='dmrst')
    """

    DMRST_PARSERS = ("gumrrg", "rstdt", "rstreebank")
    UNIVERSAL_PARSERS = ("rrtrrg", "unirst")
    AVAILABLE_VERSIONS = DMRST_PARSERS + UNIVERSAL_PARSERS
    AVAILABLE_FAMILIES = ("dmrst", "unirst")
    _DEFAULT_HF_MODEL_NAME = "tchewik/isanlp_rst_v3"
    DEFAULT_HF_MODEL_VERSION = "gumrrg"
    _DEFAULT_HF_MODEL_VERSION = DEFAULT_HF_MODEL_VERSION
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
    ) -> None:
        if model_dir is not None and hf_model_name is not None and hf_model_name != self._DEFAULT_HF_MODEL_NAME:
            raise ValueError(
                "Pass either `model_dir` or `hf_model_name`, not both. "
                "When loading from disk, omit hf_model_name (or leave the default)."
            )

        if model_dir is None and hf_model_version is None and family is None:
            hf_model_version = self._DEFAULT_HF_MODEL_VERSION
            family = "dmrst"

        resolved_family = self._resolve_family(model_dir, hf_model_version, family)
        if model_dir is not None:
            if _validated_model_release is None:
                from rdam.rst.model_loading import validate_model_release

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

        if _validated_model_release is not None:
            self.predictor.loaded_release_files = _validated_model_release.manifest.files

        if segmenter is not None:
            self.segmenter = segmenter
        elif segmenter_model is not None:
            from rdam.rst.segmentation.transformer_segmenter import TransformerEduSegmenter

            self.segmenter = TransformerEduSegmenter(
                model_name_or_path=segmenter_model,
                device=self.predictor._device,
            )
        else:
            self.segmenter = None

        from rdam.rst.erst.checkpoint import load_erst_checkpoint_bundle, resolve_default_erst_checkpoint

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

        from rdam.rst.model_loading import ParserCapacity

        return ParserCapacity(unit="edu_count", maximum=512, source="isanlp_rst.parser/recursive-v1")

    @property
    def model_release_identity(self) -> ModelReleaseIdentity | None:
        """Return immutable released-model identity, or ``None`` for mutable/HF construction."""

        release = self._validated_model_release
        if release is None:
            return None
        return release.analysis_identity(self.analysis_capacity)

    @classmethod
    def family_for_runtime_contract(cls, runtime_contract: str) -> str:
        """Resolve canonical parser family from runtime contract string."""
        prefix = "isanlp_rst.parser/"
        if not runtime_contract.startswith(prefix):
            raise ValueError(f"Invalid parser runtime contract prefix: {runtime_contract!r}")
        suffix = runtime_contract[len(prefix) :]
        family = suffix.split("-v", 1)[0]
        if family not in cls.AVAILABLE_FAMILIES:
            raise ValueError(
                f"Unknown parser family {family!r} for contract {runtime_contract!r}. Available: {cls.AVAILABLE_FAMILIES}"
            )
        return family

    @classmethod
    def from_model_release(
        cls,
        store: str | Path,
        release_id: str,
        *,
        family: str | None = None,
        relinventory: str | None = None,
        relinventory_idx: int = 0,
        device: str | torch.device | None = None,
        cuda_device: int | None = None,
        dtype: str | torch.dtype | None = None,
        segmenter: Any | None = None,
        segmenter_model: str | None = None,
        erst_scorer_checkpoint: str | Path | None = None,
    ) -> Parser:
        """Validate and load one immutable child of the production model store."""

        from rdam.rst.model_loading import load_model_release, peek_runtime_contract

        if family is None:
            contract = peek_runtime_contract(Path(store) / release_id)
            family = cls.family_for_runtime_contract(contract)
        elif family not in cls.AVAILABLE_FAMILIES:
            raise ValueError(f"Unknown family {family!r}. Available: {cls.AVAILABLE_FAMILIES}.")

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
                    f"Pass family='dmrst' or 'unirst' explicitly."
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
        if cfg is not None:
            data = cfg.get("data")
            if isinstance(data, dict) and "corpora" in cast(dict[object, object], data):
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
    def _safe_load_json(path: Path) -> dict[str, object] | None:
        """Read ``path`` as JSON. Returns ``None`` if the file is missing,
        unreadable, or contains malformed JSON.
        """
        if not path.is_file():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except OSError, json.JSONDecodeError:
            return None
        if not isinstance(payload, dict):
            return None
        return cast(dict[str, object], payload)

    def __call__(self, text: str) -> dict[str, Any]:
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

    def from_edus(self, edus: Sequence[str]) -> dict[str, Any]:
        """Parse a document using predefined EDUs."""
        return self.predictor.parse_from_edus(edus)

    def analyse_document(
        self,
        document: RstDocument,
        *,
        analysis_policy: AnalysisPolicy | None = None,
    ) -> ParserAnalysisResult:
        """Return the canonical evidence-complete analysis of one exact document."""

        import time

        from rdam.rst.english.erst.completer import CompleterConfig, ErstCompleter
        from rdam.rst.ingest.contracts.analysis import (
            AnalysisPolicy,
            MarkerRefinementMode,
        )
        from rdam.rst.ingest.contracts.inference import OutputFormalism
        from rdam.rst.ingest.parser_result import build_parser_analysis_result
        from rdam.rst.ingest.service import DEFAULT_ANALYSIS_POLICY
        from rdam.rst.relations.primer import DiscourseMarkerPrimer

        policy = AnalysisPolicy.model_validate((analysis_policy or DEFAULT_ANALYSIS_POLICY).model_dump())
        if policy.output_formalism is OutputFormalism.ERST_GRAPH and self.erst_checkpoint is None:
            from rdam.rst.erst.checkpoint import ErstCapabilityError

            raise ErstCapabilityError("output_formalism='erst_graph' requires a validated completion bundle")
        started = time.perf_counter()
        segmentation_source: str | None = None
        edus = document.edus
        if edus is None and self.segmenter is not None:
            edus = self.segmenter.segment(document.text)
            segmentation_source = "model"
        trace = self.predictor.analyse_with_evidence(
            document.text,
            edus=edus,
            sentence_boundaries=document.sentence_boundaries,
            paragraph_boundaries=document.paragraph_boundaries,
            segmentation_source=segmentation_source,
        )
        model_analysis = _analysis_with_document_identity(
            trace.analysis,
            document_id=document.document_id,
            elapsed_ms=(time.perf_counter() - started) * 1_000.0,
            model_id=self.hf_model_version or str(getattr(self.predictor, "model_dir", "unknown")),
        )
        if policy.marker_refinement is MarkerRefinementMode.EVIDENCE_PRESERVING:
            primary_analysis = DiscourseMarkerPrimer().prime_analysis(model_analysis, document)
        else:
            primary_analysis = model_analysis
        erst_trace = None
        final_analysis = primary_analysis
        if policy.output_formalism is OutputFormalism.ERST_GRAPH:
            checkpoint = self.erst_checkpoint
            if checkpoint is None:
                raise RuntimeError("validated eRST checkpoint disappeared during analysis")
            completer = ErstCompleter(
                config=CompleterConfig(
                    min_confidence_threshold=checkpoint.decoder_config.edge_threshold,
                ),
                signal_detector=checkpoint.signal_detector,
                decoder_config=checkpoint.decoder_config,
            )
            erst_trace = completer.complete_graph_with_evidence(
                document,
                primary_analysis,
                neural_scorer=checkpoint.scorer,
            )
            final_analysis = erst_trace.analysis
        duration_ms = (time.perf_counter() - started) * 1_000.0
        return build_parser_analysis_result(
            self,
            document,
            trace,
            policy=policy,
            model_analysis=model_analysis,
            final_analysis=final_analysis,
            erst_trace=erst_trace,
            duration_ms=duration_ms,
        )

    def parse_document(
        self,
        document: RstDocument,
        output: str = "rst_tree",
        prime_markers: bool = True,
    ) -> RstAnalysis:
        """Project the canonical parser result to its final graph."""

        from rdam.rst.ingest.contracts.analysis import AnalysisPolicy, MarkerRefinementMode
        from rdam.rst.ingest.contracts.inference import OutputFormalism
        from rdam.rst.ingest.service import DEFAULT_ANALYSIS_POLICY

        policy = AnalysisPolicy.model_validate(
            {
                **DEFAULT_ANALYSIS_POLICY.model_dump(exclude={"semantic_digest"}),
                "output_formalism": OutputFormalism(output),
                "marker_refinement": (
                    MarkerRefinementMode.EVIDENCE_PRESERVING if prime_markers else MarkerRefinementMode.DISABLED
                ),
            }
        )
        return self.analyse_document(document, analysis_policy=policy).semantic.analysis

    def complete_erst_document(
        self,
        document: RstDocument,
        primary_result: ParserAnalysisResult,
        *,
        analysis_policy: AnalysisPolicy,
    ) -> ParserAnalysisResult:
        """Add global eRST evidence to a complete validated primary result."""

        from rdam.rst.english.erst.completer import CompleterConfig, ErstCompleter
        from rdam.rst.erst.checkpoint import ErstCapabilityError
        from rdam.rst.ingest.parser_result import complete_parser_analysis_result_with_erst

        checkpoint = self.erst_checkpoint
        if checkpoint is None:
            raise ErstCapabilityError("output_formalism='erst_graph' requires a validated completion bundle")
        completer = ErstCompleter(
            config=CompleterConfig(
                min_confidence_threshold=checkpoint.decoder_config.edge_threshold,
            ),
            signal_detector=checkpoint.signal_detector,
            decoder_config=checkpoint.decoder_config,
        )
        trace = completer.complete_graph_with_evidence(
            document,
            primary_result.semantic.analysis,
            neural_scorer=checkpoint.scorer,
        )
        return complete_parser_analysis_result_with_erst(
            self,
            document,
            primary_result,
            trace,
            policy=analysis_policy,
        )

    def describe_analysis_identity(
        self,
        *,
        analysis_policy: AnalysisPolicy,
        segmentation_source: str,
    ) -> CompositeAnalysisIdentity:
        """Return the exact composite runtime identity without running inference."""

        from rdam.rst.ingest.parser_result import describe_analysis_components

        composite, _ = describe_analysis_components(
            self,
            segmentation_source=segmentation_source,
            policy=analysis_policy,
        )
        return composite

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
        from rdam.rst._provenance import resolve_package_version, resolve_source_revision
        from rdam.rst.contracts import OutputFormalismEnum, ProvenanceRecord, RstAnalysis, TimingRecord
        from rdam.rst.erst.checkpoint import ErstCapabilityError
        from rdam.rst.erst.converter import du_to_analysis
        from rdam.rst.relations.primer import DiscourseMarkerPrimer

        if not documents:
            return []
        if batch_size <= 0:
            raise ValueError(f"batch_size must be positive, got {batch_size}")

        formalism = OutputFormalismEnum(output)
        erst_checkpoint = getattr(self, "erst_checkpoint", None)
        if formalism == OutputFormalismEnum.ERST_GRAPH and erst_checkpoint is None:
            raise ErstCapabilityError(
                "output='erst_graph' requires a validated completion bundle via Parser(erst_scorer_checkpoint=...)"
            )

        segmenter = getattr(self, "segmenter", None)
        parse_rst_batch_fn = getattr(self.predictor, "parse_rst_batch", None)

        if all(doc.edus is None for doc in documents) and segmenter is None and parse_rst_batch_fn is not None:
            start_t = time.perf_counter()
            texts = [doc.text for doc in documents]
            batch_raw_res: list[dict[str, Any]] = parse_rst_batch_fn(texts, batch_size=batch_size)
            average_parsing_ms = ((time.perf_counter() - start_t) * 1000.0) / max(1, len(documents))

            results: list[RstAnalysis] = []
            primer = DiscourseMarkerPrimer() if prime_markers else None
            completer = None
            if formalism == OutputFormalismEnum.ERST_GRAPH:
                from rdam.rst.english.erst.completer import CompleterConfig, ErstCompleter

                if erst_checkpoint is None:
                    raise RuntimeError("validated eRST checkpoint disappeared during parsing")
                completer = ErstCompleter(
                    config=CompleterConfig(
                        min_confidence_threshold=erst_checkpoint.decoder_config.edge_threshold,
                    ),
                    signal_detector=erst_checkpoint.signal_detector,
                    decoder_config=erst_checkpoint.decoder_config,
                )
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
                timing = TimingRecord(parsing_ms=average_parsing_ms, total_ms=average_parsing_ms)

                analysis = RstAnalysis(
                    document_id=base_analysis.document_id,
                    formalism=formalism,
                    nodes=base_analysis.nodes,
                    primary_edges=base_analysis.primary_edges,
                    secondary_edges=base_analysis.secondary_edges,
                    signals=base_analysis.signals,
                    provenance=prov,
                    timing=timing,
                    warnings=(*base_analysis.warnings, "timing:parsing_ms=batch_average_per_document"),
                    failure_code=base_analysis.failure_code,
                )

                if primer is not None:
                    analysis = primer.prime_analysis(analysis, doc)

                if formalism == OutputFormalismEnum.ERST_GRAPH:
                    if completer is None or erst_checkpoint is None:
                        raise RuntimeError("validated eRST completion runtime disappeared during parsing")
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
        from rdam.rst.hierarchical.stitcher import HierarchicalSectionStitcher

        stitcher = HierarchicalSectionStitcher(parser=self)
        return stitcher.parse_hierarchical(
            document=document,
            custom_boundaries=custom_boundaries,
            output=output,
        )


def _analysis_with_document_identity(
    analysis: RstAnalysis,
    *,
    document_id: str,
    elapsed_ms: float,
    model_id: str,
) -> RstAnalysis:
    from rdam.rst._provenance import resolve_package_version, resolve_source_revision
    from rdam.rst.contracts import ProvenanceRecord, RstAnalysis, TimingRecord

    return RstAnalysis(
        document_id=document_id,
        formalism=analysis.formalism,
        nodes=analysis.nodes,
        primary_edges=analysis.primary_edges,
        secondary_edges=analysis.secondary_edges,
        signals=analysis.signals,
        provenance=ProvenanceRecord(
            producer="isanlp_rst.parser",
            software_version=resolve_package_version(),
            source_revision=resolve_source_revision(),
            model_id=model_id,
            ontology_version="4.1.0-discourse",
        ),
        timing=TimingRecord(parsing_ms=elapsed_ms, total_ms=elapsed_ms),
        warnings=analysis.warnings,
        failure_code=analysis.failure_code,
    )

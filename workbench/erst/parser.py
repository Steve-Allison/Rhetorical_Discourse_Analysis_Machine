"""Experimental eRST facade, excluded from the production distribution."""

from dataclasses import replace
from pathlib import Path
from typing import Any

from rdam.rst.parser import Parser as RstParser
from rdam.rst.contracts import RstDocument
from rdam.ingest.contracts.analysis import AnalysisPolicy, ParserAnalysisResult
from rdam.ingest.contracts.inference import OutputFormalism
from rdam.ingest.service import DEFAULT_ANALYSIS_POLICY
from workbench.erst.checkpoint import load_erst_checkpoint_bundle, resolve_default_erst_checkpoint


class Parser(RstParser):
    """Run the production RST parser followed by experimental graph completion."""

    def __init__(self, *args: Any, erst_scorer_checkpoint: str | Path | None = None, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        checkpoint = resolve_default_erst_checkpoint(erst_scorer_checkpoint)
        self.erst_checkpoint = (
            load_erst_checkpoint_bundle(checkpoint, device=self.predictor._device) if checkpoint is not None else None
        )

    def analyse_document(
        self, document: RstDocument, *, analysis_policy: AnalysisPolicy | None = None
    ) -> ParserAnalysisResult:
        policy = analysis_policy or DEFAULT_ANALYSIS_POLICY
        primary_policy = AnalysisPolicy.model_validate(
            {
                **policy.model_dump(exclude={"semantic_digest"}),
                "output_formalism": OutputFormalism.RST_TREE,
            }
        )
        primary = super().analyse_document(document, analysis_policy=primary_policy)
        return (
            self.complete_erst_document(document, primary, analysis_policy=policy)
            if policy.output_formalism is OutputFormalism.ERST_GRAPH
            else primary
        )

    def complete_erst_document(
        self,
        document: RstDocument,
        primary_result: ParserAnalysisResult,
        *,
        analysis_policy: AnalysisPolicy,
    ) -> ParserAnalysisResult:
        """Add global eRST evidence to a complete validated primary result."""

        from workbench.erst.completer import CompleterConfig, ErstCompleter
        from workbench.erst.checkpoint import ErstCapabilityError
        from workbench.erst.evidence import complete_parser_analysis_result_with_erst

        checkpoint = self.erst_checkpoint
        if checkpoint is None:
            raise ErstCapabilityError("output_formalism='erst_graph' requires a validated completion bundle")
        completer = ErstCompleter(
            config=CompleterConfig(
                min_confidence_threshold=checkpoint.decoder_config.edge_threshold,
            ),
            signal_detector=checkpoint.signal_detector,
            decoder_config=checkpoint.decoder_config,
            calibration=checkpoint.calibration,
        )
        from rdam.rst.contracts import DocumentToken, TextSpan

        substrate = primary_result.semantic.analysed_document
        if substrate.text != document.text or primary_result.analysis.document_id != document.document_id:
            raise ValueError("completion source differs from the primary result")
        sentence_ids = {
            identity: index
            for index, identity in enumerate(
                dict.fromkeys(token.sentence_id for token in substrate.tokens),
                start=1,
            )
        }
        paragraph_ids = {
            identity: index
            for index, identity in enumerate(
                dict.fromkeys(token.paragraph_id for token in substrate.tokens),
                start=1,
            )
        }
        tokens = tuple(
            DocumentToken(
                token_id=(
                    token.order
                    if primary_result.semantic.recombination is not None
                    else int(token.token_id.rsplit(":", 1)[-1])
                ),
                text=token.text,
                start=token.character_range.start,
                end=token.character_range.end,
                sentence_id=sentence_ids[token.sentence_id],
                paragraph_id=paragraph_ids[token.paragraph_id],
            )
            for token in substrate.tokens
        )
        aligned_document = replace(
            document,
            tokens=tokens,
            sentence_boundaries=tuple(
                TextSpan(start=span.start, end=span.end, text=document.text[span.start : span.end])
                for span in substrate.sentence_boundaries
            ),
            paragraph_boundaries=tuple(
                TextSpan(start=span.start, end=span.end, text=document.text[span.start : span.end])
                for span in substrate.paragraph_boundaries
            ),
        )
        trace = completer.complete_graph_with_evidence(
            aligned_document,
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

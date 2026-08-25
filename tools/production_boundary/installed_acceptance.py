"""Exercise the installed wheel's complete production surface outside the repository."""

import argparse
from importlib.metadata import PackageNotFoundError, distribution
import json
from pathlib import Path
import sys


_MODEL_RELEASES = (
    ("gumrrg", "gumrrg-eb1d5745f3a1", "dmrst", None),
    ("rrtrrg", "rrtrrg-a4d19fc65bb1", "unirst", None),
    ("rstdt", "rstdt-cc01afde1232", "dmrst", None),
    ("rstreebank", "rstreebank-a3df81661baa", "dmrst", None),
    ("unirst", "unirst-9407970f1d9d", "unirst", "eng.erst.gum"),
)
_OFFLINE_DISTRIBUTIONS = ("fire", "jsonnet", "nltk", "peft", "pytest", "tiktoken")
_TEXT = "Because it rained, the match stopped. The crowd left."
_EDUS = ("Because it rained, the match stopped.", "The crowd left.")


def _assert_offline_distributions_absent() -> None:
    present: list[str] = []
    for name in _OFFLINE_DISTRIBUTIONS:
        try:
            distribution(name)
        except PackageNotFoundError:
            continue
        present.append(name)
    if present:
        raise AssertionError(f"offline distributions are available in production: {present}")


def _run_formats(markdown: Path, doclang: Path, docling: Path) -> dict[str, object]:
    from isanlp_rst.contracts import OutputFormalismEnum, RstAnalysis, RstDocument
    from isanlp_rst.ingest import ProductionAnalysisResult, ProductionIngestor, SourceArtifact, SourceForm
    from isanlp_rst.model_loading import ParserCapacity

    class _AcceptanceParser:
        analysis_capacity = ParserCapacity(unit="edu_count", maximum=512, source="installed-acceptance")
        model_release_identity = None

        def parse_document(self, document: RstDocument, output: str = "rst_tree") -> RstAnalysis:
            return RstAnalysis(
                document_id=document.document_id,
                formalism=OutputFormalismEnum(output),
                nodes=(),
                primary_edges=(),
            )

        def parse_hierarchical(
            self,
            document: RstDocument,
            custom_boundaries: object | None = None,
            output: str = "rst_tree",
        ) -> RstAnalysis:
            if custom_boundaries is None:
                raise AssertionError("structured acceptance requires explicit subdivision boundaries")
            return self.parse_document(document, output)

    artifacts = (
        SourceArtifact.from_text(_TEXT, source_name="acceptance.txt"),
        SourceArtifact.from_edus(_EDUS, source_name="acceptance.edus"),
        SourceArtifact.from_path(markdown),
        SourceArtifact.from_path(doclang),
        SourceArtifact.from_path(docling, source_form=SourceForm.DOCLING_JSON),
    )
    ingestor = ProductionIngestor(parser=_AcceptanceParser())
    result: dict[str, object] = {}
    for artifact in artifacts:
        analysis = ingestor.analyse(artifact)
        payload = json.loads(analysis.model_dump_json())
        reloaded = ProductionAnalysisResult.model_validate(payload)
        if reloaded != analysis:
            raise AssertionError(f"canonical serialization changed for {artifact.source_form.value}")
        result[artifact.source_form.value] = {
            "analysis_status": analysis.analysis_status.value,
            "prepared_segments": len(analysis.prepared_document.segments) if analysis.prepared_document else 0,
        }
    return result


def _run_full(model_store: Path, device: str) -> dict[str, object]:
    from isanlp_rst import Parser
    from isanlp_rst.contracts import RstDocument, analysis_from_json, to_json
    from isanlp_rst.erst import RS4Document, RS4Group, RS4Reader, RS4Segment, RS4Writer
    from isanlp_rst.erst.checkpoint import ErstCapabilityError

    model_results: dict[str, dict[str, int | str]] = {}
    gum_parser = None
    for model, release_id, family, relinventory in _MODEL_RELEASES:
        parser = Parser.from_model_release(
            model_store,
            release_id,
            family=family,
            relinventory=relinventory,
            device=device,
        )
        raw = parser(_TEXT)["rst"][0]
        presegmented = parser.from_edus(_EDUS)["rst"][0]
        analysis = parser.parse_document(RstDocument.from_text(_TEXT, document_id=f"acceptance-{model}"), prime_markers=False)
        reloaded = analysis_from_json(to_json(analysis))
        if reloaded != analysis:
            raise AssertionError(f"analysis serialization changed for {model}")
        model_results[model] = {
            "actual_device": str(parser.predictor._device),
            "raw_end": int(raw.end),
            "presegmented_end": int(presegmented.end),
            "nodes": len(analysis.nodes),
        }
        if model == "gumrrg":
            gum_parser = parser

    if gum_parser is None:
        raise AssertionError("gumrrg acceptance parser was not created")
    hierarchical_text = "First section explains the context.\n\nSecond section gives the result."
    hierarchical = gum_parser.parse_hierarchical(
        RstDocument.from_text(hierarchical_text, document_id="acceptance-hierarchical")
    )
    if hierarchical.root_node is None:
        raise AssertionError("hierarchical production route returned no root")
    try:
        gum_parser.parse_document(RstDocument.from_text(_TEXT), output="erst_graph")
    except ErstCapabilityError:
        pass
    else:
        raise AssertionError("eRST route accepted a parser without a completion bundle")

    rs4 = RS4Document(
        relations={"elaboration-additional": "rst"},
        segments=(
            RS4Segment(id=1, text="Context.", parent=3, relname="span"),
            RS4Segment(id=2, text="Result.", parent=1, relname="elaboration-additional"),
        ),
        groups=(RS4Group(id=3, type="span"),),
    )
    if RS4Reader.read_string(RS4Writer.to_string(rs4)) != rs4:
        raise AssertionError("eRST RS4 runtime round trip changed the document")
    return {"models": model_results, "hierarchical_nodes": len(hierarchical.nodes), "erst_rs4": True}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--model-store", type=Path)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--formats", action="store_true")
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--markdown", type=Path)
    parser.add_argument("--doclang", type=Path)
    parser.add_argument("--docling", type=Path)
    args = parser.parse_args()

    from isanlp_rst import Parser

    package_file = Path(sys.modules["isanlp_rst"].__file__ or "").resolve()
    if package_file.is_relative_to(args.source_root.resolve()):
        raise AssertionError(f"installed acceptance imported the source tree: {package_file}")
    _assert_offline_distributions_absent()
    try:
        Parser()
    except ValueError:
        pass
    else:
        raise AssertionError("Parser() must reject a missing model identity")

    result: dict[str, object] = {"package_file": str(package_file), "offline_distributions_absent": True}
    if args.formats:
        if args.markdown is None or args.doclang is None or args.docling is None:
            raise ValueError("format acceptance requires --markdown, --doclang, and --docling")
        result["formats"] = _run_formats(args.markdown, args.doclang, args.docling)
    if args.full:
        if args.model_store is None:
            raise ValueError("full acceptance requires --model-store")
        result["full"] = _run_full(args.model_store, args.device)
    result["valid"] = True
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

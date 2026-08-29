"""Unit tests for batched document inference across Parser and Predictors."""

from isanlp_rst.annotation_rst import DiscourseUnit
from isanlp_rst.contracts import OutputFormalismEnum, RstDocument
from isanlp_rst.parser import Parser


class DummyPredictor:
    def __init__(self) -> None:
        self.model_dir = "dummy_dir"

    def parse_rst(self, text: str) -> dict:
        return self.parse_rst_batch([text], batch_size=1)[0]

    def parse_rst_batch(self, texts: list[str], batch_size: int = 16) -> list[dict]:
        results = []
        for text in texts:
            unit = DiscourseUnit(
                id=1,
                relation="elaboration",
                nuclearity="NS",
                start=0,
                end=len(text) - 1,
                text=text,
            )
            results.append({"rst": [unit]})
        return results


def test_parse_documents_empty():
    parser = Parser.__new__(Parser)
    parser.predictor = DummyPredictor()  # type: ignore[assignment]
    parser.hf_model_version = "dummy_v1"
    parser.erst_checkpoint = None

    results = parser.parse_documents([])
    assert results == []


def test_parse_documents_batch_equivalence():
    parser = Parser.__new__(Parser)
    parser.predictor = DummyPredictor()  # type: ignore[assignment]
    parser.hf_model_version = "dummy_v1"
    parser.erst_checkpoint = None

    doc1 = RstDocument(document_id="doc1", text="First document text.")
    doc2 = RstDocument(document_id="doc2", text="Second document text with more content.")

    single1 = parser.parse_document(doc1)
    single2 = parser.parse_document(doc2)

    batched = parser.parse_documents([doc1, doc2], batch_size=2)
    assert len(batched) == 2
    assert batched[0].document_id == "doc1"
    assert batched[1].document_id == "doc2"
    assert batched[0].formalism == OutputFormalismEnum.RST_TREE
    assert batched[1].formalism == OutputFormalismEnum.RST_TREE
    assert len(batched[0].nodes) == len(single1.nodes)
    assert len(batched[1].nodes) == len(single2.nodes)

"""Batch equivalence against real immutable DMRST and UniRST releases."""

from pathlib import Path

import pytest
import razdel

from rdam.rst.contracts import OutputFormalismEnum, RstDocument
from rdam.rst.parser import Parser

pytestmark = pytest.mark.slow


@pytest.fixture(scope="module", params=("gumrrg-eb1d5745f3a1", "unirst-9407970f1d9d"))
def batch_parser(request: pytest.FixtureRequest) -> Parser:
    return Parser.from_model_release(
        Path.home() / ".cache/isanlp_rst/model-releases", request.param, device="cpu",
    )


def test_parse_documents_empty(batch_parser: Parser) -> None:
    assert batch_parser.parse_documents([]) == []


def test_parse_documents_batch_equivalence(batch_parser: Parser) -> None:
    documents = (
        RstDocument(document_id="doc1", text="Because it rained, the match stopped. The crowd left."),
        RstDocument(document_id="doc2", text="The survey supports the claim. However, the sample was small."),
        RstDocument(document_id="unicode", text="Dvořák left. However, cafe\u0301 patrons stayed—because it rained."),
        RstDocument(document_id="trivial", text="However"),
    )
    batched = batch_parser.parse_documents(list(documents), batch_size=2)
    assert len(batched) == len(documents)
    for document, result in zip(documents, batched, strict=True):
        sequential = batch_parser.parse_document(document)
        assert result.document_id == document.document_id
        assert result.formalism == OutputFormalismEnum.RST_TREE
        assert result.nodes == sequential.nodes
        assert result.primary_edges == sequential.primary_edges
        assert result.secondary_edges == sequential.secondary_edges
        assert result.signals == sequential.signals
        assert result.signals
        assert all(signal.token_ids for signal in result.signals)


def test_unknown_unicode_preserves_source_token_coverage(batch_parser: Parser) -> None:
    text = "[ ˈantoɲiːn ˈlɛopolt ˈdvor̝aːk ] ; He was a Czech composer. However, he also taught music."
    result = batch_parser.parse_document(RstDocument.from_text(text))
    spans = sorted(node.char_span for node in result.nodes if node.kind.value == "edu")
    for token in razdel.tokenize(text):
        assert sum(start <= token.start and token.stop <= end for start, end in spans) == 1
    assert spans[0][0] == 0
    assert spans[-1][1] == len(text)


def test_predefined_unicode_edus_keep_exact_source_spans(batch_parser: Parser) -> None:
    edus = ["[ ˈdvor̝aːk ] ;", "He composed music.", "However, cafe\u0301 patrons stayed."]
    document = RstDocument.from_edus(edus)
    result = batch_parser.parse_document(document)
    spans = sorted(node.char_span for node in result.nodes if node.kind.value == "edu")
    assert [document.text[start:end] for start, end in spans] == edus

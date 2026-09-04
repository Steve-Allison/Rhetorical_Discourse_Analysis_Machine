"""Batch equivalence against the real immutable DMRST release."""

from pathlib import Path

import pytest

from rdam.rst.contracts import OutputFormalismEnum, RstDocument
from rdam.rst.parser import Parser

pytestmark = pytest.mark.slow


@pytest.fixture(scope="module")
def batch_parser() -> Parser:
    return Parser.from_model_release(
        Path.home() / ".cache/isanlp_rst/model-releases", "gumrrg-eb1d5745f3a1", device="cpu",
    )


def test_parse_documents_empty(batch_parser: Parser) -> None:
    assert batch_parser.parse_documents([]) == []


def test_parse_documents_batch_equivalence(batch_parser: Parser) -> None:
    documents = (
        RstDocument(document_id="doc1", text="Because it rained, the match stopped. The crowd left."),
        RstDocument(document_id="doc2", text="The survey supports the claim. However, the sample was small."),
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

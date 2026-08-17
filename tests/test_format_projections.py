"""Tests for format-native projections (Docling, DocLang, Markdown -> FormatRstAnalysis)."""

from isanlp_rst.contracts import (
    FormatRstAnalysis,
    OutputFormalismEnum,
)
from isanlp_rst.doclang.schema import (
    Boundary as DoclangBoundary,
    DoclangRstResult,
    RstEdu as DoclangEdu,
    RstRelation as DoclangRelation,
)
from isanlp_rst.docling.schema import (
    Boundary as DoclingBoundary,
    DoclingRstResult,
    RstEdu as DoclingEdu,
    RstRelation as DoclingRelation,
    TableAnalysis as DoclingTableAnalysis,
)
from isanlp_rst.markdown.schema import (
    Boundary as MarkdownBoundary,
    MarkdownRstResult,
    RstEdu as MarkdownEdu,
    RstRelation as MarkdownRelation,
)


def test_docling_to_format_analysis() -> None:
    edus = (
        DoclingEdu(id=1, self_refs=("#/texts/0",), depth=1),
        DoclingEdu(id=2, self_refs=("#/texts/1",), depth=1),
    )
    relations = (
        DoclingRelation(
            id=3,
            relation="Elaboration",
            nuclearity="NS",
            nucleus_refs=("#/texts/0",),
            satellite_refs=("#/texts/1",),
            depth=0,
            left_id=1,
            right_id=2,
            boundary_memberships=("doc",),
        ),
    )
    tbl_edus = (
        DoclingEdu(id=1, self_refs=("#/tables/0/data/table_cells/0",), depth=1),
        DoclingEdu(id=2, self_refs=("#/tables/0/data/table_cells/1",), depth=1),
    )
    tbl_relations = (
        DoclingRelation(
            id=3,
            relation="Joint",
            nuclearity="NN",
            nucleus_refs=("#/tables/0/data/table_cells/0", "#/tables/0/data/table_cells/1"),
            satellite_refs=(),
            depth=0,
            left_id=1,
            right_id=2,
            boundary_memberships=("table-0",),
        ),
    )
    tables = (DoclingTableAnalysis(id="table-0", relations=tbl_relations, edus=tbl_edus),)
    result = DoclingRstResult(
        schema_name="isanlp_rst_docling",
        schema_version="1.1",
        tool="isanlp_rst",
        tool_version="1.0.0",
        model_version="gumrrg",
        inventory="rst_dt",
        source="doc1.json",
        source_origin={},
        boundaries=(
            DoclingBoundary(id="doc", kind="document", label=None, parent_self_ref=None, self_refs=("#/texts/0",)),
        ),
        relations=relations,
        edus=edus,
        table_analyses=tables,
    )

    format_analysis = result.to_format_analysis()
    assert isinstance(format_analysis, FormatRstAnalysis)
    assert format_analysis.document_analysis.formalism == OutputFormalismEnum.RST_TREE
    assert len(format_analysis.document_analysis.nodes) == 3
    assert len(format_analysis.document_analysis.primary_edges) == 2
    assert "#/texts/0" in format_analysis.node_map
    assert format_analysis.node_map["#/texts/0"] == 1
    assert "table-0" in format_analysis.table_analyses
    tbl_analysis = format_analysis.table_analyses["table-0"]
    assert len(tbl_analysis.nodes) == 3
    assert len(tbl_analysis.primary_edges) == 2


def test_doclang_to_format_analysis() -> None:
    edus = (
        DoclangEdu(id=1, xpaths=("/doc/p[1]",), thread_ids=(1,), depth=1),
        DoclangEdu(id=2, xpaths=("/doc/p[2]",), thread_ids=(1,), depth=1),
    )
    relations = (
        DoclangRelation(
            id=3,
            relation="Cause",
            nuclearity="SN",
            nucleus_xpaths=("/doc/p[2]",),
            satellite_xpaths=("/doc/p[1]",),
            nucleus_thread_ids=(1,),
            satellite_thread_ids=(1,),
            depth=0,
            left_id=1,
            right_id=2,
            boundary_memberships=("doc",),
        ),
    )
    result = DoclangRstResult(
        schema_name="isanlp_rst_doclang",
        schema_version="1.1",
        tool="isanlp_rst",
        tool_version="1.0.0",
        model_version="gumrrg",
        inventory="rst_dt",
        source="doc1.dclg",
        source_origin={},
        boundaries=(DoclangBoundary(id="doc", kind="document", label=None, parent_xpath=None, xpaths=("/doc/p[1]",)),),
        relations=relations,
        edus=edus,
    )

    format_analysis = result.to_format_analysis()
    assert isinstance(format_analysis, FormatRstAnalysis)
    assert "/doc/p[1]" in format_analysis.node_map
    assert format_analysis.node_map["/doc/p[1]"] == 1
    assert len(format_analysis.document_analysis.nodes) == 3


def test_markdown_to_format_analysis() -> None:
    edus = (
        MarkdownEdu(id=1, block_refs=("block-0",), depth=1),
        MarkdownEdu(id=2, block_refs=("block-1",), depth=1),
    )
    relations = (
        MarkdownRelation(
            id=3,
            relation="Contrast",
            nuclearity="NN",
            nucleus_refs=("block-0", "block-1"),
            satellite_refs=(),
            depth=0,
            left_id=1,
            right_id=2,
            boundary_memberships=("doc",),
        ),
    )
    result = MarkdownRstResult(
        schema_name="isanlp_rst_markdown",
        schema_version="1.1",
        tool="isanlp_rst",
        tool_version="1.0.0",
        model_version="gumrrg",
        inventory="rst_dt",
        source="doc1.md",
        source_origin={},
        boundaries=(
            MarkdownBoundary(id="doc", kind="document", label=None, parent_block_ref=None, block_refs=("block-0",)),
        ),
        relations=relations,
        edus=edus,
    )

    format_analysis = result.to_format_analysis()
    assert isinstance(format_analysis, FormatRstAnalysis)
    assert "block-0" in format_analysis.node_map
    assert format_analysis.node_map["block-0"] == 1
    assert len(format_analysis.document_analysis.nodes) == 3

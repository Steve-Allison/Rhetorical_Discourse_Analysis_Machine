from isanlp_rst.contracts import (
    NodeKindEnum,
    NuclearityPatternEnum,
    OutputFormalismEnum,
    PrimaryRelationEdge,
    RstAnalysis,
    RstNode,
)
from isanlp_rst.hierarchical.stitcher import nuclear_spine_text


def test_macro_representation_uses_exact_nuclear_spine_not_a_fixed_prefix() -> None:
    nucleus = "Nucleus at source coordinates."
    satellite = "S" * 2_000
    analysis = RstAnalysis(
        document_id="section",
        formalism=OutputFormalismEnum.RST_TREE,
        nodes=(
            RstNode(1, NodeKindEnum.EDU, (1, 1), (0, len(nucleus)), nucleus),
            RstNode(2, NodeKindEnum.EDU, (2, 2), (len(nucleus) + 1, len(nucleus) + 1 + len(satellite)), satellite),
            RstNode(3, NodeKindEnum.ROOT, (1, 2), (0, len(nucleus) + 1 + len(satellite)), f"{nucleus} {satellite}"),
        ),
        primary_edges=(
            PrimaryRelationEdge("e1", 3, 1, "elaboration", "elaboration", NuclearityPatternEnum.NS),
            PrimaryRelationEdge("e2", 3, 2, "elaboration", "elaboration", NuclearityPatternEnum.NS),
        ),
    )
    assert nuclear_spine_text(analysis, fallback="unused") == nucleus


def test_multinuclear_spine_retains_every_nucleus_in_source_order() -> None:
    analysis = RstAnalysis(
        document_id="section",
        formalism=OutputFormalismEnum.RST_TREE,
        nodes=(
            RstNode(1, NodeKindEnum.EDU, (1, 1), (0, 4), "One."),
            RstNode(2, NodeKindEnum.EDU, (2, 2), (5, 9), "Two."),
            RstNode(3, NodeKindEnum.ROOT, (1, 2), (0, 9), "One. Two."),
        ),
        primary_edges=(
            PrimaryRelationEdge("e1", 3, 1, "joint", "joint", NuclearityPatternEnum.NN),
            PrimaryRelationEdge("e2", 3, 2, "joint", "joint", NuclearityPatternEnum.NN),
        ),
    )
    assert nuclear_spine_text(analysis, fallback="unused") == "One. Two."

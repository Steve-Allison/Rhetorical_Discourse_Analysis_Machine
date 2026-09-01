"""Unit tests for GUM v12.1.0 dataset parsing, token alignment, and target matrix generation."""

from pathlib import Path
import pytest

from workbench.training.modern.gum_dataset import (
    build_target_matrices,
    extract_edus_from_tree,
    load_gum_splits,
    map_nuclearity,
    map_relation,
    parse_dis_tree,
)

SAMPLE_DIS = """( Root (span 1 3)
  ( Satellite (leaf 1) (rel2par context-background) (text _!First background EDU._!) )
  ( Nucleus (span 2 3) (rel2par span)
    ( Nucleus (leaf 2) (rel2par joint-list) (text _!Second main EDU._!) )
    ( Nucleus (leaf 3) (rel2par joint-list) (text _!Third main EDU._!) )
  )
)
"""


def test_parse_dis_tree_structure() -> None:
    root = parse_dis_tree(SAMPLE_DIS)
    assert root.node_type == "Root"
    assert root.edu_start == 1
    assert root.edu_end == 3
    assert len(root.children) == 2

    # Left child
    sat = root.children[0]
    assert sat.node_type == "Satellite"
    assert sat.edu_start == 1
    assert sat.edu_end == 1
    assert sat.rel2par == "context-background"
    assert sat.text == "First background EDU."

    # Right child
    nuc = root.children[1]
    assert nuc.node_type == "Nucleus"
    assert nuc.edu_start == 2
    assert nuc.edu_end == 3
    assert len(nuc.children) == 2


def test_extract_edus() -> None:
    root = parse_dis_tree(SAMPLE_DIS)
    edus = extract_edus_from_tree(root)
    assert len(edus) == 3
    assert edus == ["First background EDU.", "Second main EDU.", "Third main EDU."]


def test_map_nuclearity_and_relations() -> None:
    root = parse_dis_tree(SAMPLE_DIS)
    # Root has Satellite (1) and Nucleus (2..3) -> SN
    assert map_nuclearity(root.children[0], root.children[1]) == "SN"
    assert map_relation(root) == "context"

    # Right child has Nucleus (2) and Nucleus (3) -> NN
    right = root.children[1]
    assert map_nuclearity(right.children[0], right.children[1]) == "NN"
    assert map_relation(right) == "joint"


def test_build_target_matrices() -> None:
    root = parse_dis_tree(SAMPLE_DIS)
    splits, nucs, rels = build_target_matrices(root, num_edus=3)

    assert splits.shape == (1, 3, 3)
    assert nucs.shape == (1, 3, 3)
    assert rels.shape == (1, 3, 3)

    # Leaves [0,0], [1,1], [2,2] are constituents
    assert splits[0, 0, 0] == 1.0
    assert splits[0, 1, 1] == 1.0
    assert splits[0, 2, 2] == 1.0

    # Span [1, 2] (EDUs 2..3) is a constituent
    assert splits[0, 1, 2] == 1.0
    # Span [0, 2] (EDUs 1..3, Root) is a constituent
    assert splits[0, 0, 2] == 1.0
    # Span [0, 1] (EDUs 1..2) is NOT a constituent in this tree
    assert splits[0, 0, 1] == 0.0

    # Nuclearity of Root [0, 2] is SN (idx 1)
    assert nucs[0, 0, 2] == 1
    # Nuclearity of Right [1, 2] is NN (idx 2)
    assert nucs[0, 1, 2] == 2
    # Non-constituent [0, 1] is masked with -100
    assert nucs[0, 0, 1] == -100


def test_gum_splits_md_partitions() -> None:
    splits_path = Path("workbench/corpora/gum-v12.1.0/splits.md")
    if not splits_path.is_file():
        pytest.skip("GUM splits.md not found in test environment")

    splits = load_gum_splits(splits_path)
    assert len(splits["train"]) == 211
    assert len(splits["dev"]) == 32
    assert len(splits["test"]) == 32
    assert len(splits["test2"]) == 26
    assert sum(len(v) for v in splits.values()) == 301


def test_real_gum_dis_file_parses() -> None:
    dis_path = Path("workbench/corpora/gum-v12.1.0/rst/lisp_binary/GUM_academic_art.dis")
    if not dis_path.is_file():
        pytest.skip("GUM_academic_art.dis not found")

    tree = parse_dis_tree(dis_path.read_text(encoding="utf-8"))
    assert tree.node_type == "Root"
    edus = extract_edus_from_tree(tree)
    assert len(edus) == 74  # GUM_academic_art has 74 EDUs

    splits, nucs, rels = build_target_matrices(tree, num_edus=74)
    assert splits.shape == (1, 74, 74)
    assert splits[0, 0, 73] == 1.0  # Root span is constituent

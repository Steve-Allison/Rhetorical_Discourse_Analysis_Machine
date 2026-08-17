"""Unit tests for ontology lock loader and adapter."""

import pytest

from isanlp_rst.contracts import NuclearityPatternEnum, RelationSchemeEnum
from isanlp_rst.ontology import OntologyAdapter, load_ontology_lock


def test_load_ontology_lock() -> None:
    lock_data = load_ontology_lock()
    assert lock_data.release_status == "released"
    assert len(lock_data.coarse_concepts) == 18
    assert "Elaboration" in lock_data.coarse_concepts
    assert len(lock_data.dmrst_gum_model_27) == 27
    assert len(lock_data.dmrst_rstdt_model_42) == 42


def test_dmrst_rstdt_model_42_mapping() -> None:
    adapter = OntologyAdapter()
    res0 = adapter.resolve_model_class(0, RelationSchemeEnum.DMRST_RSTDT_MODEL_42)
    assert res0.canonical_label == "Elaboration"
    assert res0.concept == "Elaboration"
    assert res0.nuclearity == NuclearityPatternEnum.NS

    res1 = adapter.resolve_model_class(1, RelationSchemeEnum.DMRST_RSTDT_MODEL_42)
    assert res1.canonical_label == "Attribution"
    assert res1.concept == "Attribution"
    assert res1.nuclearity == NuclearityPatternEnum.SN

    res2 = adapter.resolve_model_class(2, RelationSchemeEnum.DMRST_RSTDT_MODEL_42)
    assert res2.canonical_label == "Joint"
    assert res2.concept == "Joint"
    assert res2.nuclearity == NuclearityPatternEnum.NN


def test_dmrst_gum_model_27_mapping() -> None:
    adapter = OntologyAdapter()
    res0 = adapter.resolve_model_class(0, RelationSchemeEnum.DMRST_GUM_MODEL_27)
    assert res0.canonical_label == "adversative"
    assert res0.concept == "Contrast"
    assert res0.nuclearity == NuclearityPatternEnum.NN

    res11 = adapter.resolve_model_class(11, RelationSchemeEnum.DMRST_GUM_MODEL_27)
    assert res11.canonical_label == "elaboration"
    assert res11.concept == "Elaboration"
    assert res11.nuclearity == NuclearityPatternEnum.NS


def test_rst_dt_alias_and_suffix_normalization() -> None:
    adapter = OntologyAdapter()

    # Normal label
    label, concept = adapter.resolve_label("elaboration-additional", RelationSchemeEnum.RST_DT_FINE)
    assert label == "elaboration-additional"
    assert concept == "Elaboration"

    # Embedded suffix (-e)
    label_e, concept_e = adapter.resolve_label("elaboration-additional-e", RelationSchemeEnum.RST_DT_FINE)
    assert label_e == "elaboration-additional"
    assert concept_e == "Elaboration"

    # Complex suffix (-s-e)
    label_se, concept_se = adapter.resolve_label("consequence-s-e", RelationSchemeEnum.RST_DT_FINE)
    assert label_se == "consequence"
    assert concept_se == "Cause"

    # Alias spelling
    label_tx, concept_tx = adapter.resolve_label("textualorganization", RelationSchemeEnum.RST_DT_FINE)
    assert label_tx == "textual-organization"
    assert concept_tx == "Textual-organization"


def test_gum_label_resolution() -> None:
    adapter = OntologyAdapter()
    label, concept = adapter.resolve_label("adversative-antithesis", RelationSchemeEnum.GUM_ERST_FINE)
    assert label == "adversative-antithesis"
    assert concept == "adversative"


def test_unmapped_label_fails_closed() -> None:
    adapter = OntologyAdapter()
    with pytest.raises(KeyError, match="Unmapped label"):
        adapter.resolve_label("non_existent_relation_xyz", RelationSchemeEnum.RST_DT_FINE)

    with pytest.raises(KeyError, match="Class index 999 not found"):
        adapter.resolve_model_class(999, RelationSchemeEnum.DMRST_RSTDT_MODEL_42)

    # Test raise_on_unmapped=False returns None
    result = adapter.resolve_label("non_existent_relation_xyz", RelationSchemeEnum.RST_DT_FINE, raise_on_unmapped=False)
    assert result is None

    result_class = adapter.resolve_model_class(999, RelationSchemeEnum.DMRST_RSTDT_MODEL_42, raise_on_unmapped=False)
    assert result_class is None


def test_missing_lockfile_raises() -> None:
    from pathlib import Path
    from isanlp_rst.ontology import load_ontology_lock

    with pytest.raises(FileNotFoundError):
        load_ontology_lock(Path("/non_existent_path/central.lock.yaml"))


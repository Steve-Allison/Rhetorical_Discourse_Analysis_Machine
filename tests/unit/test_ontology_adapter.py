"""Unit tests for ontology lock loader and adapter."""

import pytest
import hashlib
from pathlib import Path

from rdam.rst.ontology.loader import LOCK_FILE_PATH

from rdam.rst.contracts import NuclearityPatternEnum, RelationSchemeEnum
from rdam.rst.ontology import OntologyAdapter, load_ontology_lock


def test_load_ontology_lock() -> None:
    lock_data = load_ontology_lock()
    assert lock_data.authority == "local_inventory"
    assert lock_data.release_status == "unverified"
    assert lock_data.release_version is None
    assert lock_data.sha256_digest == hashlib.sha256(LOCK_FILE_PATH.read_bytes()).hexdigest()
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
    assert concept == "Contrast"


@pytest.mark.parametrize("raw", ("attribution-n", "ATTRIBUTION-N-E"))
def test_negative_attribution_is_not_a_nuclearity_suffix(raw: str) -> None:
    assert OntologyAdapter().resolve_label(raw, RelationSchemeEnum.RST_DT_FINE) == (
        "attribution-negative", "Attribution",
    )


@pytest.mark.parametrize("label", ("Manner-Means", "Topic-Change", "Topic-Comment"))
def test_hyphenated_coarse_labels_preserve_inventory_spelling(label: str) -> None:
    assert OntologyAdapter().resolve_label(label.upper(), RelationSchemeEnum.RST_DT_COARSE_18) == (label, label)


def test_all_gum_model_categories_resolve_under_coarse_scheme() -> None:
    adapter = OntologyAdapter()
    for mapping in adapter.lock_data.dmrst_gum_model_27.values():
        assert adapter.resolve_label(mapping.label, RelationSchemeEnum.GUM_ERST_COARSE) == (
            mapping.label, mapping.concept,
        )
    # A coarse adversative prediction does not select a fine concession/contrast label.
    assert adapter.resolve_label("adversative", RelationSchemeEnum.GUM_ERST_FINE, raise_on_unmapped=False) is None


def test_every_locked_gum_fine_label_resolves_to_a_canonical_concept() -> None:
    adapter = OntologyAdapter()
    for raw_label in adapter.lock_data.gum_fine_to_coarse:
        canonical_label, concept = adapter.resolve_label(raw_label, RelationSchemeEnum.GUM_ERST_FINE)
        assert canonical_label == raw_label
        assert concept in adapter.lock_data.coarse_concepts


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
    from rdam.rst.ontology import load_ontology_lock

    with pytest.raises(FileNotFoundError):
        load_ontology_lock(Path("/non_existent_path/central.lock.yaml"))


@pytest.mark.parametrize("old,new", (
    ("release_version: null", 'release_version: "4.1.0-discourse"'),
    ("release_status: unverified", "release_status: released"),
    ("authority: local_inventory", "authority: Central_Configs"),
    ('concept: "Contrast"', 'concept: "Invented"'),
    ('nuclearity: "NN"', 'nuclearity: "SS"'),
    ('  0: { label: "adversative"', '  99: { label: "adversative"'),
))
def test_local_inventory_rejects_false_provenance_and_invalid_mappings(tmp_path: Path, old: str, new: str) -> None:
    original = LOCK_FILE_PATH.read_text(encoding="utf-8")
    assert old in original
    path = tmp_path / "inventory.yaml"
    path.write_text(original.replace(old, new, 1), encoding="utf-8")
    with pytest.raises(ValueError):
        load_ontology_lock(path)

"""Corpus scope comes from runtime data, with explicit unresolved inventories."""

from dataclasses import dataclass

import pytest

from rdam.ingest.contracts.base import Sha256Identity
from rdam.ingest.identity import semantic_sha256
from rdam.rst.ontology import load_ontology_lock
from rdam.ingest.vocabulary import RuntimeRelationVocabulary, capture_runtime_vocabulary


@dataclass
class ConfiguredInventory:
    relation_table: tuple[str, ...]
    config: dict[str, dict[str, str]]


@dataclass
class SelectedInventory:
    relation_table: tuple[str, ...]
    dataset_names: tuple[str, ...]
    relinventory_idx: int


@dataclass
class SharedClassifier:
    relation_vocab: tuple[str, ...]
    dataset_masks: tuple[tuple[bool, ...], ...] | None


@dataclass
class UnionInventory(SelectedInventory):
    model: SharedClassifier


def test_shared_classifier_inventory_is_not_a_corpus_crosswalk() -> None:
    predictor = UnionInventory(
        ("context_NS",), ("GUM",), 0,
        SharedClassifier(("context_NS", "elaboration_NS"), ((True, False),)),
    )
    vocabulary = capture_runtime_vocabulary(predictor, ("context", "elaboration"))
    assert vocabulary.corpus_name == "GUM"
    assert vocabulary.inventory_scope == "shared_classifier"
    assert vocabulary.mapping_reason == "shared_classifier_crosswalk_unavailable"
    assert vocabulary.alignment is None
    assert RuntimeRelationVocabulary.model_validate_json(vocabulary.model_dump_json()) == vocabulary
    predictor.model.dataset_masks = None
    with pytest.raises(ValueError, match="differs from the loaded relation table"):
        capture_runtime_vocabulary(predictor, ("context", "elaboration"))


def test_no_decisions_can_retain_the_loaded_corpus_inventory() -> None:
    predictor = UnionInventory(
        ("context_NS",), ("GUM",), 0,
        SharedClassifier(("context_NS", "elaboration_NS"), ((True, False),)),
    )
    assert capture_runtime_vocabulary(predictor, ("context",)).inventory_scope == "corpus"


def test_configured_gum_inventory_resolves_without_using_model_name() -> None:
    table = tuple(f"{item.label}_{item.nuclearity}" for item in load_ontology_lock().dmrst_gum_model_27.values())
    labels = tuple(dict.fromkeys(label.rpartition("_")[0] for label in table))
    vocabulary = capture_runtime_vocabulary(ConfiguredInventory(table, {"data": {"corpus": "GUM"}}), labels)
    assert vocabulary.corpus_name == "GUM"
    assert vocabulary.scope_basis == "configured_corpus"
    assert vocabulary.alignment is not None
    assert vocabulary.alignment.scheme.endswith("/gum_erst_groups")
    assert RuntimeRelationVocabulary.model_validate_json(vocabulary.model_dump_json()) == vocabulary


def test_selected_corpus_wins_over_other_available_inventories() -> None:
    vocabulary = capture_runtime_vocabulary(SelectedInventory(("context_NS",), ("RST-DT", "GUM"), 1), ("context",))
    assert vocabulary.corpus_name == "GUM"
    assert vocabulary.scope_basis == "selected_corpus"
    assert vocabulary.alignment is not None


def test_unregistered_labels_never_acquire_guessed_meaning() -> None:
    vocabulary = capture_runtime_vocabulary(SelectedInventory(("Condition_NS",), ("GUM",), 0), ("Condition",))
    assert vocabulary.alignment is None
    assert vocabulary.mapping_reason == "inventory_has_unmapped_labels"


def test_missing_corpus_remains_explicit() -> None:
    vocabulary = capture_runtime_vocabulary(ConfiguredInventory(("context_NS",), {}), ("context",))
    assert vocabulary.alignment is None
    assert vocabulary.mapping_reason == "corpus_not_declared"


def test_changed_runtime_table_rejects_captured_labels() -> None:
    with pytest.raises(ValueError, match="differs from the loaded relation table"):
        capture_runtime_vocabulary(ConfiguredInventory(("context_NS",), {}), ("joint",))


def test_false_inventory_digest_is_rejected() -> None:
    vocabulary = capture_runtime_vocabulary(ConfiguredInventory(("context_NS",), {}), ("context",))
    data = vocabulary.model_dump()
    data["inventory_identity"] = Sha256Identity(hex_digest=semantic_sha256(("joint",)))
    with pytest.raises(ValueError, match="identity differs"):
        RuntimeRelationVocabulary.model_validate(data)

"""Real pre-update records retain the authority and profile they identify."""

from pathlib import Path

import pytest

from rdam._strict import Sha256Identity, sha256_bytes
from rdam.ingest.vocabulary import RuntimeRelationVocabulary
from rdam.ontology import ObservedVocabularyAlignment, technique_projection_identity, walton_profile_alignment
from tools.ontology.project_discourse_concepts import preserve_snapshot

FIXTURES = Path(__file__).parent / "fixtures/ontology"


def test_pre_update_walton_mapping_is_not_reinterpreted_as_current() -> None:
    old = ObservedVocabularyAlignment.model_validate_json(
        (FIXTURES / "walton-profile-before-sign-variables.json").read_bytes(),
    )
    current = walton_profile_alignment(("expert_opinion",))
    assert old.projection_identity != technique_projection_identity()
    assert old.consumer_profile_identity != current.consumer_profile_identity
    assert "expert_opinion/premise/source" in {item.native_value for item in old.unmapped}
    assert "expert_opinion/premise/source" in {item.native_value for item in current.mappings}
    assert ObservedVocabularyAlignment.model_validate_json(old.model_dump_json()) == old


def test_pre_update_runtime_vocabulary_uses_its_original_snapshot() -> None:
    old = RuntimeRelationVocabulary.model_validate_json(
        (FIXTURES / "gum-vocabulary-before-sign-variables.json").read_bytes(),
    )
    assert old.alignment is not None
    assert old.alignment.projection_identity != technique_projection_identity()
    assert old.corpus_name == "GUM"
    assert not old.alignment.unmapped
    assert RuntimeRelationVocabulary.model_validate_json(old.model_dump_json()) == old


def test_missing_snapshot_does_not_fall_back_to_current_meaning() -> None:
    current = walton_profile_alignment(("expert_opinion",))
    data = current.model_dump()
    data["projection_identity"] = Sha256Identity(hex_digest=sha256_bytes(b"not an ontology snapshot"))
    with pytest.raises(ValueError, match="snapshot is unavailable"):
        ObservedVocabularyAlignment.model_validate(data)


def test_snapshot_preservation_refuses_to_overwrite_corruption(tmp_path: Path) -> None:
    raw = b'{"authority":"fixture"}'
    preserve_snapshot(raw, tmp_path)
    path = tmp_path / f"{sha256_bytes(raw)}.json"
    path.write_bytes(b"corrupted")
    with pytest.raises(ValueError, match="snapshot is corrupt"):
        preserve_snapshot(raw, tmp_path)
    assert path.read_bytes() == b"corrupted"

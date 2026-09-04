"""Instruction identity cannot make unknown or dirty source revisions cacheable."""

import pytest

from rdam._provider_provenance import instruction_revision
from rdam._result_cache import revision_is_cacheable
from rdam.contracts import semantic_sha256


@pytest.mark.parametrize("instructions", (None, "", "Analyse source evidence."))
@pytest.mark.parametrize(
    ("revision", "cacheable"),
    (("", False), ("unknown", False), ("abc-dirty", False), ("abc", True)),
)
def test_instruction_binding_preserves_source_cache_eligibility(
    revision: str, instructions: str | None, cacheable: bool,
) -> None:
    bound = instruction_revision(revision, instructions)
    if instructions is None:
        assert bound == revision
    else:
        suffix = "-dirty" if revision.endswith("-dirty") else ""
        expected = f"{revision.removesuffix('-dirty')}:instructions:{semantic_sha256(instructions)}{suffix}"
        assert bound == expected
    assert revision_is_cacheable(bound) is cacheable


def test_instruction_changes_change_identity_without_changing_source_status() -> None:
    assert instruction_revision("abc", "first") != instruction_revision("abc", "second")

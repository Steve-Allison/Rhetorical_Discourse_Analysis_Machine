"""Tests for the shared DocLang eligibility policy."""

from dataclasses import FrozenInstanceError

import pytest

from isanlp_rst.doclang.eligibility import DoclangEligibility, METADATA_HEAD_ELEMENTS


def test_default_policy_is_safe_and_complete() -> None:
    policy = DoclangEligibility()
    assert policy.allows_main_kind("text")
    assert policy.allows_main_kind("heading")
    assert policy.allows_main_kind("list_item")
    assert policy.allows_main_kind("caption")
    assert policy.include_table_cells
    assert policy.include_page_boundaries
    assert policy.include_group_boundaries
    assert policy.allowed_layers == frozenset({"body"})
    assert not policy.allows_main_kind("code")
    assert not policy.allows_main_kind("formula")


def test_every_content_and_structure_switch_is_independent() -> None:
    policy = DoclangEligibility(
        include_prose=False,
        include_picture_captions=False,
        include_lists=False,
        include_table_cells=False,
        include_code_blocks=True,
        include_formulas=True,
        include_field_regions=True,
        include_background=True,
        include_furniture=True,
        include_page_boundaries=False,
        include_group_boundaries=False,
        include_heading_boundaries=False,
    )
    assert not policy.allows_main_kind("text")
    assert not policy.allows_main_kind("heading")
    assert not policy.allows_main_kind("list_item")
    assert not policy.allows_main_kind("caption")
    assert policy.allows_main_kind("code")
    assert policy.allows_main_kind("formula")
    assert policy.include_field_regions
    assert not policy.include_table_cells
    assert not policy.include_page_boundaries
    assert not policy.include_group_boundaries
    assert policy.allowed_layers == frozenset({"body", "background", "furniture"})


def test_current_metadata_heads_include_derived_text_elements() -> None:
    assert {"description", "summary"} <= METADATA_HEAD_ELEMENTS


def test_policy_is_immutable() -> None:
    policy = DoclangEligibility()
    with pytest.raises(FrozenInstanceError):
        policy.__setattr__("include_code_blocks", True)

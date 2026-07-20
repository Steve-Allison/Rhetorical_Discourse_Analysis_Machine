"""Tests for ``isanlp_rst.parser.Parser`` dispatch and auto-detection.

These exercise the façade WITHOUT loading models — every test fails fast on
argument validation or runs ``_resolve_family`` / ``_detect_family_from_model_dir``
directly.
"""

from __future__ import annotations

import json

import pytest

from isanlp_rst.parser import Parser


# ---------- _resolve_family logic ----------


class TestResolveFamily:
    def test_explicit_family_dmrst(self):
        assert Parser._resolve_family(None, 'gumrrg', 'dmrst') == 'dmrst'

    def test_explicit_family_unirst(self):
        assert Parser._resolve_family(None, 'unirst', 'unirst') == 'unirst'

    def test_explicit_family_invalid(self):
        with pytest.raises(ValueError, match="Unknown family"):
            Parser._resolve_family(None, None, 'whatever')

    def test_version_routes_to_dmrst(self):
        for v in Parser.DMRST_PARSERS:
            assert Parser._resolve_family(None, v, None) == 'dmrst', v

    def test_version_routes_to_unirst(self):
        for v in Parser.UNIVERSAL_PARSERS:
            assert Parser._resolve_family(None, v, None) == 'unirst', v

    def test_version_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown hf_model_version"):
            Parser._resolve_family(None, 'not-a-version', None)

    def test_explicit_family_mismatched_version_raises(self):
        """When both family and version are set, version must belong to family."""
        with pytest.raises(ValueError, match="not valid for family"):
            Parser._resolve_family(None, 'gumrrg', 'unirst')
        with pytest.raises(ValueError, match="not valid for family"):
            Parser._resolve_family(None, 'unirst', 'dmrst')

    def test_family_alone_without_model_dir_raises(self):
        with pytest.raises(ValueError, match="requires hf_model_version or model_dir"):
            Parser._resolve_family(None, None, 'dmrst')
        with pytest.raises(ValueError, match="requires hf_model_version or model_dir"):
            Parser._resolve_family(None, None, 'unirst')

    def test_family_with_matching_version_ok(self):
        assert Parser._resolve_family(None, 'gumrrg', 'dmrst') == 'dmrst'
        assert Parser._resolve_family(None, 'rstdt', 'dmrst') == 'dmrst'
        assert Parser._resolve_family(None, 'unirst', 'unirst') == 'unirst'
        assert Parser._resolve_family(None, 'rrtrrg', 'unirst') == 'unirst'

    def test_family_with_model_dir_ok_without_version(self, tmp_path):
        assert Parser._resolve_family(str(tmp_path), None, 'dmrst') == 'dmrst'
        assert Parser._resolve_family(str(tmp_path), None, 'unirst') == 'unirst'

    def test_no_args_raises(self):
        with pytest.raises(ValueError, match="hf_model_version"):
            Parser._resolve_family(None, None, None)


# ---------- _detect_family_from_model_dir ----------


class TestDetectFamilyFromModelDir:
    def test_dmrst_via_relation_table(self, tmp_path):
        d = tmp_path / "dmrst"
        d.mkdir()
        (d / "relation_table.txt").write_text("elaboration\ncontrast\n")
        assert Parser._detect_family_from_model_dir(str(d)) == 'dmrst'

    def test_unirst_via_pickle_at_root(self, tmp_path):
        d = tmp_path / "unirst"
        d.mkdir()
        (d / "data_manager_eng.rst.gum.pickle").write_bytes(b"fake")
        assert Parser._detect_family_from_model_dir(str(d)) == 'unirst'

    def test_unirst_via_pickle_under_data(self, tmp_path):
        d = tmp_path / "unirst"
        (d / "data").mkdir(parents=True)
        (d / "data" / "data_manager_eng.rst.gum.pickle").write_bytes(b"fake")
        assert Parser._detect_family_from_model_dir(str(d)) == 'unirst'

    def test_unirst_via_pickle_under_data_dms(self, tmp_path):
        d = tmp_path / "unirst"
        (d / "data" / "dms").mkdir(parents=True)
        (d / "data" / "dms" / "data_manager_eng.rst.gum.pickle").write_bytes(b"fake")
        assert Parser._detect_family_from_model_dir(str(d)) == 'unirst'

    def test_unirst_via_config_corpora(self, tmp_path):
        d = tmp_path / "unirst"
        d.mkdir()
        (d / "config.json").write_text(
            json.dumps({"data": {"corpora": ["eng.rst.rstdt"]}})
        )
        assert Parser._detect_family_from_model_dir(str(d)) == 'unirst'

    def test_unirst_pickle_takes_priority_over_dmrst_signature(self, tmp_path):
        """If both signatures are present, UniRST wins (more specific)."""
        d = tmp_path / "ambiguous"
        d.mkdir()
        (d / "relation_table.txt").write_text("elaboration\n")
        (d / "data_manager_eng.rst.gum.pickle").write_bytes(b"fake")
        assert Parser._detect_family_from_model_dir(str(d)) == 'unirst'

    def test_no_signature_returns_none(self, tmp_path):
        d = tmp_path / "empty"
        d.mkdir()
        assert Parser._detect_family_from_model_dir(str(d)) is None

    def test_invalid_config_json_treated_as_no_signature(self, tmp_path):
        d = tmp_path / "broken"
        d.mkdir()
        (d / "config.json").write_text("not valid json {{{")
        # Falls through; with no other markers this should return None.
        assert Parser._detect_family_from_model_dir(str(d)) is None

    def test_config_without_corpora_does_not_match(self, tmp_path):
        d = tmp_path / "no-corpora"
        d.mkdir()
        (d / "config.json").write_text(
            json.dumps({"data": {"something_else": "foo"}})
        )
        assert Parser._detect_family_from_model_dir(str(d)) is None


# ---------- Parser.__init__ argument validation (no model load) ----------


class TestParserInitValidation:
    def test_no_args_raises(self):
        with pytest.raises(ValueError, match="hf_model_version"):
            Parser()

    def test_family_alone_without_version_or_model_dir_raises(self):
        """``family=`` alone is not enough — need a version or local dir."""
        with pytest.raises(ValueError):
            Parser(family="dmrst")

    def test_family_mismatched_version_raises_before_download(self):
        """Incompatible family+version must fail before any model load."""
        with pytest.raises(ValueError):
            Parser(family="dmrst", hf_model_version="unirst")

    def test_unknown_version_raises(self):
        with pytest.raises(ValueError, match="Unknown hf_model_version"):
            Parser(hf_model_version="not-a-version")

    def test_unknown_family_raises(self):
        with pytest.raises(ValueError, match="Unknown family"):
            Parser(family="not-a-family", hf_model_version="gumrrg")

    def test_empty_model_dir_raises(self, tmp_path):
        with pytest.raises(ValueError, match="auto-detect"):
            Parser(model_dir=str(tmp_path), hf_model_name=None)

    def test_model_dir_with_explicit_nondefault_hf_name_raises(self, tmp_path):
        (tmp_path / "relation_table.txt").write_text("elaboration\n", encoding="utf-8")
        with pytest.raises(ValueError, match="not both"):
            Parser(
                model_dir=str(tmp_path),
                hf_model_name="some/other-repo",
                family="dmrst",
            )

    def test_class_constants(self):
        """Public class constants documenting valid versions."""
        assert 'gumrrg' in Parser.DMRST_PARSERS
        assert 'unirst' in Parser.UNIVERSAL_PARSERS
        assert 'dmrst' in Parser.AVAILABLE_FAMILIES
        assert 'unirst' in Parser.AVAILABLE_FAMILIES
        assert set(Parser.AVAILABLE_VERSIONS) == (
            set(Parser.DMRST_PARSERS) | set(Parser.UNIVERSAL_PARSERS)
        )

# DocLang test fixtures

This directory mirrors both the valid and invalid DocLang examples from
[`doclang-project/doclang`](https://github.com/doclang-project/doclang/tree/main/tests/data)
at commit `7f53133d47e1424fb18c3a53faed4df43f21a86b` (`main`, 2026-10-09). The 60 valid
specimens are in this directory and the 79 invalid specimens are in `invalid/`. The
`formats` extra installs the DocLang validator from the same commit. Upstream files
and local files both use the recommended `.dclg` extension.

The upstream repository is Apache-2.0 licensed. The fixtures are mirrored
verbatim and remain attributable to their upstream commit.

`upstream-manifest.json` is the pinned filename and SHA-256 authority. Tests
derive both fixture inventories from the filesystem, compare every name and
hash with that manifest, validate every valid fixture, and require both
upstream DocLang and RDAM ingest to reject every invalid fixture with the locked
`doclang[schematron-saxon]` installation. This avoids a hand-maintained count
that can silently become stale or a validator call that can silently disappear.

Refreshes must use the GitHub Contents API at the selected immutable commit,
replace the manifest hashes, move the `doclang` pin in `pyproject.toml` to the same
commit, and pass `tests/ingest/test_doclang_fixture_parity.py` and
`pixi run python scripts/verify_doclang_fixtures.py`.

## Real-world preparation specimen

`real_world/change-of-tenancy.dclg` is a verbatim DocLang export of a completed
business change-of-tenancy form, copied from
`Docling_Machine/tests/fixtures/doclang/sample.dclg`. It exercises a substantial
real document containing prose, populated tables, pictures, a formula and chart
data. It is deliberately outside `upstream-manifest.json`: that manifest remains
the exact authority for the upstream conformance corpus, while this document is
the representative real-world preparation specimen.

SHA-256: `bd0e7d861054842e2e6993c4d92367a54a20cdb1ba21a8eb1d7640c642747449`.

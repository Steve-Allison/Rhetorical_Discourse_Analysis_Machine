# DocLang test fixtures

This directory mirrors the valid DocLang examples from
[`doclang-project/doclang`](https://github.com/doclang-project/doclang/tree/main/tests/data/valid)
at commit `6d3b3d3c195d1f63333c5c5fcba8da17937a33bd`. Upstream files and local files
both use the recommended `.dclg` extension.

The upstream repository is Apache-2.0 licensed. The fixtures are mirrored
verbatim and remain attributable to their upstream commit.

`upstream-manifest.json` is the pinned filename and SHA-256 authority. Tests
derive the fixture inventory from the filesystem, compare every name and hash
with that manifest, and validate every discovered fixture with the locked
`doclang[schematron-saxon]` installation. This avoids a hand-maintained count
that can silently become stale.

Refreshes must use the GitHub Contents API at the selected immutable commit,
replace the manifest hashes, and pass `tests/test_doclang_fixture_parity.py`.

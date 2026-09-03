# DocLang test fixtures

This directory mirrors both the valid and invalid DocLang examples from
[`doclang-project/doclang`](https://github.com/doclang-project/doclang/tree/main/tests/data)
at commit `6d3b3d3c195d1f63333c5c5fcba8da17937a33bd`. The 42 valid specimens are in
this directory and the 59 invalid specimens are in `invalid/`. Upstream files
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
replace the manifest hashes, and pass
`tests/ingest/test_doclang_fixture_parity.py`.

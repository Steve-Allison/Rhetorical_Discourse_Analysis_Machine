"""Verify local DocLang fixtures against an immutable upstream GitHub commit."""

from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from pathlib import Path
from urllib.request import Request, urlopen

from pydantic import BaseModel, ConfigDict, TypeAdapter


class FixtureParityError(RuntimeError):
    """Raised when local, manifest, and upstream fixture authority diverge."""


class _Manifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    upstream_commit: str
    files: dict[str, str]
    invalid_files: dict[str, str]


class _GithubEntry(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    type: str
    name: str
    download_url: str | None


class FixtureParityReceipt(BaseModel):
    """Sanitized evidence from a successful upstream parity check."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    upstream_commit: str
    local_files: int
    upstream_files: int
    local_invalid_files: int
    upstream_invalid_files: int
    names_match: bool
    hashes_match: bool


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = REPOSITORY_ROOT / "tests" / "fixtures" / "doclang"
MANIFEST_PATH = FIXTURE_DIR / "upstream-manifest.json"
GITHUB_CONTENTS_URL = "https://api.github.com/repos/doclang-project/doclang/contents/tests/data"
USER_AGENT = "isanlp-rst-doclang-fixture-audit"


def _read_url(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=30) as response:
        return response.read()


def _verify_corpus(kind: str, directory: Path, pinned: dict[str, str], commit: str) -> tuple[int, int]:
    api_url = f"{GITHUB_CONTENTS_URL}/{kind}?ref={commit}"
    entries = TypeAdapter(list[_GithubEntry]).validate_json(_read_url(api_url))
    upstream = {
        entry.name: entry.download_url
        for entry in entries
        if entry.type == "file" and entry.name.endswith(".dclg") and entry.download_url is not None
    }
    local = {path.name: path for path in directory.glob("*.dclg")}
    if not local.keys() == pinned.keys() == upstream.keys():
        raise FixtureParityError(
            f"DocLang {kind} fixture names differ across local files, the pinned manifest, and the upstream API"
        )
    with ThreadPoolExecutor(max_workers=8) as executor:
        upstream_bytes = dict(zip(upstream, executor.map(_read_url, upstream.values()), strict=True))
    mismatches = [
        name
        for name, path in local.items()
        if sha256(path.read_bytes()).hexdigest() != pinned[name]
        or sha256(upstream_bytes[name]).hexdigest() != pinned[name]
    ]
    if mismatches:
        raise FixtureParityError(f"DocLang {kind} fixture hashes differ for: {', '.join(sorted(mismatches))}")
    return len(local), len(upstream)


def verify_doclang_fixtures() -> FixtureParityReceipt:
    """Compare local valid and invalid names and bytes with the pinned manifest and upstream API."""

    manifest = _Manifest.model_validate_json(MANIFEST_PATH.read_text(encoding="utf-8"))
    local_files, upstream_files = _verify_corpus("valid", FIXTURE_DIR, manifest.files, manifest.upstream_commit)
    local_invalid, upstream_invalid = _verify_corpus(
        "invalid", FIXTURE_DIR / "invalid", manifest.invalid_files, manifest.upstream_commit
    )
    return FixtureParityReceipt(
        upstream_commit=manifest.upstream_commit,
        local_files=local_files,
        upstream_files=upstream_files,
        local_invalid_files=local_invalid,
        upstream_invalid_files=upstream_invalid,
        names_match=True,
        hashes_match=True,
    )


if __name__ == "__main__":
    print(verify_doclang_fixtures().model_dump_json(indent=2))

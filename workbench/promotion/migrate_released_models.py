"""Migrate cached upstream parser releases into the strict local model store."""

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path, PurePosixPath
import tempfile

from pydantic import BaseModel, ConfigDict

from workbench.promotion.promote import (
    copy_release_file,
    promote_model_release,
    write_candidate_manifest,
)


class UpstreamRelease(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    revision: str
    weights_sha256: str
    family: str


_RELEASES = (
    UpstreamRelease(name="gumrrg", revision="eb1d5745f3a18b8894ce72abad3c2a76442d1107", weights_sha256="1fd8dcfb1b72a0c448cf61e91b7b9142407a9c39f49ae665af69ad6b746db02b", family="dmrst"),
    UpstreamRelease(name="rrtrrg", revision="a4d19fc65bb17f399ddcbc909c8650c2fad8e55b", weights_sha256="0016c30a752c594fb7680443ef15f42de4c578cb06825ac8ac9d5ee6a17cc1a8", family="unirst"),
    UpstreamRelease(name="rstdt", revision="cc01afde123253fec70787f6442642f5b7634587", weights_sha256="c4008a42605d6fc2657be72ba1de50977b164f88bbc5f53b62a922f43fff3c32", family="dmrst"),
    UpstreamRelease(name="rstreebank", revision="a3df81661baa4ed41755155eec141f9bf83733b4", weights_sha256="82ffa417ae4fc7e82267e889c73c52f6f4be6fcca847c4a283155356e5028176", family="dmrst"),
    UpstreamRelease(name="unirst", revision="9407970f1d9d2435b5f875a0cd14293a16646304", weights_sha256="1cb7f7df68db3fc996b3fa904dbf443f5bffa0ba403a6fb5f6acc2231b965b6e", family="unirst"),
)


def _role(path: PurePosixPath) -> str:
    if path.name == "best_weights.pt":
        return "legacy-model-weights"
    if path.name == "config.json":
        return "runtime-configuration"
    if path.name.startswith("relation_table"):
        return "relation-inventory"
    return "runtime-resource"


def migrate(cache_root: Path, store: Path) -> dict[str, object]:
    receipts: list[dict[str, object]] = []
    with tempfile.TemporaryDirectory(prefix="isanlp-rst-model-migration-") as temporary:
        staging = Path(temporary)
        for release in _RELEASES:
            snapshot = cache_root / "snapshots" / release.revision
            if not snapshot.is_dir():
                raise FileNotFoundError(f"cached release snapshot is unavailable: {snapshot}")
            candidate = staging / release.name
            candidate.mkdir()
            roles: dict[PurePosixPath, str] = {}
            for source in sorted(snapshot.rglob("*")):
                if not source.is_file():
                    continue
                relative = PurePosixPath(source.relative_to(snapshot).as_posix())
                copy_release_file(source.resolve(strict=True), candidate / relative)
                roles[relative] = _role(relative)
            weights = candidate / "best_weights.pt"
            from isanlp_rst.model_loading.release import sha256_file

            if sha256_file(weights) != release.weights_sha256:
                raise RuntimeError(f"released weight identity changed for {release.name}")
            release_id = f"{release.name}-{release.revision[:12]}"
            write_candidate_manifest(
                candidate,
                release_id=release_id,
                model_task="rst-parsing",
                architecture=f"isanlp-rst-{release.family}",
                runtime_contract=f"isanlp_rst.parser/{release.family}-v1",
                compatibility_range=">=4,<5",
                source_model_identity=f"tchewik/isanlp_rst_v3:{release.name}",
                source_revision=release.revision,
                licence="CC-BY-NC-4.0",
                use_restrictions=("research and non-commercial use only",),
                roles=roles,
                evaluation_evidence="Published model metrics recorded in repository README.md",
            )
            receipt = promote_model_release(candidate, store)
            receipts.append(receipt.model_dump(mode="json"))
    return {
        "schema_version": "isanlp_rst_released_model_migration/v1",
        "created_at": datetime.now(UTC).isoformat(),
        "cache_root": str(cache_root.resolve()),
        "store": str(store.resolve()),
        "receipts": receipts,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--cache-root",
        type=Path,
        default=Path("/Users/steveallison/.cache/huggingface/hub/models--tchewik--isanlp_rst_v3"),
    )
    parser.add_argument(
        "--store",
        type=Path,
        default=Path("/Users/steveallison/.cache/isanlp_rst/model-releases"),
    )
    args = parser.parse_args()
    print(json.dumps(migrate(args.cache_root, args.store), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""CUDA verification script — to be run on a real NVIDIA host.

Usage:

    pixi run cuda-smoke

This Mac-pinned project can't exercise CUDA in CI. Run this on any NVIDIA
host (Linux + CUDA-built PyTorch) to confirm the CUDA dispatch path of the
``Parser`` façade end-to-end. Verifies:

* ``torch.cuda.is_available()`` returns True (otherwise the test refuses to run).
* Every ModernBERT release in ``models/model-releases`` loads on ``cuda:0``
  through ``Parser.from_model_release`` (not MPS, not CPU).
* Tree alignment matches the input text.
* ``from_edus`` round-trips the input EDUs.

Releases are loaded from the local immutable store; nothing is downloaded.
DMRST and UniRST are archived from production and are not exercised.
"""

from pathlib import Path
import sys
import time

import torch

from isanlp_rst.annotation_rst import DiscourseUnit
from isanlp_rst.parser import Parser

SAMPLE_TEXT = "The cat sat on the mat. It was a black cat. The mat was red."
SAMPLE_EDUS = [
    "The cat sat on the mat.",
    "It was a black cat.",
    "The mat was red.",
]
STORE = Path("models/model-releases")


def _assert_aligned(tree: DiscourseUnit, text: str) -> None:
    expected = text[tree.start : tree.end]
    if tree.text != expected:
        raise AssertionError(f"alignment failed: tree.text={tree.text!r} != text[{tree.start}:{tree.end}]={expected!r}")
    for child in (tree.left, tree.right):
        if child is not None:
            _assert_aligned(child, text)


def _collect_leaves(tree: DiscourseUnit) -> list[str]:
    out: list[str] = []

    def walk(unit: DiscourseUnit) -> None:
        if unit.left is None and unit.right is None:
            out.append(unit.text)
            return
        if unit.left is not None:
            walk(unit.left)
        if unit.right is not None:
            walk(unit.right)

    walk(tree)
    return out


def main() -> int:
    if not torch.cuda.is_available():
        print(
            "FAIL — torch.cuda.is_available() is False. This script is meant "
            "to be run on an NVIDIA host with a CUDA-built PyTorch.",
            file=sys.stderr,
        )
        return 2

    print(f"CUDA: {torch.cuda.get_device_name(0)} | torch {torch.__version__}")

    store = STORE.resolve()
    releases = sorted(child.name for child in store.iterdir() if (child / "release-manifest.json").is_file())
    if not releases:
        print(f"FAIL — no releases found in {store}", file=sys.stderr)
        return 1

    for release_id in releases:
        print(f"\n--- {release_id} ---")
        t0 = time.time()
        parser = Parser.from_model_release(store, release_id, family="modernbert", device="cuda")
        device = parser.predictor._device
        if device.type != "cuda":
            print(f"FAIL — expected cuda device, got {device}", file=sys.stderr)
            return 1
        print(f"  loaded in {time.time() - t0:.1f}s on {device}")

        t0 = time.time()
        _assert_aligned(parser(SAMPLE_TEXT)["rst"][0], SAMPLE_TEXT)
        print(f"  parse_rst: {time.time() - t0:.2f}s, alignment OK")

        t0 = time.time()
        leaves = _collect_leaves(parser.from_edus(SAMPLE_EDUS)["rst"][0])
        if leaves != SAMPLE_EDUS:
            print(f"FAIL — EDU round-trip mismatch: {leaves} != {SAMPLE_EDUS}", file=sys.stderr)
            return 1
        print(f"  from_edus: {time.time() - t0:.2f}s, round-trip OK")

    print("\nPASS — CUDA path verified end-to-end.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

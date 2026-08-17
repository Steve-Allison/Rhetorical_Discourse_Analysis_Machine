"""CUDA verification script — to be run on a real NVIDIA host.

Usage:

    pixi run cuda-smoke

This Mac-pinned project can't exercise CUDA in CI. Run this on any NVIDIA
host (Linux + CUDA-built PyTorch) to confirm the CUDA dispatch path of the
``Parser`` façade end-to-end. Verifies:

* ``torch.cuda.is_available()`` returns True (otherwise the test refuses to run).
* ``Parser(device='cuda')`` resolves to ``cuda:0`` (not MPS, not CPU).
* DMRST ``gumrrg`` and UniRST ``unirst`` both load and parse on GPU.
* Tree alignment matches the input text.
* ``parse_from_edus`` round-trips the input EDUs.

Models are pulled from the HF Hub (~2 GB each on first run).
"""

import sys
import time

import torch

from isanlp_rst.parser import Parser


SAMPLE_TEXT = "The cat sat on the mat. It was a black cat. The mat was red."
SAMPLE_EDUS = [
    "The cat sat on the mat.",
    "It was a black cat.",
    "The mat was red.",
]


def _assert_aligned(tree, text: str) -> None:
    expected = text[tree.start:tree.end]
    if tree.text != expected:
        raise AssertionError(
            f"alignment failed: tree.text={tree.text!r} != "
            f"text[{tree.start}:{tree.end}]={expected!r}"
        )
    for child in (getattr(tree, 'left', None), getattr(tree, 'right', None)):
        if child is not None:
            _assert_aligned(child, text)


def _collect_leaves(tree) -> list[str]:
    out: list[str] = []

    def walk(u) -> None:
        l, r = getattr(u, 'left', None), getattr(u, 'right', None)
        if l is None and r is None:
            out.append(u.text)
            return
        if l is not None:
            walk(l)
        if r is not None:
            walk(r)

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

    cases: list[tuple[str, dict]] = [
        ('DMRST gumrrg', dict(hf_model_version='gumrrg')),
        (
            'UniRST unirst',
            dict(hf_model_version='unirst', relinventory='eng.erst.gum'),
        ),
    ]

    for name, kwargs in cases:
        print(f"\n--- {name} ---")
        t0 = time.time()
        parser = Parser(
            hf_model_name='tchewik/isanlp_rst_v3', device='cuda', **kwargs,
        )
        device = parser.predictor._device
        if device.type != 'cuda':
            print(f"FAIL — expected cuda device, got {device}", file=sys.stderr)
            return 1
        print(f"  loaded in {time.time() - t0:.1f}s on {device}")

        t0 = time.time()
        res = parser(SAMPLE_TEXT)
        _assert_aligned(res['rst'][0], SAMPLE_TEXT)
        print(f"  parse_rst: {time.time() - t0:.2f}s, alignment OK")

        t0 = time.time()
        res = parser.from_edus(SAMPLE_EDUS)
        leaves = _collect_leaves(res['rst'][0])
        if leaves != SAMPLE_EDUS:
            print(
                f"FAIL — EDU round-trip mismatch: {leaves} != {SAMPLE_EDUS}",
                file=sys.stderr,
            )
            return 1
        print(f"  parse_from_edus: {time.time() - t0:.2f}s, round-trip OK")

    print("\nPASS — CUDA path verified end-to-end.")
    return 0


if __name__ == '__main__':
    sys.exit(main())

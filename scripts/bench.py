"""Performance benchmark for isanlp_rst across devices and dtypes.

Usage:

    pixi run bench
    pixi run bench --version unirst --runs 10
    pixi run bench --text-length long

Reports median wall-clock latency for ``parse_rst`` after warm-up. Comparing
across:

* CPU fp32 (baseline, host-dependent)
* GPU fp32 (the library default on every device — equivalent precision to CPU baseline)
* GPU bf16 (opt-in via dtype='bf16' — 2026 SOTA on native-bf16 accelerators)
* GPU fp16 (opt-in via dtype='fp16' — faster on hardware without native bf16, e.g. M1)

Tree shapes from every (device, dtype) combination must match the CPU fp32
baseline. The benchmark fails if any combination diverges in tree structure.
"""

import argparse
from pathlib import Path
import pickle
import statistics
import sys
import time

import torch
from huggingface_hub.errors import EntryNotFoundError

from rdam.rst.parser import Parser


SHORT_TEXT = "The cat sat on the mat. It was a black cat. The mat was red."

LONG_TEXT = (
    "Climate scientists have been documenting an alarming acceleration in the "
    "rate of polar ice melt over the past decade. The latest satellite data "
    "indicates that ice loss in Greenland alone has tripled compared to "
    "measurements from the early 2000s. This rapid melting contributes "
    "significantly to global sea level rise, threatening coastal communities "
    "worldwide. Researchers warn that without immediate action to reduce "
    "greenhouse gas emissions, the consequences will be irreversible. "
    "However, recent technological advances in carbon capture offer some hope. "
    "If deployed at scale, these technologies could help offset emissions "
    "from industries that are difficult to decarbonise directly."
)


def _shape(unit) -> tuple:
    if not getattr(unit, "left", None) and not getattr(unit, "right", None):
        return ("LEAF", unit.start, unit.end)
    return (unit.relation, _shape(unit.left), _shape(unit.right))


def _time_parse(parser: Parser, text: str, runs: int) -> tuple[float, tuple]:
    """Run parser n times after a warm-up. Return median seconds and tree shape."""
    # Warm-up — first run on accelerator includes kernel compile / autocast
    # init cost which we don't want in the timing distribution.
    res = parser(text)
    shape = _shape(res["rst"][0])

    timings: list[float] = []
    for _ in range(runs):
        t0 = time.perf_counter()
        parser(text)
        timings.append(time.perf_counter() - t0)
    return statistics.median(timings), shape


def main() -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    ap.add_argument("--family", default="modernbert", choices=("modernbert", "unirst", "dmrst"))
    ap.add_argument("--release-id", default=None, help="Model release ID from model store")
    ap.add_argument("--model-store", type=Path, default=Path.home() / ".cache/isanlp_rst/model-releases")
    ap.add_argument("--version", default="gumrrg", choices=("gumrrg", "rstdt", "rstreebank", "rrtrrg", "unirst"))
    ap.add_argument("--relinventory", default="eng.erst.gum", help="Only used for unirst.")
    ap.add_argument("--runs", type=int, default=5)
    ap.add_argument("--text-length", choices=("short", "long"), default="long")
    args = ap.parse_args()

    text = SHORT_TEXT if args.text_length == "short" else LONG_TEXT

    print(f"Bench: family={args.family}, release_id={args.release_id}, runs={args.runs}, text-length={args.text_length} ({len(text)} chars)")
    print(f"PyTorch: {torch.__version__}")
    print()

    configs: list[tuple[str, dict]] = [
        ("CPU fp32", dict(device="cpu")),
    ]
    if torch.cuda.is_available():
        configs.extend(
            [
                ("CUDA fp32", dict(device="cuda", dtype=torch.float32)),
                ("CUDA bf16", dict(device="cuda", dtype=torch.bfloat16)),
                ("CUDA fp16", dict(device="cuda", dtype=torch.float16)),
            ]
        )
    elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available() and torch.backends.mps.is_built():
        configs.extend(
            [
                ("MPS fp32", dict(device="mps", dtype=torch.float32)),
                ("MPS bf16", dict(device="mps", dtype=torch.bfloat16)),
                ("MPS fp16", dict(device="mps", dtype=torch.float16)),
            ]
        )

    print(f"{'config':<14} {'load':>8} {'parse (median)':>16} {'per char':>12} {'tree match':>11}")
    print("-" * 65)

    baseline_shape = None
    failed = 0
    for name, kwargs in configs:
        try:
            t0 = time.perf_counter()
            if args.family == "modernbert" and args.release_id:
                parser = Parser.from_model_release(
                    args.model_store,
                    args.release_id,
                    family=args.family,
                    **kwargs,
                )
            else:
                parser = Parser(
                    family=args.family,
                    **kwargs,
                )
            load_s = time.perf_counter() - t0

            median, shape = _time_parse(parser, text, args.runs)

            if baseline_shape is None:
                baseline_shape = shape
                tree_match = "baseline"
            else:
                tree_match = "OK" if shape == baseline_shape else "DIVERGED"
                if shape != baseline_shape:
                    failed += 1

            per_char_us = median / max(len(text), 1) * 1e6
            print(f"{name:<14} {load_s:>7.1f}s {median * 1000:>14.1f}ms {per_char_us:>10.1f}µs {tree_match:>11}")

        except (OSError, RuntimeError, ValueError, EntryNotFoundError, pickle.UnpicklingError) as exc:
            failed += 1
            print(f"{name:<14} FAILED: {type(exc).__name__}: {exc}")

    print()
    if failed:
        print(f"FAIL — {failed} configuration(s) diverged or errored")
        return 1
    print("All configurations produced identical tree structure.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

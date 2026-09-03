# Python 3.14 production modernization performance evidence

Measured on 2026-09-03 in the repository's locked Pixi `default` environment on the local Apple Silicon host. Values are medians of three to ten runs; peak memory is Python `tracemalloc` peak and therefore excludes device/native allocator memory. Inputs and both implementations returned equal values before timing.

| Case | Input | Before | After | Peak before | Peak after |
|---|---:|---:|---:|---:|---:|
| sentence assignment | 100,000 tokens / 2,000 sentences | 4,122.99 ms | 26.24 ms | 3,591,424 B | 3,588,224 B |
| token-to-EDU assignment | 20,000 tokens / 2,000 EDUs | 360.89 ms | 2.94 ms | 379,944 B | 379,816 B |
| DocLang canonical paths | 8,000 same-name siblings | 4,370.22 ms | 18.16 ms | 637,541 B | 929,185 B |
| provider provenance | 100 repeated calls | 10.33 ms | 0.104 ms | 94,062,891 B | 10,011 B |
| viewer source load | classic RS3 fixture | 4.82 ms | 0.160 ms | 185,839 B | 133,304 B |
| RST serialization | skew tree, depth 400 | 1.23 ms | 1.89 ms | 169,088 B | 263,820 B |
| RST serialization | skew tree, depth 1,500 | `RecursionError` | 8.31 ms | n/a | 1,183,368 B |

The shallow-tree serialization result is not a speed claim: the iterative implementation adds explicit cycle/shared-node rejection and bounded call-stack behavior. The performance acceptance is successful completion at adversarial depth. The other measurements show the expected change from repeated nested scans or I/O to monotonic/indexed/cached work.

The final production preparation threshold suite passed: `3 passed in 2.76s`.

The viewer was also exercised through real Chromium after installing the Playwright-pinned browser runtime: async PNG output was 13,780 bytes, async PDF output was 18,921 bytes, and a Poppler render proved the one-page PDF nonblank at 1212 × 768 pixels.

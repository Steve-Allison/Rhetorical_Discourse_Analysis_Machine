# T073 parser concurrency measurement — 2026-09-03

Command actually run:

```bash
HF_HUB_OFFLINE=1 pixi run --locked pytest \
  tests/stress/test_concurrency_stress.py -k real_parser -v
```

Result: **4 passed, 4 deselected in 44.25 seconds**.

| Real predictor | Device | Result |
| --- | --- | --- |
| `PredictorDMRST` | CPU | PASS |
| `PredictorUniRST` | CPU | PASS |
| `PredictorDMRST` | MPS | PASS |
| `PredictorUniRST` | MPS | PASS |

Each case loads a validated compatible immutable local release, asserts its actual
predictor type, measures four distinct texts sequentially, then shares that same parser
across four synchronized worker threads for three rounds. Every tree field is compared
as JSON bytes, including text, offsets, child IDs, relation, nuclearity, probability, and
entropy. Every node's text is also checked against its exact source slice.

The selected cache releases were `gumrrg-eb1d5745f3a1` and `unirst-9407970f1d9d`, with
`eng.erst.gum` explicitly selected for UniRST. Network access was disabled for model
resolution. Test platform: macOS, Python 3.14.7, pytest 9.1.1; MPS available.

This establishes equivalence for these tested configurations and inputs. It does not
establish safety for arbitrary devices, precision modes, segmenters, eRST scorers, lazy
initialization, or every possible input. T082 must use this bounded evidence when
declaring provider safety; the entire provider includes more than an already-loaded
tree predictor.

## T082 full-provider follow-up — 2026-09-04

```bash
HF_HUB_OFFLINE=1 pixi run --locked pytest -q \
  tests/stress/test_concurrency_stress.py -k 'real_parser or real_provider'
```

Observed: **8 passed, 4 deselected in 88.33 seconds**. The four additional cases
start four requests against a cold `RstProvider`, verify that every declaration
reports available, and compare complete native analytical identities against a
subsequent sequential result. Both families pass on CPU and MPS. Full artifact
identities differ because execution evidence remains present.

The cold declaration test exposed a real race: the release-check flag could be
visible before validation completed. Release inspection and parser construction
now share a reentrant initialization lock. Inference itself is not held under
that initialization lock.

RST therefore declares concurrent operation for CPU, MPS, and macOS automatic
device selection when no eRST completion bundle resolves. Other devices and
configurations with an eRST completion bundle declare serialized operation;
this measurement does not establish their full-provider concurrency safety.

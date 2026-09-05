# Feature 019 historical contract specimens

Captured on 2026-09-04 from RDAM 6.0.0 at
`e7deef4968e5b921c33caa8bd1723b58b65280cd`, before native production changes.
The working tree contained untracked Feature 019 planning files; preserve the
emitted provenance's `-dirty` suffix rather than rewriting the records.

## What these records prove

These are deliberately authored external-model **test responses**, passed through
the real `WaltonProvider.analyse` and `ToulminProvider.analyse` implementations and
their native validators. Pydantic AI's `FunctionModel` replaced only the external
model boundary, with `ALLOW_MODEL_REQUESTS=False`. A process-local dummy credential
enabled declaration checks; no external model was called and no real credential
is stored here. The emitted `openai:gpt-5.4` identity is the configured identity
retained by the existing provider, **not evidence of a response from that model**.

The exact source text, without a trailing newline, was:

```text
Dark clouds are visible. Rain is likely. Dark clouds often precede rain.
```

`SourceIdentity.from_text` used `source_name="019-historical-contract-probe"`.
Direct `ProviderRequest` supplied that text and no structure or projection. No
original-file alignment is claimed. Each provider completed in one output attempt
and one transport attempt through the local test boundary.

| File | Historical observation |
|---|---|
| walton-omitted-v1.json | Sign instance with no reported assessments, but two derived open questions. |
| walton-partial-v1.json | One addressed assessment with a note, no evidence spans, and one omitted question derived as open. |
| toulmin-v1.json | Warrant without origin or evidence fields; a qualifier alone increments fully_qualified_count. |
| aggregate-v1.json | Real AggregateAnalysis validation over the omitted-Walton and Toulmin native records; no persisted requested scope or completion status. |

The aggregate was constructed from those real native records, not captured from
a Machine run. It has no preparation receipt. These specimens establish v1
persistence and validator behavior only. They are not reviewed gold, held-out
cases, T007's comparable live baseline, transport parity, or quality acceptance.

## Preservation and verification

Each result file contains the exact shared serializer output followed by one LF.
`expected-digests.json` pins the emitted semantic/artifact identities independently
of the future historical reader. Aggregate v1 has no artifact digest; its expected
value is null. Do not regenerate these specimens with corrected providers or add
missing assessments, origin fields, evidence roles, requested scope or status.

Executed verification on 2026-09-04:

```sh
pixi run python - <<'PY'
import json
from pathlib import Path
from rdam import load, serialize
root = Path('tests/interfaces/fixtures/historical')
expected = json.loads((root / 'expected-digests.json').read_text())
for name, digests in expected.items():
    raw = (root / name).read_bytes()
    record = load(raw)
    assert serialize(record) + b'\n' == raw, name
    dump = record.model_dump(mode='json')
    assert dump['semantic_digest']['hex_digest'] == digests['semantic_digest']
    assert dump.get('artifact_digest', {}).get('hex_digest') == digests['artifact_digest']
    print(name, 'canonical round-trip and fixed digests verified')
PY
```

All four records printed `canonical round-trip and fixed digests verified`; exit
status was 0. T015 must retain these checks under the explicit historical reader
and add damaged-record/cache cases; that later work is not complete.

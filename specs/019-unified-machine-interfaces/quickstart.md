# Quickstart and Validation Guide

The unified interface is implemented in this checkout. Verification results and
any unverified model prerequisites are recorded in [tasks.md](tasks.md); examples
alone are not proof of completion.

## Prerequisites

Runnable document.md, dung.json and ibis.json are under tests/interfaces/fixtures/.
Generate a fully materialized request.json using the Python example below. Model-free structured
analysis needs no LLM credentials or RST weights. RST/eRST need declared valid
local artifacts; LLM integration needs explicitly configured models/credentials.
Keep keys outside requests/configuration/results. HTTP is installed only through
the optional extra; everyday developer commands use the default Pixi environment.

## Primary workflows

```sh
pixi run rdam capabilities
pixi run rdam schema request
pixi run rdam schema configuration
pixi run rdam prepare tests/interfaces/fixtures/document.md
pixi run rdam analyse --techniques dung,ibis --structured dung=tests/interfaces/fixtures/dung.json --structured ibis=tests/interfaces/fixtures/ibis.json --output analysis.json
pixi run rdam summary analysis.json
pixi run rdam view analysis.json --techniques dung --output dung-view.json
```

Expected: capability/schema/preparation have no inference; structured analysis
returns a complete canonical aggregate with inline reading guide and exit 0.
The view preserves the original status, full Dung native result and context,
and explicitly identifies excluded IBIS. Summary/view never run inference.
Existing output files require --force; never overwrite a fixture/input.

Configured document analysis:

```sh
pixi run rdam analyse tests/interfaces/fixtures/document.md --techniques rst,toulmin,walton --config machine.json --output document-analysis.json
```

machine.json is an owner-created configuration matching the generated schema,
not a tracked credential file. Inspect effective provider settings in the result.
Walton must cover every question of each returned instance. Toulmin must retain
warrant origin and validated supporting spans. An invalid model proposal must
follow bounded provider retry/failure semantics, not be repaired into certainty.

## Python and HTTP parity

Use AggregateRequest constructors and serialize_request to create request.json
once. Call Machine.analyse(load_request(bytes)) directly, then submit those same
bytes through CLI and HTTP with the same configured machine. Do not compare a
file-origin request against an independently invented stdin origin as identical.

```python
import json
from pathlib import Path
from rdam import AggregateRequest, StructuredInput, Technique, serialize_request

framework = json.loads(Path("tests/interfaces/fixtures/dung.json").read_text())
request = AggregateRequest.for_structured(
    (StructuredInput(technique=Technique.DUNG, payload=framework),),
    techniques=(Technique.DUNG,),
)
Path("request.json").write_bytes(serialize_request(request))
```

```sh
pixi run rdam analyse --request request.json --output cli-result.json
pixi run rdam serve --host 127.0.0.1 --port 8765
```

From a separate terminal:

```sh
curl --fail-with-body --silent --show-error -H 'Content-Type: application/json' --data-binary @request.json http://127.0.0.1:8765/v1/analyse
```

HTTP 200 means an aggregate was produced, not that every technique succeeded.
Inspect status/outcomes. For exact parity, use deterministic native operations
or fixed responses at the external model protocol boundary. Live independent
model calls may differ; report their actual grounding/validation results separately.

## Implementation checks

Run the new native integrity suites, tests/machine/ and tests/interfaces/ through
Pixi, then existing project lint/type/full-test tasks. Follow
[acceptance-matrix.md](contracts/acceptance-matrix.md) for precise cases.
Build and install the candidate wheel with existing production tooling and prove
the installed rdam command, schemas and optional dependency boundaries; a source
checkout invocation alone is insufficient. Record actual commands, outputs and
unverified model prerequisites in the implementation report. No publication or
new release ceremony is part of this validation guide.

## Analytical-quality validation

Write native regression tests, implement the fixes, then run focused real-model
cases and have a cold critic inspect the source and actual outputs. Follow
[analytical-quality.md](contracts/analytical-quality.md) for required semantic
cases. No manual annotation or evaluation framework is required. Use the existing
explicit model-run opt-in for external calls.

Opted-in live checks:

```sh
RDAM_RUN_LIVE_MODEL_TESTS=1 pixi run pytest tests/interfaces/test_model_backed.py -v
```

This command requires configured models and exercises real providers. Inspect
source support and native meanings, fix concrete errors, and rerun affected tests.
Report missing model access explicitly; skipped cases are not passes. Valid JSON
and equal transport outputs alone do not demonstrate a correct analysis.

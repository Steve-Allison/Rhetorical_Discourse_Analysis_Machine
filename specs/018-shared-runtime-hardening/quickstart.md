# Quickstart: Shared Runtime Hardening

```python
from pathlib import Path

from rdam import AggregateRequest, ExecutionPolicy, Technique, production_machine

machine = production_machine(
    execution_policy=ExecutionPolicy(max_workers=4, cache_directory=Path(".local-rdam-cache")),
)
analysis = machine.analyse(
    AggregateRequest.for_text("The proposal is costly, but it may reduce risk.", (Technique.RST, Technique.PDTB))
)
```

Omit `cache_directory` for the default no-persistence behavior. A dirty/unknown revision also bypasses caching even when a directory is supplied.

## Acceptance Commands

```sh
pixi run lint
pixi run typecheck
pixi run test
pixi run test-stress
pixi run shared-runtime-coverage
pixi run shared-runtime-mutation-test
pixi run production-api-contract
pixi run production-boundary
pixi run production-import-check
pixi run build-production --evidence-dir specs/018-shared-runtime-hardening/build-evidence
pixi run validate-production-artifacts
pixi run -e production production-clean-install \
  --model-store /Users/steveallison/.cache/isanlp_rst/model-releases \
  --release-id gumrrg-eb1d5745f3a1
git diff --check
```

Run `pixi run test-all` only when the configured local model releases are present; report unavailable prerequisites explicitly.

The build requires a clean committed checkout. The clean-install command takes
an explicit local model store and release; the values above are the existing
release used on this machine, not a hidden task default. Installation fetches
dependencies, then acceptance runs with external network access disabled.

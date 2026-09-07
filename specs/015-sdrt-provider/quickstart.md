# Quickstart: SDRT Provider

Current native integrity/version corrections are recorded in
[Feature 019](../019-unified-machine-interfaces/contracts/native-integrity.md).
Model execution requires configured credentials; discovery alone does not verify
remote service availability.

```python
from rdam import ProviderRequest, SourceIdentity
from rdam.sdrt import SdrtProvider

text = "The roads flooded. Traffic stopped. This delayed deliveries."
source = SourceIdentity.from_text(text)
result = SdrtProvider().analyse(
    ProviderRequest(source=source, text=text, structured_input=None)
)
print(result.payload)
```

Capability inspection is safe before invocation:

```python
declaration = SdrtProvider().declaration
print(declaration.capability)
```

Validation:

```bash
pixi run pytest tests/sdrt -q
pixi run lint
pixi run typecheck
pixi run -e default production-boundary
```

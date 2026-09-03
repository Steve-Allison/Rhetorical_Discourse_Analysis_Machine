# Quickstart: SDRT Provider

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

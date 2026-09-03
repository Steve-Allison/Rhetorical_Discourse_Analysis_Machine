# Quickstart: PDTB Provider

```python
from rdam import ProviderRequest, SourceIdentity
from rdam.pdtb import PdtbProvider

text = "Roads flooded, so traffic stopped."
source = SourceIdentity.from_text(text)
result = PdtbProvider().analyse(
    ProviderRequest(source=source, text=text, structured_input=None)
)
print(result.payload)
```

Capability inspection is side-effect-free:

```python
print(PdtbProvider().declaration.capability)
```

Validation:

```bash
pixi run pytest tests/pdtb -q
pixi run lint
pixi run typecheck
pixi run -e default production-boundary
```

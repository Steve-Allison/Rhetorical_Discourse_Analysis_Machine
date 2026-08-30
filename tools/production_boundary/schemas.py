"""Generate deterministic Draft 2020-12 production-contract schemas."""

from collections.abc import Mapping
from pathlib import Path
from typing import Any, Final

from pydantic import BaseModel, TypeAdapter
import rfc8785

from isanlp_rst.ingest.contracts.analysis import (
    AnalysedOutcome,
    EmptyPrimaryAnalysisOutcome,
    ParserAnalysisResult,
    ProductionAnalysisOutcome,
)
from isanlp_rst.ingest.contracts.capabilities import ProductionCapabilities
from isanlp_rst.ingest.contracts.failure import (
    DiagnosticProductionFailureRecord,
    SafeProductionFailureRecord,
)
from isanlp_rst.ingest.contracts.preparation import PreparationOutcome

SCHEMA_ROOT: Final = Path("isanlp_rst/ingest/schemas")
SCHEMA_BASE: Final = "https://schemas.isanlp-rst.local/production/2.0.0"

_MODELS: Final[Mapping[str, type[BaseModel] | TypeAdapter[Any]]] = {
    "analysed-outcome.schema.json": AnalysedOutcome,
    "capabilities.schema.json": ProductionCapabilities,
    "diagnostic-production-failure.schema.json": DiagnosticProductionFailureRecord,
    "empty-primary-analysis-outcome.schema.json": EmptyPrimaryAnalysisOutcome,
    "parser-analysis-result.schema.json": ParserAnalysisResult,
    "preparation-outcome.schema.json": PreparationOutcome,
    "production-analysis-outcome.schema.json": TypeAdapter(ProductionAnalysisOutcome),
    "safe-production-failure.schema.json": SafeProductionFailureRecord,
}


def generated_schemas() -> dict[str, bytes]:
    """Return the complete deterministic filename-to-schema byte projection."""

    generated: dict[str, bytes] = {}
    for filename, model in _MODELS.items():
        schema = model.json_schema(mode="serialization") if isinstance(model, TypeAdapter) else model.model_json_schema(mode="serialization")
        schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
        schema["$id"] = f"{SCHEMA_BASE}/{filename}"
        generated[filename] = rfc8785.dumps(schema) + b"\n"
    return generated


def write_schemas(root: Path = SCHEMA_ROOT) -> tuple[Path, ...]:
    """Write every projection and return paths in canonical filename order."""

    root.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for filename, payload in generated_schemas().items():
        path = root / filename
        path.write_bytes(payload)
        paths.append(path)
    return tuple(paths)


def schema_parity(root: Path = SCHEMA_ROOT) -> tuple[str, ...]:
    """Return missing or byte-divergent committed schema filenames."""

    return tuple(
        filename
        for filename, expected in generated_schemas().items()
        if not (root / filename).is_file() or (root / filename).read_bytes() != expected
    )


if __name__ == "__main__":
    for generated_path in write_schemas():
        print(generated_path)


__all__ = ["SCHEMA_BASE", "SCHEMA_ROOT", "generated_schemas", "schema_parity", "write_schemas"]

"""Native computed Dung result schema; no document-derived arguments."""

from typing import Literal
from pydantic import Field
from rdam._native_output import DerivedFromRecord
from rdam._strict import StrictModel
from rdam.dung.semantics import DungInput


class ExtensionOutput(StrictModel):
    grounded: tuple[str, ...]
    complete: tuple[tuple[str, ...], ...]
    preferred: tuple[tuple[str, ...], ...]
    stable: tuple[tuple[str, ...], ...]


class AlgorithmOutput(StrictModel):
    name: Literal["exhaustive-subset"]
    version: Literal["1"]
    capacity: int = Field(gt=0)


class DungOutput(StrictModel):
    framework: DungInput
    input_origin: Literal["supplied", "explicitly_derived"]
    extensions: ExtensionOutput
    algorithm: AlgorithmOutput
    derived_from: DerivedFromRecord | None = Field(default=None, exclude_if=lambda value: value is None)

"""Native computed Dung result schema; no document-derived arguments."""

from typing import Literal, Self
from pydantic import Field, model_validator
from rdam._native_output import DerivedFromRecord
from rdam._strict import StrictModel
from rdam.dung.semantics import ArgumentationFramework, DungInput, evaluate


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

    @model_validator(mode="after")
    def extensions_reproduce_framework(self) -> Self:
        if (self.input_origin == "explicitly_derived") != (self.derived_from is not None):
            raise ValueError("Dung input origin must agree with its derivation reference")
        framework = ArgumentationFramework.from_payload(self.framework.model_dump(mode="json"))
        expected = evaluate(framework, capacity=self.algorithm.capacity).to_payload(framework)
        if self.extensions.model_dump(mode="json") != expected:
            raise ValueError("Dung extensions must reproduce the supplied framework")
        return self

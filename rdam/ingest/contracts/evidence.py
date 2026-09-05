"""Exact source passages shared by native analytical contracts."""

from typing import Self

from pydantic import Field, model_validator

from rdam._strict import StrictModel


class SourceEvidenceSpan(StrictModel):
    """Unicode character offsets, half-open, into the exact analysed text."""

    start: int = Field(ge=0)
    end: int = Field(gt=0)
    text: str = Field(min_length=1)

    @model_validator(mode="after")
    def coherent_range(self) -> Self:
        if self.end <= self.start or self.end - self.start != len(self.text):
            raise ValueError("evidence range must equal the quoted text length")
        self.text.encode("utf-8", errors="strict")
        return self

    def validate_source(self, text: str) -> None:
        if self.end > len(text) or text[self.start : self.end] != self.text:
            first = text.find(self.text)
            if first < 0:
                detail = "the proposed quotation has no literal occurrence in the source"
            elif first != text.rfind(self.text):
                detail = "the quotation has multiple literal occurrences; identify the intended source passage"
            else:
                detail = f"the quotation has a unique literal occurrence at [{first}, {first + len(self.text)})"
            raise ValueError(
                f"evidence at [{self.start}, {self.end}) does not match the analysed source; {detail}. "
                "Offsets count Unicode characters, not bytes. Resubmit evidence; validation does not repair it."
            )

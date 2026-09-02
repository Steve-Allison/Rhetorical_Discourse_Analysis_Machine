"""Document input models and coordinate representation."""

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4

from rdam.rst._version import resolve_installed_package_version
from rdam.rst.contracts.enums import InputFidelityEnum


@dataclass(frozen=True, slots=True)
class DocumentToken:
    """A single token aligned with character coordinates."""

    token_id: int
    text: str
    start: int
    end: int
    sentence_id: int | None = None
    paragraph_id: int | None = None

    def __post_init__(self) -> None:
        if self.start < 0 or self.end < self.start:
            raise ValueError(f"Invalid character span [{self.start}, {self.end}) for token {self.token_id}")


@dataclass(frozen=True, slots=True)
class Edu:
    """An elementary discourse unit (EDU) with character and token spans."""

    edu_id: int
    text: str
    start: int
    end: int
    token_ids: tuple[int, ...] = ()
    source_anchors: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.start < 0 or self.end < self.start:
            raise ValueError(f"Invalid character span [{self.start}, {self.end}) for EDU {self.edu_id}")


@dataclass(frozen=True, slots=True)
class TextSpan:
    """Character offset span in the original text."""

    start: int
    end: int
    text: str

    def __post_init__(self) -> None:
        if self.start < 0 or self.end < self.start:
            raise ValueError(f"Invalid character span [{self.start}, {self.end})")


@dataclass(frozen=True, slots=True)
class SourceReference:
    """Provenance pointer to the source document."""

    uri: str | None = None
    locator: str | None = None
    mime_type: str | None = None


@dataclass(frozen=True, slots=True)
class ProvenanceRecord:
    """Provenance and derivation record."""

    producer: str = "isanlp_rst"
    software_version: str = field(default_factory=resolve_installed_package_version)
    source_revision: str | None = None
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    model_id: str | None = None
    model_digest: str | None = None
    ontology_version: str | None = None
    ontology_digest: str | None = None


@dataclass(frozen=True, slots=True)
class RstDocument:
    """Lossless document representation for discourse parsing."""

    document_id: str
    text: str
    tokens: tuple[DocumentToken, ...] = ()
    edus: tuple[Edu, ...] | None = None
    sentence_boundaries: tuple[TextSpan, ...] = ()
    paragraph_boundaries: tuple[TextSpan, ...] = ()
    source: SourceReference | None = None
    language: str | None = None
    provenance: ProvenanceRecord = field(default_factory=ProvenanceRecord)
    fidelity: InputFidelityEnum = InputFidelityEnum.LOSSLESS

    @classmethod
    def from_text(
        cls,
        text: str,
        document_id: str | None = None,
        language: str | None = None,
        source: SourceReference | None = None,
        provenance: ProvenanceRecord | None = None,
    ) -> "RstDocument":
        """Create an RstDocument from raw text without pre-segmented EDUs."""
        doc_id = document_id or str(uuid4())
        prov = provenance or ProvenanceRecord()
        return cls(
            document_id=doc_id,
            text=text,
            tokens=(),
            edus=None,
            sentence_boundaries=(),
            paragraph_boundaries=(),
            source=source,
            language=language,
            provenance=prov,
            fidelity=InputFidelityEnum.LOSSLESS,
        )

    @classmethod
    def from_edus(
        cls,
        edus: Sequence[str],
        document_id: str | None = None,
        language: str | None = None,
        source: SourceReference | None = None,
        provenance: ProvenanceRecord | None = None,
    ) -> "RstDocument":
        """Create an RstDocument from pre-segmented EDU strings.

        Note: Character offsets are reconstructed by joining EDUs with spaces.
        Fidelity is marked as RECONSTRUCTED.
        """
        if not edus:
            raise ValueError("edus sequence must not be empty.")

        doc_id = document_id or str(uuid4())
        prov = provenance or ProvenanceRecord()

        constructed_parts: list[str] = []
        edu_objs: list[Edu] = []
        curr_offset = 0

        for idx, edu_str in enumerate(edus):
            if not isinstance(edu_str, str) or not edu_str.strip():
                raise ValueError(f"EDU at index {idx} must be a non-empty string.")
            if idx > 0:
                constructed_parts.append(" ")
                curr_offset += 1
            start = curr_offset
            constructed_parts.append(edu_str)
            curr_offset += len(edu_str)
            end = curr_offset
            edu_objs.append(Edu(edu_id=idx + 1, text=edu_str, start=start, end=end))

        full_text = "".join(constructed_parts)
        return cls(
            document_id=doc_id,
            text=full_text,
            tokens=(),
            edus=tuple(edu_objs),
            sentence_boundaries=(),
            paragraph_boundaries=(),
            source=source,
            language=language,
            provenance=prov,
            fidelity=InputFidelityEnum.RECONSTRUCTED,
        )

    @classmethod
    def from_tokens_and_edus(
        cls,
        text: str,
        tokens: Sequence[DocumentToken],
        edus: Sequence[Edu],
        sentence_boundaries: Sequence[TextSpan] = (),
        paragraph_boundaries: Sequence[TextSpan] = (),
        document_id: str | None = None,
        language: str | None = None,
        source: SourceReference | None = None,
        provenance: ProvenanceRecord | None = None,
        fidelity: InputFidelityEnum = InputFidelityEnum.LOSSLESS,
    ) -> "RstDocument":
        """Create an RstDocument with full token and EDU coordinates."""
        doc_id = document_id or str(uuid4())
        prov = provenance or ProvenanceRecord()
        return cls(
            document_id=doc_id,
            text=text,
            tokens=tuple(tokens),
            edus=tuple(edus),
            sentence_boundaries=tuple(sentence_boundaries),
            paragraph_boundaries=tuple(paragraph_boundaries),
            source=source,
            language=language,
            provenance=prov,
            fidelity=fidelity,
        )

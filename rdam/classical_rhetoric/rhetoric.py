"""Aristotelian pisteis, kairos, Hermagorean stasis, and rhetorical schemes with deterministic grounding."""

from collections import Counter
from typing import Annotated, Final, Literal, Self

from pydantic import Field, StringConstraints, model_validator
from razdel import tokenize

from rdam._grounding import GroundingCollector, QuoteRef
from rdam._strict import StrictModel
from rdam.ingest.contracts.evidence import SourceEvidenceSpan

type NonEmpty = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]

type PistisMode = Literal["ethos", "pathos", "logos"]

type EthosSubMode = Literal["phronesis", "arete", "eunoia"]
type LogosSubMode = Literal["enthymeme", "example", "maxim", "data_evidence"]
type StasisKind = Literal["conjectural", "definitional", "qualitative", "translative", "none"]
type RhetoricalScheme = Literal[
    "anaphora",
    "epistrophe",
    "antithesis",
    "tricolon",
    "rhetorical_question",
    "chiasmus",
    "klimax",
    "paraleipsis",
]

ETHOS_SUBMODES: Final[frozenset[str]] = frozenset({"phronesis", "arete", "eunoia"})
LOGOS_SUBMODES: Final[frozenset[str]] = frozenset({"enthymeme", "example", "maxim", "data_evidence"})


class ClassicalRhetoricError(ValueError):
    """Raised when a classical rhetoric proposal violates Aristotelian/stasis/scheme invariants."""


class AppealProposal(StrictModel):
    appeal_id: NonEmpty
    pistis: PistisMode
    sub_mode: NonEmpty
    rationale: NonEmpty
    evidence: QuoteRef

    @model_validator(mode="after")
    def validate_submode(self) -> Self:
        if self.pistis == "ethos" and self.sub_mode not in ETHOS_SUBMODES:
            raise ValueError(
                f"Appeal {self.appeal_id!r}: ethos sub_mode must be one of {sorted(ETHOS_SUBMODES)}, "
                f"got {self.sub_mode!r}."
            )
        if self.pistis == "logos" and self.sub_mode not in LOGOS_SUBMODES:
            raise ValueError(
                f"Appeal {self.appeal_id!r}: logos sub_mode must be one of {sorted(LOGOS_SUBMODES)}, "
                f"got {self.sub_mode!r}."
            )
        return self


class KairosCueProposal(StrictModel):
    cue_id: NonEmpty
    urgency_or_timeliness: NonEmpty
    evidence: QuoteRef


class StasisProposal(StrictModel):
    dominant_stasis: StasisKind
    contested_question: NonEmpty | None = None
    evidence: QuoteRef | None = None

    @model_validator(mode="after")
    def check_stasis_presence(self) -> Self:
        if self.dominant_stasis == "none":
            if self.contested_question is not None or self.evidence is not None:
                raise ValueError("dominant_stasis='none' requires contested_question=null and evidence=null")
        else:
            if self.contested_question is None or self.evidence is None:
                raise ValueError(
                    f"dominant_stasis={self.dominant_stasis!r} requires both contested_question and evidence"
                )
        return self


class RhetoricalFigureProposal(StrictModel):
    figure_id: NonEmpty
    scheme: RhetoricalScheme
    explanation: NonEmpty
    evidence: QuoteRef


def _has_repeated_word(text: str) -> bool:
    words = [tok.text.lower() for tok in tokenize(text) if any(ch.isalpha() for ch in tok.text)]
    counts = Counter(words)
    return any(count >= 2 for count in counts.values())


class ClassicalRhetoricProposal(StrictModel):
    appeals: list[AppealProposal] = Field(default_factory=list[AppealProposal])
    kairos_cues: list[KairosCueProposal] = Field(default_factory=list[KairosCueProposal])
    stasis: StasisProposal = StasisProposal(dominant_stasis="none")
    figures: list[RhetoricalFigureProposal] = Field(default_factory=list[RhetoricalFigureProposal])

    @model_validator(mode="after")
    def unique_identifiers(self) -> Self:
        for label, ids in (
            ("appeal_id", [a.appeal_id for a in self.appeals]),
            ("cue_id", [k.cue_id for k in self.kairos_cues]),
            ("figure_id", [f.figure_id for f in self.figures]),
        ):
            if len(set(ids)) != len(ids):
                raise ValueError(f"Duplicate {label} in ClassicalRhetoricProposal")
        return self

    def validate_source(
        self,
        source_text: str,
    ) -> tuple[
        dict[str, SourceEvidenceSpan],
        dict[str, SourceEvidenceSpan],
        SourceEvidenceSpan | None,
        dict[str, SourceEvidenceSpan],
    ]:
        collector = GroundingCollector(source_text)
        appeal_spans: dict[str, SourceEvidenceSpan] = {}
        kairos_spans: dict[str, SourceEvidenceSpan] = {}
        figure_spans: dict[str, SourceEvidenceSpan] = {}
        stasis_span: SourceEvidenceSpan | None = None

        for idx, app in enumerate(self.appeals):
            span = collector.resolve(app.evidence, field_name=f"appeals[{idx}] ({app.appeal_id}).evidence")
            if span is not None:
                appeal_spans[app.appeal_id] = span

        for idx, cue in enumerate(self.kairos_cues):
            span = collector.resolve(cue.evidence, field_name=f"kairos_cues[{idx}] ({cue.cue_id}).evidence")
            if span is not None:
                kairos_spans[cue.cue_id] = span

        if self.stasis.evidence is not None:
            stasis_span = collector.resolve(self.stasis.evidence, field_name="stasis.evidence")

        for idx, fig in enumerate(self.figures):
            span = collector.resolve(fig.evidence, field_name=f"figures[{idx}] ({fig.figure_id}).evidence")
            if span is not None:
                figure_spans[fig.figure_id] = span
                if fig.scheme == "rhetorical_question" and "?" not in span.text and "？" not in span.text:
                    collector.error(
                        f"figures[{idx}] ({fig.figure_id}): scheme='rhetorical_question' requires a question mark "
                        f"in its quoted span {span.text!r}."
                    )
                elif fig.scheme in {"anaphora", "epistrophe", "chiasmus"} and not _has_repeated_word(span.text):
                    collector.error(
                        f"figures[{idx}] ({fig.figure_id}): scheme={fig.scheme!r} requires lexical repetition "
                        f"within its quoted span {span.text!r}."
                    )

        try:
            collector.raise_if_errors()
        except ValueError as exc:
            raise ClassicalRhetoricError(str(exc)) from exc
        return appeal_spans, kairos_spans, stasis_span, figure_spans


__all__ = [
    "ETHOS_SUBMODES",
    "LOGOS_SUBMODES",
    "AppealProposal",
    "ClassicalRhetoricError",
    "ClassicalRhetoricProposal",
    "EthosSubMode",
    "KairosCueProposal",
    "LogosSubMode",
    "PistisMode",
    "RhetoricalFigureProposal",
    "RhetoricalScheme",
    "StasisKind",
    "StasisProposal",
]

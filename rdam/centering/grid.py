"""Deterministic Centering Theory (Grosz, Joshi & Weinstein 1995) and Entity Grid (Barzilay & Lapata 2008)."""

from dataclasses import dataclass
from typing import Final, Literal

from razdel import sentenize, tokenize

from rdam.concepts.linker import scan_text_mentions
from rdam.ingest.contracts.evidence import SourceEvidenceSpan
from rdam.ingest.substrate import LinguisticSubstrate, SentenceSpan, TokenSpan

type GrammaticalRole = Literal["S", "O", "X", "-"]
type CenteringTransition = Literal[
    "establishment",
    "continue",
    "retain",
    "smooth_shift",
    "rough_shift",
    "zero_cb",
]

ROLE_PRECEDENCE: Final[dict[GrammaticalRole, int]] = {"S": 0, "O": 1, "X": 2, "-": 3}

_STOPWORDS: Final[frozenset[str]] = frozenset(
    {
        "a", "an", "the", "this", "that", "these", "those", "some", "any", "each", "every", "all",
        "both", "either", "neither", "no", "nor", "not", "only", "just", "even", "also", "too", "very",
        "and", "or", "but", "yet", "so", "for", "because", "although", "though", "while", "whereas",
        "if", "unless", "until", "when", "whenever", "where", "wherever", "after", "before", "since",
        "as", "than", "whether", "however", "therefore", "thus", "hence", "moreover", "furthermore",
        "nevertheless", "nonetheless", "meanwhile", "instead", "otherwise", "consequently", "accordingly",
        "in", "on", "at", "by", "with", "from", "to", "of", "into", "onto", "upon", "over", "under",
        "above", "below", "between", "among", "through", "across", "against", "without", "within",
        "about", "around", "during", "despite", "beyond", "towards", "toward",
        "is", "are", "was", "were", "be", "been", "being", "am",
        "have", "has", "had", "having", "do", "does", "did", "doing",
        "can", "could", "may", "might", "must", "shall", "should", "will", "would",
        "who", "whom", "whose", "which", "what", "there", "here", "then", "now", "today", "always", "never",
    }
)

_PREPOSITIONS: Final[frozenset[str]] = frozenset(
    {
        "in", "on", "at", "by", "with", "from", "to", "of", "into", "onto", "upon",
        "over", "under", "above", "below", "between", "among", "through", "across",
        "against", "without", "within", "about", "around", "during", "despite", "beyond",
        "for", "towards", "toward", "via", "per",
    }
)

_FINITE_AUX_AND_VERBS: Final[frozenset[str]] = frozenset(
    {
        "is", "are", "was", "were", "has", "have", "had", "does", "do", "did",
        "can", "could", "may", "might", "must", "shall", "should", "will", "would",
        "shows", "show", "showed", "proves", "prove", "proved", "demonstrates", "demonstrate",
        "causes", "cause", "caused", "leads", "lead", "led", "requires", "require", "required",
        "supports", "support", "supported", "contradicts", "contradict", "prevents", "prevent",
        "reduces", "reduce", "reduced", "increases", "increase", "increased", "creates", "create",
        "produces", "produce", "produced", "provides", "provide", "provided", "makes", "make", "made",
        "uses", "use", "used", "includes", "include", "included", "contains", "contain", "contained",
        "affects", "affect", "affected", "explains", "explain", "explained", "implies", "imply",
        "means", "mean", "meant", "states", "state", "stated", "argues", "argue", "argued",
        "claims", "claim", "claimed", "suggests", "suggest", "suggested", "indicates", "indicate",
        "stopped", "left", "complained", "travelled", "traveled", "rained", "failed", "succeeded",
    }
)

_NEUTRAL_PRONOUNS: Final[frozenset[str]] = frozenset({"it", "its", "itself"})
_PLURAL_PRONOUNS: Final[frozenset[str]] = frozenset({"they", "them", "their", "theirs", "themselves"})
_ANIMATE_PRONOUNS: Final[frozenset[str]] = frozenset(
    {"he", "him", "his", "himself", "she", "her", "hers", "herself"}
)
_ALL_PRONOUNS: Final[frozenset[str]] = _NEUTRAL_PRONOUNS | _PLURAL_PRONOUNS | _ANIMATE_PRONOUNS


@dataclass(frozen=True, slots=True)
class EntityMention:
    utterance_id: str
    role: GrammaticalRole
    span: SourceEvidenceSpan
    is_pronoun: bool


@dataclass(frozen=True, slots=True)
class DiscourseEntity:
    entity_id: str
    canonical_name: str
    is_plural: bool
    mentions: tuple[EntityMention, ...]


@dataclass(frozen=True, slots=True)
class UtteranceRecord:
    utterance_id: str
    sentence_index: int
    start: int
    end: int
    text: str
    speaker: str | None
    cf_ranking: tuple[str, ...]
    cp: str | None
    cb: str | None
    transition: CenteringTransition


@dataclass(frozen=True, slots=True)
class CenteringGridAnalysis:
    entities: tuple[DiscourseEntity, ...]
    utterances: tuple[UtteranceRecord, ...]
    entity_grid: dict[str, tuple[GrammaticalRole, ...]]
    transition_counts: dict[CenteringTransition, int]
    local_coherence_score: float


def _normalize_entity_key(surface: str) -> tuple[str, bool]:
    words = [w.lower() for w in surface.split() if any(ch.isalnum() for ch in w)]
    while words and words[0] in _STOPWORDS:
        words.pop(0)
    if not words:
        return "", False
    head = words[-1]
    is_plural = False
    if len(head) > 4 and head.endswith("ies"):
        head = head[:-3] + "y"
        is_plural = True
    elif len(head) > 3 and head.endswith("s") and not head.endswith(("ss", "us", "is")):
        head = head[:-1]
        is_plural = True
    normalized = " ".join([*words[:-1], head])
    return normalized, is_plural


def _looks_verbal_token(lower: str) -> bool:
    if lower in _FINITE_AUX_AND_VERBS:
        return True
    return len(lower) > 4 and lower.endswith(("ed", "ing", "ates", "izes", "ises", "ifies"))


def _overlaps(start: int, end: int, occupied: list[tuple[int, int]]) -> bool:
    return any(start < o_end and o_start < end for o_start, o_end in occupied)


def _find_main_verb_offset(tokens: list[tuple[int, int, str]]) -> int | None:
    for idx, (start, _end, surface) in enumerate(tokens):
        lower = surface.lower()
        if idx > 0 and _looks_verbal_token(lower):
            return start
    return None


def _assign_role(
    mention_start: int,
    tokens: list[tuple[int, int, str]],
    verb_offset: int | None,
) -> GrammaticalRole:
    prev_word: str | None = None
    for t_start, _t_end, surface in tokens:
        if t_start >= mention_start:
            break
        if any(ch.isalnum() for ch in surface):
            prev_word = surface.lower()
    if prev_word is not None and prev_word in _PREPOSITIONS:
        return "X"
    if verb_offset is None or mention_start < verb_offset:
        return "S"
    return "O"


def _sentence_spans_from_text(source_text: str) -> tuple[SentenceSpan, ...]:
    sentences: list[SentenceSpan] = []
    for idx, sent in enumerate(sentenize(source_text)):
        raw = sent.text
        stripped = raw.strip()
        if not stripped:
            continue
        lead = len(raw) - len(raw.lstrip())
        s_start = sent.start + lead
        s_end = s_start + len(stripped)
        sentences.append(
            SentenceSpan(
                sentence_id=f"s_{idx}",
                unit_id="u_0",
                start=s_start,
                end=s_end,
                text=source_text[s_start:s_end],
                tokens=tuple(
                    TokenSpan(start=s_start + tok.start, end=s_start + tok.stop, text=tok.text)
                    for tok in tokenize(stripped)
                    if tok.text.strip()
                ),
            )
        )
    return tuple(sentences)


def analyse_centering(
    source_text: str,
    substrate: LinguisticSubstrate | None = None,
) -> CenteringGridAnalysis:
    """Compute the Centering Theory transition sequence and Barzilay–Lapata entity grid."""
    sentences = substrate.sentences if substrate is not None else _sentence_spans_from_text(source_text)
    speaker_by_unit = (
        {unit.unit_id: unit.speaker for unit in substrate.units}
        if substrate is not None
        else {}
    )

    if substrate is not None:
        concept_spans = [
            (sig.start, sig.end, sig.text)
            for sig in substrate.signals
            if sig.kind == "concept_mention"
        ]
    else:
        concept_spans = [
            (start, end, source_text[start:end])
            for start, end, _target in scan_text_mentions(source_text)
        ]

    entity_key_to_id: dict[str, str] = {}
    entity_names: dict[str, str] = {}
    entity_plural: dict[str, bool] = {}
    entity_mentions: dict[str, list[EntityMention]] = {}

    def register_entity(key: str, surface: str, is_plural: bool) -> str:
        existing = entity_key_to_id.get(key)
        if existing is not None:
            return existing
        ent_id = f"ent_{len(entity_key_to_id) + 1}"
        entity_key_to_id[key] = ent_id
        entity_names[ent_id] = surface
        entity_plural[ent_id] = is_plural
        entity_mentions[ent_id] = []
        return ent_id

    utterances: list[UtteranceRecord] = []
    prev_cf: tuple[str, ...] = ()
    prev_cb: str | None = None

    for u_idx, sent in enumerate(sentences):
        u_id = f"u_{u_idx + 1}"
        tokens = [(tok.start, tok.end, tok.text) for tok in sent.tokens]
        verb_offset = _find_main_verb_offset(tokens)
        occupied: list[tuple[int, int]] = []
        local_mentions: list[tuple[str, GrammaticalRole, SourceEvidenceSpan, bool]] = []

        # 1. Concept-linked multi-word / domain terms inside this sentence
        for c_start, c_end, surface in concept_spans:
            if c_start < sent.start or c_end > sent.end or _overlaps(c_start, c_end, occupied):
                continue
            key, is_plural = _normalize_entity_key(surface)
            if not key or key in _STOPWORDS or key in _ALL_PRONOUNS:
                continue
            ent_id = register_entity(key, surface, is_plural)
            role = _assign_role(c_start, tokens, verb_offset)
            span = SourceEvidenceSpan(start=c_start, end=c_end, text=source_text[c_start:c_end])
            occupied.append((c_start, c_end))
            local_mentions.append((ent_id, role, span, False))

        # 2. Multi-token TitleCase proper noun phrases and substantive head nouns
        idx = 0
        while idx < len(tokens):
            t_start, t_end, surface = tokens[idx]
            lower = surface.lower()
            if _overlaps(t_start, t_end, occupied) or not any(ch.isalpha() for ch in surface):
                idx += 1
                continue

            # Pronoun resolution against preceding Cf ranking
            if lower in _ALL_PRONOUNS and prev_cf:
                want_plural = lower in _PLURAL_PRONOUNS
                resolved_ent: str | None = None
                for cand_id in prev_cf:
                    if entity_plural[cand_id] == want_plural:
                        resolved_ent = cand_id
                        break
                if resolved_ent is None:
                    resolved_ent = prev_cf[0]
                role = _assign_role(t_start, tokens, verb_offset)
                span = SourceEvidenceSpan(start=t_start, end=t_end, text=source_text[t_start:t_end])
                occupied.append((t_start, t_end))
                local_mentions.append((resolved_ent, role, span, True))
                idx += 1
                continue

            # Proper noun span (non-sentence-initial capitalized or multi-word capitalized)
            if surface[0].isupper() and lower not in _STOPWORDS and lower not in _ALL_PRONOUNS:
                end_idx = idx
                while end_idx + 1 < len(tokens):
                    nt_start, nt_end, n_surf = tokens[end_idx + 1]
                    if (
                        not _overlaps(nt_start, nt_end, occupied)
                        and n_surf
                        and n_surf[0].isupper()
                        and n_surf.lower() not in _STOPWORDS
                        and nt_start - tokens[end_idx][1] <= 2
                    ):
                        end_idx += 1
                    else:
                        break
                if end_idx > idx or idx > 0:
                    p_start = t_start
                    p_end = tokens[end_idx][1]
                    phrase = source_text[p_start:p_end]
                    key, is_plural = _normalize_entity_key(phrase)
                    if key and key not in _STOPWORDS and not _looks_verbal_token(key):
                        ent_id = register_entity(key, phrase, is_plural)
                        role = _assign_role(p_start, tokens, verb_offset)
                        span = SourceEvidenceSpan(start=p_start, end=p_end, text=phrase)
                        occupied.append((p_start, p_end))
                        local_mentions.append((ent_id, role, span, False))
                        idx = end_idx + 1
                        continue

            # Common nominal heads (preceded by determiner/possessive/adjective or pre-verbal noun)
            prev_lower = tokens[idx - 1][2].lower() if idx > 0 else ""
            next_lower = tokens[idx + 1][2].lower() if idx + 1 < len(tokens) else ""
            is_determiner_headed = prev_lower in {
                "the", "a", "an", "this", "that", "these", "those", "our", "their", "its", "his", "her",
                "each", "every", "some", "any", "no", "many", "several",
            }
            if (
                len(lower) >= 3
                and lower.isalpha()
                and lower not in _STOPWORDS
                and lower not in _ALL_PRONOUNS
                and not _looks_verbal_token(lower)
                and not lower.endswith(("ly", "ous", "ive", "able", "ible", "ful", "less"))
                and (is_determiner_headed or (verb_offset is not None and t_start < verb_offset))
                and not (next_lower.isalpha() and next_lower not in _STOPWORDS and not _looks_verbal_token(next_lower))
            ):
                key, is_plural = _normalize_entity_key(surface)
                if key and key not in _STOPWORDS:
                    ent_id = register_entity(key, surface, is_plural)
                    role = _assign_role(t_start, tokens, verb_offset)
                    span = SourceEvidenceSpan(start=t_start, end=t_end, text=source_text[t_start:t_end])
                    occupied.append((t_start, t_end))
                    local_mentions.append((ent_id, role, span, False))
            idx += 1

        best_role_per_ent: dict[str, tuple[int, int]] = {}
        for ent_id, role, span, is_pronoun in local_mentions:
            entity_mentions[ent_id].append(
                EntityMention(utterance_id=u_id, role=role, span=span, is_pronoun=is_pronoun)
            )
            rank = ROLE_PRECEDENCE[role]
            existing_rank = best_role_per_ent.get(ent_id)
            if existing_rank is None or (rank, span.start) < existing_rank:
                best_role_per_ent[ent_id] = (rank, span.start)

        cf_ranking = tuple(
            ent_id for ent_id, _ in sorted(best_role_per_ent.items(), key=lambda item: item[1])
        )
        cp = cf_ranking[0] if cf_ranking else None

        if u_idx == 0:
            cb = None
            transition: CenteringTransition = "establishment" if cf_ranking else "zero_cb"
        elif not prev_cf:
            cb = None
            transition = "establishment" if cf_ranking else "zero_cb"
        else:
            realized_set = set(cf_ranking)
            cb = next((ent_id for ent_id in prev_cf if ent_id in realized_set), None)
            effective_prev_cb = prev_cb if prev_cb is not None else prev_cf[0]
            if cb is None:
                transition = "zero_cb"
            elif cb == effective_prev_cb:
                transition = "continue" if cb == cp else "retain"
            else:
                transition = "smooth_shift" if cb == cp else "rough_shift"

        utterances.append(
            UtteranceRecord(
                utterance_id=u_id,
                sentence_index=u_idx,
                start=sent.start,
                end=sent.end,
                text=sent.text,
                speaker=speaker_by_unit.get(sent.unit_id) if sent.unit_id is not None else None,
                cf_ranking=cf_ranking,
                cp=cp,
                cb=cb,
                transition=transition,
            )
        )
        prev_cf = cf_ranking
        prev_cb = cb

    entities = tuple(
        DiscourseEntity(
            entity_id=ent_id,
            canonical_name=entity_names[ent_id],
            is_plural=entity_plural[ent_id],
            mentions=tuple(entity_mentions[ent_id]),
        )
        for ent_id in entity_key_to_id.values()
        if entity_mentions[ent_id]
    )

    utterance_ids = [u.utterance_id for u in utterances]
    entity_grid: dict[str, tuple[GrammaticalRole, ...]] = {}
    for ent in entities:
        role_by_utt: dict[str, GrammaticalRole] = {}
        for m in ent.mentions:
            prev_role = role_by_utt.get(m.utterance_id, "-")
            if ROLE_PRECEDENCE[m.role] < ROLE_PRECEDENCE[prev_role]:
                role_by_utt[m.utterance_id] = m.role
        entity_grid[ent.entity_id] = tuple(role_by_utt.get(uid, "-") for uid in utterance_ids)

    counts: dict[CenteringTransition, int] = {
        "establishment": 0,
        "continue": 0,
        "retain": 0,
        "smooth_shift": 0,
        "rough_shift": 0,
        "zero_cb": 0,
    }
    for u in utterances:
        counts[u.transition] += 1

    scored_total = (
        counts["continue"]
        + counts["retain"]
        + counts["smooth_shift"]
        + counts["rough_shift"]
        + (counts["zero_cb"] if len(utterances) > 1 else 0)
    )
    if scored_total == 0:
        coherence_score = 1.0 if utterances else 0.0
    else:
        weighted = (
            1.0 * counts["continue"]
            + 0.75 * counts["retain"]
            + 0.5 * counts["smooth_shift"]
            + 0.15 * counts["rough_shift"]
        )
        coherence_score = round(min(1.0, max(0.0, weighted / scored_total)), 4)

    return CenteringGridAnalysis(
        entities=entities,
        utterances=tuple(utterances),
        entity_grid=entity_grid,
        transition_counts=counts,
        local_coherence_score=coherence_score,
    )


__all__ = [
    "ROLE_PRECEDENCE",
    "CenteringGridAnalysis",
    "CenteringTransition",
    "DiscourseEntity",
    "EntityMention",
    "GrammaticalRole",
    "UtteranceRecord",
    "analyse_centering",
]

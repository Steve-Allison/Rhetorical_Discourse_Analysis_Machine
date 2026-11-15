"""Deterministic Hamblin (1970) / Walton & Krabbe (1995) dialogue commitment-store replay."""

from collections.abc import Sequence
from dataclasses import dataclass

from rdam.speech_acts.acts import SpeechActItemProposal


def _canonical_prop(text: str) -> str:
    collapsed = " ".join(text.strip().lower().split())
    return collapsed.rstrip(".!;")


def _negation_pair(prop_a: str, prop_b: str) -> bool:
    a = _canonical_prop(prop_a)
    b = _canonical_prop(prop_b)
    if not a or not b or a == b:
        return False
    for prefix in ("not ", "it is false that ", "it is not the case that "):
        if a == prefix + b or b == prefix + a:
            return True
    if " is not " in a and a.replace(" is not ", " is ", 1) == b:
        return True
    if " is not " in b and b.replace(" is not ", " is ", 1) == a:
        return True
    if " does not " in a and a.replace(" does not ", " does ", 1) == b:
        return True
    return " does not " in b and b.replace(" does not ", " does ", 1) == a


@dataclass(frozen=True, slots=True)
class SpeakerCommitmentState:
    speaker: str
    active_commitments: tuple[str, ...]
    retracted_commitments: tuple[str, ...]
    challenges_raised: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CommitmentConflict:
    speaker: str
    earlier_act_id: str
    later_act_id: str
    earlier_proposition: str
    later_proposition: str


@dataclass(frozen=True, slots=True)
class CommitmentStoreSummary:
    speakers: tuple[SpeakerCommitmentState, ...]
    conflicts: tuple[CommitmentConflict, ...]


def replay_commitments(acts: Sequence[SpeechActItemProposal]) -> CommitmentStoreSummary:
    """Replay ordered speech acts into per-speaker Hamblin commitment stores."""
    speaker_order: list[str] = []
    active_by_speaker: dict[str, dict[str, tuple[str, str]]] = {}
    retracted_by_speaker: dict[str, list[str]] = {}
    challenges_by_speaker: dict[str, list[str]] = {}
    conflicts: list[CommitmentConflict] = []

    for act in acts:
        spk = act.speaker
        if spk not in active_by_speaker:
            speaker_order.append(spk)
            active_by_speaker[spk] = {}
            retracted_by_speaker[spk] = []
            challenges_by_speaker[spk] = []

        store = active_by_speaker[spk]
        op = act.commitment_operation
        if op in {"assert", "concede"}:
            key = _canonical_prop(act.propositional_content)
            for existing_key, (earlier_act_id, earlier_prop) in store.items():
                if _negation_pair(existing_key, key):
                    conflicts.append(
                        CommitmentConflict(
                            speaker=spk,
                            earlier_act_id=earlier_act_id,
                            later_act_id=act.act_id,
                            earlier_proposition=earlier_prop,
                            later_proposition=act.propositional_content,
                        )
                    )
            if key not in store:
                store[key] = (act.act_id, act.propositional_content)
        elif op == "retract" and act.target_proposition is not None:
            t_key = _canonical_prop(act.target_proposition)
            removed = store.pop(t_key, None)
            retracted_text = removed[1] if removed is not None else act.target_proposition
            if retracted_text not in retracted_by_speaker[spk]:
                retracted_by_speaker[spk].append(retracted_text)
        elif (
            op == "challenge"
            and act.target_proposition is not None
            and act.target_proposition not in challenges_by_speaker[spk]
        ):
            challenges_by_speaker[spk].append(act.target_proposition)

    speakers = tuple(
        SpeakerCommitmentState(
            speaker=spk,
            active_commitments=tuple(prop for _aid, prop in active_by_speaker[spk].values()),
            retracted_commitments=tuple(retracted_by_speaker[spk]),
            challenges_raised=tuple(challenges_by_speaker[spk]),
        )
        for spk in speaker_order
    )
    return CommitmentStoreSummary(speakers=speakers, conflicts=tuple(conflicts))


__all__ = [
    "CommitmentConflict",
    "CommitmentStoreSummary",
    "SpeakerCommitmentState",
    "replay_commitments",
]

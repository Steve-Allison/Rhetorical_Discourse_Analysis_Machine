"""Immutable snapshots of decisions taken by the production decoding networks."""

from collections.abc import Sequence
from dataclasses import dataclass
import math

from torch import Tensor

from rdam.ingest.contracts.decoding import NetworkTransitionDecision


@dataclass(frozen=True, slots=True)
class NetworkStructureDecision:
    """One local decision, in zero-based inclusive EDU coordinates.

    Joint scores retain the network's relation/nuclearity class order, including
    masked classes with log probability -inf. A missing split distribution means
    either a forced two-EDU split or a bottom-up transition sequence. Transition
    records occur once, on the reduction that follows them.
    These are conditional decoding scores, not calibrated tree probabilities.
    """

    start: int
    end: int
    split: int
    joint_labels: tuple[str, ...]
    selected_class: int
    joint_log_probabilities: tuple[float, ...]
    split_log_probabilities: tuple[float, ...] | None
    transitions: tuple[NetworkTransitionDecision, ...] = ()

    def __post_init__(self) -> None:
        if not 0 <= self.start <= self.split < self.end:
            raise ValueError("network decision has an invalid constituent or split")
        if not self.joint_labels or len(self.joint_labels) != len(self.joint_log_probabilities):
            raise ValueError("network class labels and scores must have equal nonzero length")
        if not 0 <= self.selected_class < len(self.joint_labels):
            raise ValueError("selected network class is outside its inventory")
        for label in self.joint_labels:
            relation, separator, nuclearity = label.rpartition("_")
            if not relation or not separator or nuclearity.upper() not in {"NS", "SN", "NN"}:
                raise ValueError(f"invalid joint relation/nuclearity label: {label!r}")
        self._validate_log_probabilities(self.joint_log_probabilities)
        if not math.isfinite(self.joint_log_probabilities[self.selected_class]):
            raise ValueError("selected network class cannot be masked")
        if self.joint_log_probabilities[self.selected_class] != max(self.joint_log_probabilities):
            raise ValueError("selected network class contradicts its scores")
        if self.transitions:
            if self.split_log_probabilities is not None:
                raise ValueError("bottom-up transitions cannot carry top-down split scores")
            final = self.transitions[-1]
            if final.applied_action != 1 or final.stack_spans[-2:] != (
                (self.start, self.split),
                (self.split + 1, self.end),
            ):
                raise ValueError("reduction state contradicts its constituent")
        elif self.split_log_probabilities is None:
            if self.end - self.start != 1:
                raise ValueError("only a two-EDU constituent has a forced split")
        else:
            if len(self.split_log_probabilities) != self.end - self.start:
                raise ValueError("split score count differs from legal split count")
            self._validate_log_probabilities(self.split_log_probabilities)
            selected = self.split_log_probabilities[self.split - self.start]
            if not math.isfinite(selected) or selected != max(self.split_log_probabilities):
                raise ValueError("selected split contradicts its scores")

    @staticmethod
    def _validate_log_probabilities(values: tuple[float, ...]) -> None:
        if any(math.isnan(value) or value > 0.0 for value in values):
            raise ValueError("network log probabilities must be nonpositive and not NaN")


def capture_structure_decision(
    destination: list[NetworkStructureDecision] | None,
    *,
    start: int,
    end: int,
    split: int,
    joint_labels: Sequence[str],
    selected_class: int,
    joint_log_probabilities: Tensor,
    split_log_probabilities: Tensor | None = None,
    transitions: tuple[NetworkTransitionDecision, ...] = (),
) -> None:
    """Copy scores from the actual forward pass without changing model state."""

    if destination is None:
        return
    destination.append(
        NetworkStructureDecision(
            start=start,
            end=end,
            split=split,
            joint_labels=tuple(joint_labels),
            selected_class=selected_class,
            transitions=transitions,
            joint_log_probabilities=tuple(
                float(value) for value in joint_log_probabilities.detach().cpu().reshape(-1).unbind()
            ),
            split_log_probabilities=(
                tuple(float(value) for value in split_log_probabilities.detach().cpu().reshape(-1).unbind())
                if split_log_probabilities is not None
                else None
            ),
        )
    )

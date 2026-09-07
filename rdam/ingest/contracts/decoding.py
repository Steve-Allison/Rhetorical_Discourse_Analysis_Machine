"""Backend-independent immutable decoder transition evidence."""

from dataclasses import dataclass
import math


@dataclass(frozen=True, slots=True)
class NetworkTransitionDecision:
    """Actual bottom-up action logits and the state constraining their execution.

    Action indices follow the trained classifier: SHIFT=0, REDUCE=1. The
    selected action is the raw argmax; the applied action obeys stack/buffer
    constraints. These must remain distinct when the decoder forces an action.
    """

    stack_spans: tuple[tuple[int, int], ...]
    next_edu: int | None
    action_logits: tuple[float, ...]
    selected_action: int
    applied_action: int

    def __post_init__(self) -> None:
        if len(self.action_logits) != 2 or not all(math.isfinite(value) for value in self.action_logits):
            raise ValueError("transition requires finite SHIFT and REDUCE logits")
        if self.selected_action != self.action_logits.index(max(self.action_logits)):
            raise ValueError("selected transition contradicts its logits")
        if any(start < 0 or end < start for start, end in self.stack_spans):
            raise ValueError("transition stack contains an invalid EDU span")
        if any(left[1] + 1 != right[0] for left, right in zip(self.stack_spans, self.stack_spans[1:], strict=False)):
            raise ValueError("transition stack spans must be contiguous")
        if self.next_edu is not None and (
            self.next_edu < 0 or (self.stack_spans and self.stack_spans[-1][1] + 1 != self.next_edu)
        ):
            raise ValueError("transition buffer must follow the stack")
        if self.next_edu is None and len(self.stack_spans) < 2:
            raise ValueError("completed decoder state cannot take a transition")
        expected = self.selected_action
        if len(self.stack_spans) < 2:
            expected = 0
        elif self.next_edu is None:
            expected = 1
        if self.applied_action != expected:
            raise ValueError("applied transition contradicts the decoder constraints")

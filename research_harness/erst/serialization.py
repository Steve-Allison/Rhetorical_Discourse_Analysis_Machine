"""Deterministic serialization for signal-aware pairwise eRST systems."""

from research_harness.erst.contracts import (
    EdgeDirection,
    SignalLocation,
    SignalMarkedExample,
)


def _marked_text(text: str, start: int, end: int) -> str:
    return f"{text[:start]}**{text[start:end]}**{text[end:]}"


def serialize_signal_marked_example(example: SignalMarkedExample) -> str:
    """Serialize one signal-aware pairwise candidate without external authority assumptions."""

    source = example.source_text
    target = example.target_text
    if example.signal_location == SignalLocation.SOURCE:
        source = _marked_text(source, example.signal_start, example.signal_end)
    else:
        target = _marked_text(target, example.signal_start, example.signal_end)

    relation = example.relation_raw.replace("-", " ")
    same_path_relation = example.same_path_relation_raw or "_"
    prefix = (
        f"{relation} ( {same_path_relation} ) {example.direction.value} "
        f"{example.head_edu_distance} : "
    )
    if example.direction == EdgeDirection.RIGHT:
        payload = f"{target} << {source}"
    else:
        payload = f"{source} >> {target}"
    if example.label is None:
        return prefix + payload
    return f"__label__{str(example.label)}\t{prefix}{payload}"


__all__ = ["serialize_signal_marked_example"]

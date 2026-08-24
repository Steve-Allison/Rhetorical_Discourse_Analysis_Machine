"""Deterministic serialization for the published eRST association baseline."""

from isanlp_rst.contracts.research import (
    BaselineDirection,
    BaselineSignalLocation,
    PublishedBaselineExample,
)


def _marked_text(text: str, start: int, end: int) -> str:
    return f"{text[:start]}**{text[start:end]}**{text[end:]}"


def serialize_published_baseline(example: PublishedBaselineExample) -> str:
    """Serialize exactly one released signal-association classifier example."""

    source = example.source_text
    target = example.target_text
    if example.signal_location == BaselineSignalLocation.SOURCE:
        source = _marked_text(source, example.signal_start, example.signal_end)
    else:
        target = _marked_text(target, example.signal_start, example.signal_end)

    relation = example.relation_raw.replace("-", " ")
    same_path_relation = example.same_path_relation_raw or "_"
    prefix = (
        f"{relation} ( {same_path_relation} ) {example.direction.value} "
        f"{example.head_edu_distance} : "
    )
    if example.direction == BaselineDirection.RIGHT:
        payload = f"{target} << {source}"
    else:
        payload = f"{source} >> {target}"
    if example.label is None:
        return prefix + payload
    return f"__label__{str(example.label)}\t{prefix}{payload}"


__all__ = ["serialize_published_baseline"]

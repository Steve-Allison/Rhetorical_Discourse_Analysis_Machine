"""Shared source-order front/back matter classification."""

from rdam.ingest.contracts.source import ContentClass


def back_matter_classes(items: tuple[tuple[ContentClass, str | None], ...]) -> tuple[ContentClass, ...]:
    revised = list(items)
    abstract_index = next(
        (
            index
            for index, item in enumerate(revised)
            if item[0] is ContentClass.HEADING and (item[1] or "").strip().casefold() == "abstract"
        ),
        None,
    )
    if abstract_index is not None:
        first_heading = next(
            (
                index
                for index, item in enumerate(revised[:abstract_index])
                if item[0] in {ContentClass.TITLE, ContentClass.HEADING}
            ),
            None,
        )
        if first_heading is not None:
            for index in range(first_heading + 1, abstract_index):
                if revised[index][0] in {ContentClass.PARAGRAPH, ContentClass.LIST_ITEM}:
                    revised[index] = (ContentClass.METADATA, revised[index][1])
    back_matter = False
    for index, item in enumerate(revised):
        if item[0] in {ContentClass.TITLE, ContentClass.HEADING}:
            heading = " ".join((item[1] or "").casefold().split()).rstrip(":")
            if heading in {"references", "bibliography", "works cited"}:
                back_matter = True
        if back_matter and item[0] in {
            ContentClass.TITLE,
            ContentClass.HEADING,
            ContentClass.PARAGRAPH,
            ContentClass.LIST_ITEM,
        }:
            revised[index] = (ContentClass.NAVIGATION, item[1])
    return tuple(item[0] for item in revised)

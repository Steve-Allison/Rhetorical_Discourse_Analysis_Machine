"""Resolve only explicit source speaker labels; never infer attribution."""

import re

from rdam.ingest.contracts.source import SpeakerIdentity
from rdam.ingest.identity import sha256_bytes

_LABEL = re.compile(r"^\s*(?:\*\*)?([^:\n]+?)(?: \(participant ([\w.-]+)\))?:(?:\*\*)?\s+")
_UNATTRIBUTED = frozenset({"unattributed", "unknown", "unidentified", "?"})


def explicitly_marked_turn(text: str) -> bool:
    """Markdown marks a speaker label explicitly; ordinary prose colons are not turns."""
    return text.lstrip().startswith("**") and _LABEL.match(text) is not None


def resolve_speaker(text: str, attributes: tuple[tuple[str, str], ...] = ()) -> SpeakerIdentity:
    values = dict(attributes)
    participant = values.get("participant_id")
    name = values.get("speaker")
    if participant:
        return SpeakerIdentity(resolution="resolved", participant_id=participant, display_name=name,
                               evidence="Source participant_id attribute: " + participant)
    match = _LABEL.match(text)
    if match is None:
        return SpeakerIdentity(resolution="unresolved", evidence="The source turn supplies no explicit speaker label or participant identifier.")
    display_name, explicit_id = match.groups()
    display_name = display_name.strip()
    if display_name.casefold() in _UNATTRIBUTED:
        return SpeakerIdentity(resolution="unresolved", display_name=display_name,
                               evidence="Source explicitly labels this turn " + display_name)
    # The exact label is the identity when the source supplies no participant key.
    # We do not merge alternate spellings or equal names carrying different explicit keys.
    identity = explicit_id or "label:" + sha256_bytes(display_name.encode("utf-8"))
    return SpeakerIdentity(resolution="resolved", participant_id=identity, display_name=display_name,
                           evidence="Explicit source speaker prefix: " + match.group(0).strip())

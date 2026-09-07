"""Split a narration script into role-labelled segments.

A voice change is a structural signal -- the audio equivalent of a heading --
so it has to mean the same thing in every episode. The narrator carries the
explanation, one voice marks the trade-off, and one voice always closes on the
exercise. A listener learns that last cue once and then recognises it for the
rest of the course.

The labels are stage directions. They are stripped before anything is spoken.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# Order is meaningless here; the script decides. These are just the roles a
# script is allowed to name.
ROLES = ("narrator", "tradeoff", "exercise")

LABEL = re.compile(r"^([A-Z][A-Z_]+):[ \t]*", re.MULTILINE)


class SegmentError(Exception):
    """A script could not be split into speakable segments."""


@dataclass(frozen=True)
class Segment:
    role: str
    text: str


def parse_segments(script: str) -> list[Segment]:
    """Split `script` into segments, or raise if it does not follow the format."""
    matches = list(LABEL.finditer(script))
    if not matches:
        raise SegmentError(
            "script has no role labels; expected lines beginning "
            f"{', '.join(r.upper() + ':' for r in ROLES)}"
        )

    segments: list[Segment] = []
    for index, match in enumerate(matches):
        label = match.group(1)
        if label.lower() not in ROLES:
            raise SegmentError(
                f"unknown role {label!r}; expected one of "
                f"{', '.join(r.upper() for r in ROLES)}"
            )
        end = matches[index + 1].start() if index + 1 < len(matches) else len(script)
        text = " ".join(script[match.end():end].split())
        if not text:
            raise SegmentError(f"role {label} has no text")
        segments.append(Segment(role=label.lower(), text=text))

    exercises = [s for s in segments if s.role == "exercise"]
    if len(exercises) != 1:
        raise SegmentError(
            f"expected exactly one exercise segment, found {len(exercises)}"
        )
    if segments[-1].role != "exercise":
        raise SegmentError(
            "the exercise must be the last segment: every episode ends in action, "
            "and the exercise voice is the cue that it is time to act"
        )
    return segments


def spoken_text(segments: list[Segment]) -> str:
    """Everything the listener actually hears, labels removed.

    This is what the sanitizer checks: the labels are never spoken, so they are
    not the sanitizer's business.
    """
    return "\n\n".join(s.text for s in segments)

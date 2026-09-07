import pytest

from audiodocs.segments import (
    ROLES, Segment, SegmentError, parse_segments, spoken_text,
)


GOOD = """NARRATOR: Last time we covered skills, and today we take on hooks.
A hook is a command the harness runs for you at a defined moment.

TRADEOFF: What a hook costs you is selectivity. It runs on every matching
event, whether or not you meant it to.

NARRATOR: So the matcher is the whole game. Write it narrowly.

EXERCISE: Add a hook that logs every Bash command, then run three of them
and read the log.
"""


def test_parses_roles_in_order():
    segs = parse_segments(GOOD)
    assert [s.role for s in segs] == ["narrator", "tradeoff", "narrator", "exercise"]
    assert segs[1].text.startswith("What a hook costs you")


def test_labels_are_never_spoken():
    """The role label is a stage direction. Speaking "narrator colon" aloud is
    the single most obvious way this feature can embarrass itself."""
    text = spoken_text(parse_segments(GOOD))
    for role in ROLES:
        assert role.upper() not in text
    assert ":" not in text.split("\n")[0][:12]


def test_an_episode_must_end_on_the_exercise():
    """INTENT.md: every episode ends in action. The exercise voice is the cue,
    so it has to be the last thing heard."""
    bad = GOOD.replace(
        "EXERCISE: Add a hook", "EXERCISE: Add a hook"
    ) + "\nNARRATOR: One more thought.\n"
    with pytest.raises(SegmentError) as exc:
        parse_segments(bad)
    assert "exercise" in str(exc.value).lower()


def test_exactly_one_exercise():
    bad = GOOD + "\nEXERCISE: And also do this other thing.\n"
    with pytest.raises(SegmentError):
        parse_segments(bad)


def test_an_unknown_role_is_an_error_not_narration():
    """Silently narrating an unrecognized label would speak it aloud."""
    with pytest.raises(SegmentError) as exc:
        parse_segments("NARRATOR: Hello.\n\nASIDE: Psst.\n\nEXERCISE: Go do it.\n")
    assert "ASIDE" in str(exc.value)


def test_an_unlabelled_script_is_an_error():
    """Loud failure: a model that ignores the format must not slip through as
    one giant unattributed block."""
    with pytest.raises(SegmentError):
        parse_segments("Just some narration with no roles at all.")


def test_empty_segments_are_rejected():
    with pytest.raises(SegmentError):
        parse_segments("NARRATOR:\n\nEXERCISE: Go do it.\n")

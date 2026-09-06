import numpy as np
import pytest

from audiodocs.speak import (
    NATURAL_WPM, SpeakError, speed_for, synthesize_segments,
)
from audiodocs.segments import Segment

CAST = {"narrator": "af_heart", "tradeoff": "bf_emma", "exercise": "am_michael"}
SEGS = [
    Segment("narrator", "The context window is one shared workspace."),
    Segment("tradeoff", "What it costs you is room for everything else."),
    Segment("exercise", "Run the context command and read the breakdown."),
]


def _engine(calls):
    """A stand-in for Kokoro. Returns a second of silence per call and records
    what it was asked to say, in which voice, at what speed."""
    def engine(text, voice, speed):
        calls.append((voice, round(speed, 3), text[:24]))
        return np.zeros(24000, dtype=np.float32)
    return engine


def test_each_role_is_spoken_in_its_own_voice(tmp_path):
    calls = []
    synthesize_segments(SEGS, CAST, 165, tmp_path / "e.m4a", engine=_engine(calls))
    assert [c[0] for c in calls] == ["af_heart", "bf_emma", "am_michael"]


def test_pace_is_normalized_per_voice(tmp_path):
    """Voices differ by 70 wpm at their natural rate. A switch should change the
    timbre, not the tempo -- a jump from 193 to 263 wpm mid-episode reads as a
    fault, not a signal."""
    calls = []
    synthesize_segments(SEGS, CAST, 165, tmp_path / "e.m4a", engine=_engine(calls))
    for voice, speed, _ in calls:
        assert abs(165 / NATURAL_WPM[voice] - speed) < 0.01


def test_speed_is_clamped_to_something_intelligible():
    """A pace far from a voice's natural rate destroys it. Better to refuse the
    extreme than to ship 43 episodes of chipmunk."""
    assert speed_for("am_fenrir", 40) >= 0.5
    assert speed_for("af_heart", 900) <= 2.0


def test_an_uncast_voice_is_rejected_before_synthesis(tmp_path):
    calls = []
    with pytest.raises(SpeakError, match="not a known voice"):
        synthesize_segments(
            SEGS, {**CAST, "tradeoff": "nope"}, 165,
            tmp_path / "e.m4a", engine=_engine(calls),
        )
    assert calls == [], "synthesis started before the cast was validated"


def test_empty_segments_are_rejected(tmp_path):
    with pytest.raises(SpeakError, match="empty"):
        synthesize_segments([], CAST, 165, tmp_path / "e.m4a", engine=_engine([]))


def test_segments_are_joined_with_a_pause(tmp_path):
    """Butt-joining two voices sounds like a splice. A beat of silence reads as
    a deliberate change of speaker."""
    calls = []
    out = synthesize_segments(
        SEGS, CAST, 165, tmp_path / "e.m4a", engine=_engine(calls)
    )
    assert out.exists()
    # 3 segments of 1s each, plus the gaps between them.
    assert out.stat().st_size > 1000


@pytest.mark.smoke
def test_real_kokoro_produces_a_playable_multi_voice_file(tmp_path):
    out = synthesize_segments(SEGS, CAST, 165, tmp_path / "smoke.m4a")
    assert out.exists() and out.stat().st_size > 5000
    assert not list(tmp_path.glob("*.wav")), "intermediate must be cleaned up"

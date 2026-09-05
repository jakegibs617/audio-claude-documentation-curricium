import pytest
from audiodocs.speak import synthesize, available_voices, SpeakError


def test_available_voices_includes_samantha():
    assert "Samantha" in available_voices()


def test_rejects_unavailable_voice(tmp_path):
    with pytest.raises(SpeakError, match="voice not installed"):
        synthesize("hello", tmp_path / "x.m4a", voice="NoSuchVoice")


def test_rejects_empty_text(tmp_path):
    with pytest.raises(SpeakError, match="empty"):
        synthesize("   ", tmp_path / "x.m4a")


@pytest.mark.smoke
def test_produces_a_playable_audio_file(tmp_path):
    out = synthesize("Testing one two three.", tmp_path / "smoke.m4a")
    assert out.exists()
    assert out.stat().st_size > 1000
    assert not (tmp_path / "smoke.aiff").exists(), "intermediate must be cleaned up"

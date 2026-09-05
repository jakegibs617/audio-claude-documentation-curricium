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


def test_voice_names_containing_spaces_are_parsed_whole():
    """macOS ships voices like "Bad News" and "Eddy (English (US))". Splitting on
    the first space invents names and rejects real ones, so the swappable-engine
    promise silently forbids a third of the installed voices."""
    from audiodocs.speak import _parse_voices

    listing = (
        "Samantha           en_US    # Hello, my name is Samantha.\n"
        "Bad News           en_US    # The light you see at the end.\n"
        "Eddy (English (US)) en_US   # Hello!\n"
    )
    assert _parse_voices(listing) == ("Samantha", "Bad News", "Eddy (English (US))")

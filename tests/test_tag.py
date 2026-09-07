import pytest
from pathlib import Path
from audiodocs.segments import Segment
from audiodocs.speak import synthesize_segments
from audiodocs.art import render_png
from audiodocs.tag import tag_audio, read_tags, TagError


def test_rejects_missing_audio(tmp_path):
    with pytest.raises(TagError, match="no such audio file"):
        tag_audio(tmp_path / "nope.m4a", "Title", 3, "Album")


@pytest.mark.smoke
def test_tags_round_trip(tmp_path):
    audio = synthesize_segments(
        [Segment("narrator", "Testing tags."),
         Segment("exercise", "Go and try it.")],
        {"narrator": "af_heart", "tradeoff": "bf_emma",
         "exercise": "am_michael"},
        165,
        tmp_path / "ep03.m4a",
    )
    art = render_png(Path("diagrams/ep03-context-window.svg"), tmp_path / "ep03.png")

    tag_audio(audio, "The context window", 3, "Claude Code, Narrated", artwork=art)
    tags = read_tags(audio)

    assert tags["title"] == "The context window"
    assert tags["track"] == 3
    assert tags["album"] == "Claude Code, Narrated"
    assert tags["has_artwork"] is True

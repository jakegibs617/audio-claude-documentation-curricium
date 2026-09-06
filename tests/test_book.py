import subprocess

import pytest

from audiodocs.book import BookError, build_audiobook, chapters_for
from audiodocs.manifest import load_curriculum
from pathlib import Path


def _silence(path: Path, seconds: float) -> Path:
    """A real, tiny AAC file -- the chapter maths depends on actual durations."""
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi",
         "-i", f"anullsrc=r=44100:cl=mono", "-t", str(seconds),
         "-c:a", "aac", "-b:a", "32k", str(path)],
        check=True, capture_output=True,
    )
    return path


@pytest.fixture
def curriculum():
    return load_curriculum(Path("curriculum.yaml"))


def test_chapters_follow_episode_order_and_accumulate(tmp_path, curriculum):
    audio = tmp_path / "audio"
    for number, secs in ((1, 2.0), (2, 3.0), (3, 1.0)):
        _silence(audio / f"{curriculum.episode(number).slug}.m4a", secs)

    chapters = chapters_for(curriculum, audio)
    assert [c.title for c in chapters] == [
        curriculum.episode(n).title for n in (1, 2, 3)
    ]
    assert chapters[0].start == 0
    assert chapters[1].start == pytest.approx(2.0, abs=0.2)
    assert chapters[2].start == pytest.approx(5.0, abs=0.3)


def test_unbuilt_episodes_are_skipped_not_faked(tmp_path, curriculum):
    """A partial course is a valid audiobook. A missing episode must not become
    a silent chapter or shift every later chapter's timestamp."""
    audio = tmp_path / "audio"
    _silence(audio / f"{curriculum.episode(1).slug}.m4a", 2.0)
    _silence(audio / f"{curriculum.episode(3).slug}.m4a", 2.0)

    chapters = chapters_for(curriculum, audio)
    assert [c.number for c in chapters] == [1, 3]
    assert chapters[1].start == pytest.approx(2.0, abs=0.2)


def test_an_empty_audio_dir_is_an_error(tmp_path, curriculum):
    (tmp_path / "audio").mkdir()
    with pytest.raises(BookError, match="no episodes"):
        build_audiobook(curriculum, tmp_path / "audio", tmp_path / "b.m4b")


@pytest.mark.smoke
def test_produces_a_playable_audiobook_with_chapters(tmp_path, curriculum):
    audio = tmp_path / "audio"
    for number in (1, 2, 3):
        _silence(audio / f"{curriculum.episode(number).slug}.m4a", 2.0)

    out = build_audiobook(curriculum, audio, tmp_path / "book.m4b")
    assert out.exists() and out.suffix == ".m4b"

    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_chapters", "-of", "csv", str(out)],
        capture_output=True, text=True,
    ).stdout
    assert probe.count("chapter") == 3
    for number in (1, 2, 3):
        assert curriculum.episode(number).title in probe

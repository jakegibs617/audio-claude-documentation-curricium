"""Write episode metadata and cover artwork into audio files."""
from __future__ import annotations

from pathlib import Path

from mutagen.mp4 import MP4, MP4Cover


class TagError(Exception):
    """Tagging failed."""


def tag_audio(
    audio_path: Path,
    title: str,
    track: int,
    album: str,
    artwork: Path | None = None,
) -> None:
    audio_path = Path(audio_path)
    if not audio_path.exists():
        raise TagError(f"no such audio file: {audio_path}")

    try:
        audio = MP4(str(audio_path))
    except Exception as exc:
        raise TagError(f"could not open {audio_path}: {exc}") from exc

    audio["\xa9nam"] = [title]
    audio["\xa9alb"] = [album]
    audio["trkn"] = [(track, 0)]

    if artwork is not None:
        artwork = Path(artwork)
        if not artwork.exists():
            raise TagError(f"no such artwork: {artwork}")
        audio["covr"] = [
            MP4Cover(artwork.read_bytes(), imageformat=MP4Cover.FORMAT_PNG)
        ]

    audio.save()


def read_tags(audio_path: Path) -> dict:
    audio = MP4(str(Path(audio_path)))
    return {
        "title": (audio.get("\xa9nam") or [None])[0],
        "album": (audio.get("\xa9alb") or [None])[0],
        "track": (audio.get("trkn") or [(None, 0)])[0][0],
        "has_artwork": bool(audio.get("covr")),
    }

"""Assemble the built episodes into one chaptered audiobook.

A course is listened to in order over weeks, which is what the audiobook format
is actually for: one file that remembers where you stopped, with a chapter list
that doubles as the curriculum. Forty-three separate tracks lose that -- each
one remembers its own position, and none of them remembers the course.

The episode audio is copied, never re-encoded: it is already AAC at the right
rate, and a second encode would cost quality for nothing.
"""
from __future__ import annotations

import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .manifest import Curriculum


class BookError(Exception):
    """The audiobook could not be assembled."""


@dataclass(frozen=True)
class Chapter:
    number: int
    title: str
    start: float
    duration: float
    path: Path


def _duration(path: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise BookError(f"could not read duration of {path.name}")
    try:
        return float(result.stdout.strip())
    except ValueError as exc:
        raise BookError(f"unreadable duration for {path.name}") from exc


def chapters_for(curriculum: Curriculum, audio_dir: Path) -> list[Chapter]:
    """One chapter per built episode, in episode order, with cumulative starts.

    An episode that has not been built is skipped rather than represented as
    silence: a partial course is a valid audiobook, and a placeholder chapter
    would shift every later timestamp out of sync with its audio.
    """
    audio_dir = Path(audio_dir)
    chapters: list[Chapter] = []
    cursor = 0.0
    for episode in sorted(curriculum.episodes, key=lambda e: e.number):
        path = audio_dir / f"{episode.slug}.m4a"
        if not path.exists():
            continue
        seconds = _duration(path)
        chapters.append(
            Chapter(episode.number, episode.title, cursor, seconds, path)
        )
        cursor += seconds
    return chapters


def _metadata(curriculum: Curriculum, chapters: list[Chapter]) -> str:
    lines = [
        ";FFMETADATA1",
        f"title={curriculum.album}",
        f"album={curriculum.album}",
        "artist=Claude Code, Narrated",
        "genre=Audiobook",
    ]
    for chapter in chapters:
        # Milliseconds: the timebase below is 1/1000.
        start = int(round(chapter.start * 1000))
        end = int(round((chapter.start + chapter.duration) * 1000))
        lines += [
            "[CHAPTER]",
            "TIMEBASE=1/1000",
            f"START={start}",
            f"END={end}",
            f"title={chapter.number:02d}. {chapter.title}",
        ]
    return "\n".join(lines) + "\n"


def build_audiobook(
    curriculum: Curriculum,
    audio_dir: Path,
    out_path: Path,
    cover: Path | None = None,
) -> Path:
    """Join every built episode into a single chaptered .m4b."""
    chapters = chapters_for(curriculum, audio_dir)
    if not chapters:
        raise BookError(f"no episodes built in {audio_dir}")

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        listing = tmp / "files.txt"
        listing.write_text(
            "".join(f"file '{c.path.resolve()}'\n" for c in chapters)
        )
        meta = tmp / "meta.txt"
        meta.write_text(_metadata(curriculum, chapters))

        use_cover = bool(cover) and Path(cover).exists()
        result = _run(listing, meta, out_path, cover if use_cover else None)

        if result.returncode != 0 and use_cover:
            # Artwork degrades; audio does not. An unreadable cover should cost
            # the picture, not six hours of narration.
            print(
                f"warning: cover rejected, building without it: "
                f"{result.stderr.strip()[:200]}"
            )
            result = _run(listing, meta, out_path, None)

    if result.returncode != 0 or not out_path.exists():
        raise BookError(f"ffmpeg failed: {result.stderr.strip()[:400]}")
    return out_path


def _run(listing: Path, meta: Path, out_path: Path, cover: Path | None):
    command = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "concat", "-safe", "0", "-i", str(listing),
        "-i", str(meta),
    ]
    if cover:
        command += ["-i", str(cover)]
    command += ["-map_metadata", "1", "-map_chapters", "1", "-map", "0:a"]
    if cover:
        command += ["-map", "2:v", "-c:v", "copy",
                    "-disposition:v", "attached_pic"]
    command += ["-c:a", "copy", str(out_path)]
    return subprocess.run(command, capture_output=True, text=True, timeout=1800)

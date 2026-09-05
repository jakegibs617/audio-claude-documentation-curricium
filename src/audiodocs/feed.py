"""Generate a podcast RSS feed for the episodes that have been built so far.

A partial course is a valid feed: episodes without audio yet are skipped
silently rather than failing the build, so the feed can be regenerated at
any point in the course.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from pathlib import Path
from urllib.parse import quote

from mutagen.mp4 import MP4

from .manifest import Curriculum, Episode

ITUNES_NS = "http://www.itunes.com/dtds/podcast-1.0.dtd"

# Podcast apps order episodes by pubDate, not by itunes:episode, so a sequenced
# course needs increasing dates or it arrives shuffled. Derived from the episode
# number rather than the clock: a feed that changes on every rebuild re-notifies
# subscribers about episodes they already have.
EPOCH = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
ET.register_namespace("itunes", ITUNES_NS)


class FeedError(Exception):
    """The feed could not be built."""


def _itunes(tag: str) -> str:
    return f"{{{ITUNES_NS}}}{tag}"


def _join_url(base_url: str, filename: str) -> str:
    if not base_url.endswith("/"):
        base_url = base_url + "/"
    return base_url + quote(filename)


def _pub_date(number: int) -> str:
    return format_datetime(EPOCH + timedelta(days=number))


def _duration_text(audio_path: Path) -> str | None:
    """Best-effort human duration ("M:SS" or "H:MM:SS") for itunes:duration.

    Returns None if the file can't be read as audio — callers should omit
    the element rather than fail the whole feed over one bad file.
    """
    try:
        seconds = int(round(MP4(str(audio_path)).info.length))
    except Exception:
        return None

    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def _built_episodes(curriculum: Curriculum, audio_dir: Path) -> list[tuple[Episode, Path]]:
    found = []
    for episode in curriculum.episodes:
        audio_path = audio_dir / f"{episode.slug}.m4a"
        if audio_path.exists():
            found.append((episode, audio_path))
    found.sort(key=lambda pair: pair[0].number)
    return found


def build_feed(curriculum: Curriculum, audio_dir: Path, out_path: Path, base_url: str) -> Path:
    audio_dir = Path(audio_dir)
    out_path = Path(out_path)

    if not audio_dir.exists():
        raise FeedError(f"no such audio directory: {audio_dir}")

    rss = ET.Element("rss", {"version": "2.0"})
    channel = ET.SubElement(rss, "channel")
    # title, link and description are required by RSS 2.0; strict readers
    # reject a feed without all three.
    ET.SubElement(channel, "title").text = curriculum.album
    ET.SubElement(channel, "link").text = base_url
    ET.SubElement(channel, "description").text = (
        f"{curriculum.album}: the Claude Code documentation, rewritten to be "
        "heard and sequenced as a course."
    )
    ET.SubElement(channel, "language").text = "en-us"
    ET.SubElement(channel, _itunes("author")).text = "Claude Code, Narrated"
    ET.SubElement(channel, _itunes("explicit")).text = "false"
    ET.SubElement(channel, _itunes("summary")).text = (
        "One narrated episode per topic, in the order that builds understanding "
        "rather than the order the sidebar happens to use."
    )

    for episode, audio_path in _built_episodes(curriculum, audio_dir):
        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = episode.title
        ET.SubElement(item, _itunes("episode")).text = str(episode.number)
        ET.SubElement(item, "pubDate").text = _pub_date(episode.number)
        ET.SubElement(item, "description").text = (
            f"{episode.title}. Exercise: {episode.exercise}"
        )
        ET.SubElement(item, "guid", {"isPermaLink": "false"}).text = episode.slug
        ET.SubElement(
            item,
            "enclosure",
            {
                "url": _join_url(base_url, audio_path.name),
                "length": str(audio_path.stat().st_size),
                "type": "audio/mp4",
            },
        )

        duration = _duration_text(audio_path)
        if duration is not None:
            ET.SubElement(item, _itunes("duration")).text = duration

    out_path.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(rss).write(out_path, encoding="UTF-8", xml_declaration=True)
    return out_path

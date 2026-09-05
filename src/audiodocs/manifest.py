"""Parse and validate the episode manifest."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


class ManifestError(Exception):
    """The curriculum file is malformed."""


@dataclass(frozen=True)
class Episode:
    number: int
    title: str
    sources: list[str]
    exercise: str
    diagram: str | None = None

    @property
    def slug(self) -> str:
        """Filesystem-safe stem, e.g. '03-the-context-window'."""
        safe = "".join(c if c.isalnum() else "-" for c in self.title.lower())
        while "--" in safe:
            safe = safe.replace("--", "-")
        return f"{self.number:02d}-{safe.strip('-')}"


@dataclass(frozen=True)
class Curriculum:
    album: str
    voice: str
    episodes: list[Episode]

    def episode(self, number: int) -> Episode:
        for ep in self.episodes:
            if ep.number == number:
                return ep
        raise ManifestError(f"no episode numbered {number}")


REQUIRED = ("number", "title", "sources", "exercise")


def load_curriculum(path: Path) -> Curriculum:
    data = yaml.safe_load(Path(path).read_text())
    if not isinstance(data, dict):
        raise ManifestError("curriculum must be a mapping")

    episodes: list[Episode] = []
    seen: set[int] = set()

    for raw in data.get("episodes") or []:
        number = raw.get("number")
        for field in REQUIRED:
            if field not in raw:
                raise ManifestError(f"episode {number} missing required field: {field}")
        if not raw["sources"]:
            raise ManifestError(f"episode {number} has no sources")
        if number in seen:
            raise ManifestError(f"duplicate episode number: {number}")
        seen.add(number)
        episodes.append(
            Episode(
                number=number,
                title=raw["title"],
                sources=list(raw["sources"]),
                exercise=raw["exercise"],
                diagram=raw.get("diagram"),
            )
        )

    return Curriculum(
        album=data.get("album", "Claude Code, Narrated"),
        voice=data.get("voice", "Samantha"),
        episodes=episodes,
    )

"""Parse and validate the episode manifest."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from .sanitize import find_violations
from .segments import ROLES


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
    cast: dict[str, str]
    pace: int
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
        if not isinstance(raw, dict):
            raise ManifestError(f"episode entry is not a mapping: {raw!r}")
        number = raw.get("number")
        for field in REQUIRED:
            if field not in raw:
                raise ManifestError(f"episode {number} missing required field: {field}")
        if not isinstance(number, int):
            raise ManifestError(f"episode number must be a whole number, got {number!r}")
        # A bare string is iterable, so `sources: context-window` would silently
        # become one slug per character and fetch 14 nonexistent pages.
        if isinstance(raw["sources"], str):
            raise ManifestError(
                f"episode {number}: sources must be a list, got the string "
                f"{raw['sources']!r} -- did you forget the brackets?"
            )
        if not raw["sources"]:
            raise ManifestError(f"episode {number} has no sources")
        if number in seen:
            raise ManifestError(f"duplicate episode number: {number}")
        # The exercise is interpolated into the narration prompt and the model is
        # told to close on it. An unspeakable exercise asks for a rejection that
        # only surfaces after a paid model call.
        violations = find_violations(raw["exercise"])
        if violations:
            raise ManifestError(
                f"episode {number}: exercise is not speakable: {violations[0]}"
            )
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

    cast = data.get("cast") or {}
    if not isinstance(cast, dict):
        raise ManifestError("cast must be a mapping of role to voice")
    for role in cast:
        if role not in ROLES:
            raise ManifestError(
                f"unknown cast role {role!r}; expected one of {', '.join(ROLES)}"
            )
    # Every role needs a voice before the build starts. A script may label any
    # of them, and discovering a gap partway through episode 9 costs the run.
    for role in ROLES:
        if not cast.get(role):
            raise ManifestError(f"cast is missing a voice for the {role!r} role")

    return Curriculum(
        album=data.get("album", "Claude Code, Narrated"),
        cast=cast,
        pace=int(data.get("pace", 165)),
        episodes=episodes,
    )

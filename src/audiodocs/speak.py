"""Text to speech.

The only module permitted to invoke a speech engine. Swapping macOS `say` for a
paid API means replacing `_synthesize_aiff` and nothing else.
"""
from __future__ import annotations

import re
import subprocess
from functools import lru_cache
from pathlib import Path


class SpeakError(Exception):
    """Speech synthesis failed."""


# "<name>  <locale>  # <sample>" -- the locale is the only dependable column.
VOICE_LINE = re.compile(r"^(.+?)\s+[a-z]{2,3}[_-][A-Za-z0-9]{2,3}\s")


def _parse_voices(listing: str) -> tuple[str, ...]:
    """Voice names from `say -v \'?\'` output.

    Names contain spaces and parentheses ("Bad News", "Eddy (English (US))"),
    and the column gap before the locale can be a single space, so neither
    `split()` nor a two-space column split works. The locale token is the only
    reliable anchor: the name is everything before it.
    """
    names = []
    for line in listing.splitlines():
        match = VOICE_LINE.match(line)
        if match:
            names.append(match.group(1).strip())
    return tuple(names)


@lru_cache(maxsize=1)
def available_voices() -> tuple[str, ...]:
    result = subprocess.run(["say", "-v", "?"], capture_output=True, text=True)
    if result.returncode != 0:
        raise SpeakError("could not list voices")
    return _parse_voices(result.stdout)


def _synthesize_aiff(text: str, aiff: Path, voice: str) -> None:
    result = subprocess.run(
        ["say", "-v", voice, "-o", str(aiff), text],
        capture_output=True,
        text=True,
        timeout=1800,
    )
    if result.returncode != 0:
        raise SpeakError(f"say failed: {result.stderr.strip()}")


def _to_m4a(aiff: Path, m4a: Path) -> None:
    result = subprocess.run(
        ["afconvert", "-f", "m4af", "-d", "aac", "-b", "64000", str(aiff), str(m4a)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise SpeakError(f"afconvert failed: {result.stderr.strip()}")


def synthesize(text: str, out_path: Path, voice: str = "Samantha") -> Path:
    """Render `text` to an audio file at `out_path`."""
    if not text.strip():
        raise SpeakError("refusing to synthesize empty text")
    if voice not in available_voices():
        raise SpeakError(
            f"voice not installed: {voice}. "
            f"Install it in System Settings, Accessibility, Spoken Content."
        )

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    aiff = out_path.with_suffix(".aiff")

    try:
        _synthesize_aiff(text, aiff, voice)
        _to_m4a(aiff, out_path)
    finally:
        aiff.unlink(missing_ok=True)

    return out_path

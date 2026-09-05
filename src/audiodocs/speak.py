"""Text to speech.

The only module permitted to invoke a speech engine. Swapping macOS `say` for a
paid API means replacing `_synthesize_aiff` and nothing else.
"""
from __future__ import annotations

import subprocess
from functools import lru_cache
from pathlib import Path


class SpeakError(Exception):
    """Speech synthesis failed."""


@lru_cache(maxsize=1)
def available_voices() -> tuple[str, ...]:
    result = subprocess.run(["say", "-v", "?"], capture_output=True, text=True)
    if result.returncode != 0:
        raise SpeakError("could not list voices")
    return tuple(line.split()[0] for line in result.stdout.splitlines() if line.strip())


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

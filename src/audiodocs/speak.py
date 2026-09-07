"""Turn role-labelled segments into a single audio file.

The only module permitted to invoke a speech engine. Everything above it deals
in text and roles; swapping vendors is a change to this file alone.

The engine is Kokoro (Apache-2.0, runs locally). It is imported lazily so the
test suite -- which injects a stand-in engine -- never loads a 350MB model.
"""
from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

from .segments import Segment

# Measured at speed 1.0 on a 222-word passage of real episode narration.
# Calibrating on a short clip gives numbers 15-20% too high: most of the
# difference is sentence-boundary pauses, which a two-sentence sample never
# exercises and which scale with the text. Kokoro's speed parameter scales
# duration, so the factor to hit a target pace is target / natural.
NATURAL_WPM = {
    "af_heart": 182,
    "af_bella": 179,
    "bf_emma": 195,
    "am_michael": 169,
    "am_fenrir": 219,
}

SAMPLE_RATE = 24000
# A beat between speakers. Butt-joining two voices sounds like a splice; this
# reads as a deliberate handover.
GAP_SECONDS = 0.65

# espeakng-loader ships a path from its own build machine, which does not exist
# here. Point it at the Homebrew install instead.
ESPEAK_DATA = "/opt/homebrew/share/espeak-ng-data"
ESPEAK_LIB = "/opt/homebrew/lib/libespeak-ng.dylib"


class SpeakError(Exception):
    """Audio could not be synthesized."""


def speed_for(voice: str, pace: int) -> float:
    """The engine speed that makes `voice` speak at roughly `pace` words/minute.

    Clamped: a pace far from a voice's natural rate destroys it, and shipping
    43 episodes of chipmunk is worse than refusing the extreme.
    """
    natural = NATURAL_WPM.get(voice)
    if natural is None:
        raise SpeakError(f"{voice!r} is not a known voice")
    return max(0.5, min(2.0, pace / natural))


def _kokoro_engine():
    """Build the real engine. Imported here so tests never pay for it."""
    os.environ.setdefault("ESPEAK_DATA_PATH", ESPEAK_DATA)
    os.environ.setdefault("PHONEMIZER_ESPEAK_LIBRARY", ESPEAK_LIB)
    try:
        import espeakng_loader

        if Path(ESPEAK_DATA).exists():
            espeakng_loader.get_data_path = lambda: ESPEAK_DATA
            espeakng_loader.get_library_path = lambda: ESPEAK_LIB
        import numpy as np
        from kokoro import KPipeline
    except ImportError as exc:  # pragma: no cover - environment problem
        raise SpeakError(
            f"the speech engine is not installed: {exc}. "
            "Install with: uv pip install kokoro soundfile "
            "&& brew install espeak-ng"
        ) from exc

    pipeline = KPipeline(lang_code="a")

    def engine(text: str, voice: str, speed: float):
        chunks = [c.audio.numpy() for c in pipeline(text, voice=voice, speed=speed)]
        if not chunks:
            raise SpeakError(f"engine returned no audio for {voice!r}")
        return np.concatenate(chunks)

    return engine


def synthesize_segments(
    segments: list[Segment],
    cast: dict[str, str],
    pace: int,
    out_path: Path,
    engine=None,
) -> Path:
    """Speak each segment in its role's voice and join them into one file."""
    import numpy as np

    if not segments:
        raise SpeakError("nothing to speak: segment list is empty")

    # Validate the whole cast before synthesizing anything. Discovering a bad
    # voice on the last segment wastes every segment before it.
    for segment in segments:
        voice = cast.get(segment.role)
        if voice is None:
            raise SpeakError(f"no voice cast for the {segment.role!r} role")
        speed_for(voice, pace)

    engine = engine or _kokoro_engine()
    gap = np.zeros(int(SAMPLE_RATE * GAP_SECONDS), dtype="float32")

    pieces = []
    for index, segment in enumerate(segments):
        voice = cast[segment.role]
        audio = engine(segment.text, voice, speed_for(voice, pace))
        pieces.append(np.asarray(audio, dtype="float32"))
        if index < len(segments) - 1:
            pieces.append(gap)

    return _write(np.concatenate(pieces), out_path)


def _write(audio, out_path: Path) -> Path:
    """Write float samples out as AAC in an MP4 container.

    afconvert refuses 24 kHz float input, so the intermediate is 16-bit PCM and
    the encoder is told to resample to 44.1 kHz.
    """
    import soundfile as sf

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        wav = Path(tmp) / "raw.wav"
        sf.write(wav, audio, SAMPLE_RATE, subtype="PCM_16")
        result = subprocess.run(
            ["afconvert", "-f", "m4af", "-d", "aac@44100", "-b", "64000",
             str(wav), str(out_path)],
            capture_output=True, text=True, timeout=600,
        )
    if result.returncode != 0 or not out_path.exists():
        raise SpeakError(f"afconvert failed: {result.stderr.strip()[:300]}")
    return out_path

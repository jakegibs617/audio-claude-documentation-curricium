"""Rewrite reference documentation into spoken-word narration."""
from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

from .manifest import Episode
from .sanitize import UnspeakableError, assert_speakable
from .segments import SegmentError, parse_segments, spoken_text


NARRATION_PROMPT = """\
You are writing a script to be read aloud as one episode of an audio course \
about Claude Code. The listener is walking or driving. They cannot see anything.

Episode title: {title}
Closing exercise: {exercise}

Rewrite the documentation piped to you as spoken narration.

Rules, all mandatory:
- Write continuous spoken prose. No headings, no bullets, no markdown of any kind.
- Never include a code block. Describe code in words instead: say "a hooks block \
keyed by event name, each holding a matcher and a command" rather than showing JSON.
- Never include a URL, and never write a command flag as a dash followed by a word. \
Name flags in words: "the print flag", "the resume flag".
- Never write a table. Turn comparisons into sentences.
- Never refer to anything "above", "below", or "shown" - the listener sees nothing.
- {continuity}
- Explain the mental model and the trade-offs, not the syntax.
- Close by stating the exercise as something to go and do.
- Target between 1200 and 1800 words.

Structure. Different voices read different parts, so label every block by starting a line with one of these, followed by a colon:

NARRATOR: the explanation. Most of the episode is this.
TRADEOFF: the cost, limit, or catch -- what this thing takes away, or when it is the wrong choice. Use it once or twice, only where there is a real trade-off to name. Do not force one.
EXERCISE: the closing call to action. Exactly one, and it must be last.

The labels are stage directions and are never read aloud, so do not refer to them and do not write anything else in capitals followed by a colon.

Output only the script. No preamble, no commentary.
"""


class ScriptError(Exception):
    """A narration script could not be produced."""


def _default_runner(prompt: str, stdin: str) -> str:
    result = subprocess.run(
        ["claude", "-p", prompt],
        input=stdin,
        capture_output=True,
        text=True,
        timeout=900,
    )
    if result.returncode != 0:
        raise ScriptError(f"claude -p failed: {result.stderr.strip()}")
    return result.stdout.strip()


FIRST_EPISODE_OPENING = (
    "This is the first episode, so open cold. Do not say \"last time\" or refer "
    "to any previous episode -- there isn't one."
)


def _continuity(previous_title: str | None) -> str:
    """What to say in the opening line.

    Told to connect to the previous episode without being told which one it was,
    the model invents a plausible-sounding one. Naming it is the whole fix.
    """
    if previous_title is None:
        return FIRST_EPISODE_OPENING
    return (
        f"Open with one sentence connecting back to the previous episode, which "
        f"was titled \"{previous_title}\". Refer to its actual subject; do not "
        f"invent a different one."
    )


def _cache_key(episode: Episode, sources_text: str, previous_title: str | None) -> str:
    digest = hashlib.sha256()
    # Hash the prompt itself, not a hand-maintained version string: editing the
    # prompt is the documented fix for bad narration and must actually rebuild.
    # The sanitizer's rules join it -- a script cached under looser rules would
    # otherwise stay key-valid but content-rejected, wedging the episode.
    # Fields are delimited so title "AB" + exercise "C" cannot collide with
    # title "A" + exercise "BC".
    for field in (
        NARRATION_PROMPT,
        sanitize_fingerprint(),
        episode.title,
        episode.exercise,
        previous_title or "",
        sources_text,
    ):
        digest.update(field.encode())
        digest.update(b"\x00")
    return digest.hexdigest()[:16]


def sanitize_fingerprint() -> str:
    """Read through the module so tests can monkeypatch the rules."""
    from . import sanitize

    return sanitize.RULES_FINGERPRINT


def _reject_unspeakable(script: str, episode: Episode, cache_dir: Path) -> None:  # noqa: D401
    """Raise if `script` cannot be spoken, keeping the text for inspection.

    A rejection has already cost a model call. Discarding the script would cost
    another just to see what was wrong with it.
    """
    try:
        # Check what is actually heard. The role labels are stage directions,
        # stripped before synthesis, so they are not the sanitizer's business --
        # but a malformed script is, and parse_segments raises on one.
        assert_speakable(spoken_text(parse_segments(script)))
    except (UnspeakableError, SegmentError) as exc:
        cache_dir.mkdir(parents=True, exist_ok=True)
        rejected = cache_dir / f"{episode.slug}.rejected.txt"
        rejected.write_text(script)
        raise ScriptError(
            f"episode {episode.number}: {exc}\nrejected script kept at {rejected}"
        ) from exc


def build_script(
    episode: Episode,
    sources_text: str,
    cache_dir: Path,
    runner=None,
    previous_title: str | None = None,
) -> str:
    """Return narration for `episode`, calling the model only on a cache miss."""
    cache_dir = Path(cache_dir)
    key = _cache_key(episode, sources_text, previous_title)
    cached = cache_dir / f"{episode.slug}-{key}.txt"

    if cached.exists():
        # Re-check on the cache-hit path too. The sanitizer will get stricter;
        # scripts written under a looser one must not stay permanently exempt.
        script = cached.read_text()
        _reject_unspeakable(script, episode, cache_dir)
        return script

    prompt = NARRATION_PROMPT.format(
        title=episode.title,
        exercise=episode.exercise,
        continuity=_continuity(previous_title),
    )
    script = (runner or _default_runner)(prompt, sources_text)

    if not script.strip():
        raise ScriptError(f"episode {episode.number}: model returned nothing")

    _reject_unspeakable(script, episode, cache_dir)

    cached.parent.mkdir(parents=True, exist_ok=True)
    cached.write_text(script)
    return script

"""Rewrite reference documentation into spoken-word narration."""
from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

from .manifest import Episode
from .sanitize import UnspeakableError, assert_speakable


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
- Open with one sentence connecting to the previous episode's idea.
- Explain the mental model and the trade-offs, not the syntax.
- Close by stating the exercise as something to go and do.
- Target between 1200 and 1800 words.

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


def _cache_key(episode: Episode, sources_text: str) -> str:
    digest = hashlib.sha256()
    # Hash the prompt itself, not a hand-maintained version string: editing the
    # prompt is the documented fix for bad narration and must actually rebuild.
    digest.update(NARRATION_PROMPT.encode())
    digest.update(episode.title.encode())
    digest.update(episode.exercise.encode())
    digest.update(sources_text.encode())
    return digest.hexdigest()[:16]


def _reject_unspeakable(script: str, episode: Episode, cache_dir: Path) -> None:
    """Raise if `script` cannot be spoken, keeping the text for inspection.

    A rejection has already cost a model call. Discarding the script would cost
    another just to see what was wrong with it.
    """
    try:
        assert_speakable(script)
    except UnspeakableError as exc:
        cache_dir.mkdir(parents=True, exist_ok=True)
        rejected = cache_dir / f"{episode.slug}.rejected.txt"
        rejected.write_text(script)
        raise ScriptError(
            f"episode {episode.number}: {exc}\nrejected script kept at {rejected}"
        ) from exc


def build_script(
    episode: Episode, sources_text: str, cache_dir: Path, runner=None
) -> str:
    """Return narration for `episode`, calling the model only on a cache miss."""
    cache_dir = Path(cache_dir)
    cached = cache_dir / f"{episode.slug}-{_cache_key(episode, sources_text)}.txt"

    if cached.exists():
        # Re-check on the cache-hit path too. The sanitizer will get stricter;
        # scripts written under a looser one must not stay permanently exempt.
        script = cached.read_text()
        _reject_unspeakable(script, episode, cache_dir)
        return script

    prompt = NARRATION_PROMPT.format(title=episode.title, exercise=episode.exercise)
    script = (runner or _default_runner)(prompt, sources_text)

    if not script.strip():
        raise ScriptError(f"episode {episode.number}: model returned nothing")

    _reject_unspeakable(script, episode, cache_dir)

    cached.parent.mkdir(parents=True, exist_ok=True)
    cached.write_text(script)
    return script

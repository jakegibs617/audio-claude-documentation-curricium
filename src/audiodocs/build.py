"""Orchestrate the episode pipeline. The only module that knows stage order."""
from __future__ import annotations

import argparse
import hashlib
import sys
from dataclasses import dataclass
from pathlib import Path

from .art import render_png
from .feed import FeedError, build_feed
from .fetch import fetch_doc
from .manifest import Curriculum, Episode, ManifestError, load_curriculum
from .script import build_script
from .speak import SpeakError, available_voices, synthesize
from .tag import tag_audio

DIAGRAMS = Path("diagrams")


def _stamp_path(episode: Episode, out_dir: Path) -> Path:
    """Records what produced the current audio, so staleness is detectable."""
    return Path(out_dir) / "audio" / f"{episode.slug}.stamp"


def _diagram_fingerprint(episode: Episode) -> str:
    """Identify the SVG an episode embeds, so editing it rebuilds the episode."""
    if not episode.diagram:
        return ""
    svg = DIAGRAMS / f"{episode.diagram}.svg"
    if not svg.exists():
        return "missing"
    return hashlib.sha256(svg.read_bytes()).hexdigest()


def _stamp(script: str, curriculum: Curriculum, episode: Episode) -> str:
    """Everything baked into the finished file.

    Not just the script: the voice speaks it, the album is tagged into it, and
    the diagram is embedded in it. Anything left out of this goes stale silently.
    """
    digest = hashlib.sha256()
    for field in (
        script, curriculum.voice, curriculum.album, _diagram_fingerprint(episode)
    ):
        digest.update(field.encode())
        digest.update(b"\x00")
    return digest.hexdigest()


def _build_one(
    episode: Episode, curriculum: Curriculum, out_dir: Path
) -> tuple[Path, bool]:
    """Build `episode`, returning its audio path and whether it was already current.

    The expensive stages (fetch, model call) are disk-cached and cheap on a hit,
    so they run every time; only synthesis and tagging are skipped. That is what
    makes staleness detectable at all: the audio is compared against the script
    that would produce it now, not merely checked for existence.
    """
    out_dir = Path(out_dir)
    cache = out_dir / "cache"

    sources_text = "\n\n---\n\n".join(
        fetch_doc(slug, cache / "docs") for slug in episode.sources
    )
    script = build_script(episode, sources_text, cache / "scripts")

    audio_path = out_dir / "audio" / f"{episode.slug}.m4a"
    stamp_path = _stamp_path(episode, out_dir)
    stamp = _stamp(script, curriculum, episode)
    if audio_path.exists() and stamp_path.exists() and stamp_path.read_text() == stamp:
        return audio_path, True

    audio = synthesize(
        script, out_dir / "audio" / f"{episode.slug}.m4a", voice=curriculum.voice
    )

    artwork = None
    if episode.diagram:
        try:
            artwork = render_png(
                DIAGRAMS / f"{episode.diagram}.svg",
                out_dir / "art" / f"{episode.diagram}.png",
            )
        except Exception as exc:  # noqa: BLE001 - artwork never fails the audio
            # Audio is the primary deliverable; artwork degrades rather than
            # fails. Chrome can hang (TimeoutExpired), be missing
            # (FileNotFoundError), or fail to move its output (OSError) -- none
            # of which are ArtError, and all of which used to abort the run.
            print(
                f"warning: artwork skipped for episode {episode.number}: {exc}",
                file=sys.stderr,
            )

    tag_audio(audio, episode.title, episode.number, curriculum.album, artwork=artwork)
    stamp_path.write_text(stamp)
    return audio, False


def build_episode(episode: Episode, curriculum: Curriculum, out_dir: Path) -> Path:
    """Build one episode and return its audio path."""
    audio, _ = _build_one(episode, curriculum, out_dir)
    return audio


def _audio_path(episode: Episode, out_dir: Path) -> Path:
    """Where `build_episode` leaves the finished, tagged audio for `episode`.

    Audio does not degrade (see INTENT.md, "Regenerable, not precious"), so
    the presence of this file is treated as proof the episode is done.
    """
    return Path(out_dir) / "audio" / f"{episode.slug}.m4a"


@dataclass
class EpisodeResult:
    """The outcome of trying to build one episode as part of a batch."""

    number: int
    title: str
    status: str  # "built" | "cached" | "failed"
    path: Path | None
    error: str | None


@dataclass
class BuildReport:
    """The outcome of a `build_all` run, across every episode attempted."""

    results: list[EpisodeResult]

    @property
    def built(self) -> list[EpisodeResult]:
        return [r for r in self.results if r.status == "built"]

    @property
    def cached(self) -> list[EpisodeResult]:
        return [r for r in self.results if r.status == "cached"]

    @property
    def failed(self) -> list[EpisodeResult]:
        return [r for r in self.results if r.status == "failed"]

    @property
    def ok(self) -> bool:
        return not self.failed


def build_all(
    curriculum: Curriculum, out_dir: Path, only: list[int] | None = None
) -> BuildReport:
    """Build every episode in `curriculum` (or just `only`, if given).

    One episode failing must never abort the batch: each episode's exceptions
    are caught and recorded, and the loop moves on. An episode whose audio
    already exists on disk is reported "cached" rather than resynthesized.
    """
    out_dir = Path(out_dir)
    episodes = (
        list(curriculum.episodes)
        if only is None
        else [curriculum.episode(number) for number in only]
    )

    results: list[EpisodeResult] = []
    for index, episode in enumerate(episodes, start=1):
        # A 43-episode build is roughly an hour of model calls and TTS. Say what
        # is happening as it happens: a silent terminal is indistinguishable
        # from a hang.
        print(
            f"[{index}/{len(episodes)}] episode {episode.number}: {episode.title}",
            file=sys.stderr,
            flush=True,
        )
        try:
            path, was_cached = _build_one(episode, curriculum, out_dir)
        except Exception as exc:  # noqa: BLE001 - isolate this episode's failure
            # Say it now. A summary an hour from now cannot tell you that the
            # run started failing on episode 2.
            print(f"    FAILED episode {episode.number}: {exc}", file=sys.stderr,
                  flush=True)
            # A half-written file is not a deliverable and must not reach the
            # feed, which lists whatever audio it finds.
            audio_path = out_dir / "audio" / f"{episode.slug}.m4a"
            audio_path.unlink(missing_ok=True)
            _stamp_path(episode, out_dir).unlink(missing_ok=True)
            results.append(
                EpisodeResult(
                    number=episode.number,
                    title=episode.title,
                    status="failed",
                    path=None,
                    error=str(exc),
                )
            )
            continue

        results.append(
            EpisodeResult(
                number=episode.number,
                title=episode.title,
                status="cached" if was_cached else "built",
                path=path,
                error=None,
            )
        )

    return BuildReport(results)


def format_report(report: BuildReport) -> str:
    """A human-readable summary of a batch build, failures unmissable."""
    lines = [
        f"Built {len(report.built)}, cached {len(report.cached)}, "
        f"failed {len(report.failed)} (of {len(report.results)} episodes)"
    ]

    for result in report.results:
        if result.status == "built":
            lines.append(f"  built   {result.number:>2}: {result.title}")
        elif result.status == "cached":
            lines.append(f"  cached  {result.number:>2}: {result.title}")

    if report.failed:
        lines.append("")
        lines.append(f"*** {len(report.failed)} EPISODE(S) FAILED ***")
        for result in report.failed:
            lines.append(f"  FAILED  {result.number:>2}: {result.title} - {result.error}")

    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build audio course episodes.")
    parser.add_argument("--curriculum", type=Path, default=Path("curriculum.yaml"))
    parser.add_argument("--out", type=Path, default=Path("out"))
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000/audio/",
        help="Where the audio files will be reachable over HTTP. Podcast apps "
        "cannot load a file:// feed, so this must be an http(s) URL to work "
        "on a phone.",
    )
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument(
        "--episode",
        type=int,
        action="append",
        dest="episode",
        help="Episode number to build. May be repeated.",
    )
    selection.add_argument(
        "--all", action="store_true", help="Build every episode in the curriculum."
    )
    args = parser.parse_args(argv)

    curriculum = load_curriculum(args.curriculum)
    only = None if args.all else args.episode

    # Check the voice before spending anything. It is used at the last stage of
    # every episode, so without this one typo burns every model call in the run.
    try:
        if curriculum.voice not in available_voices():
            print(
                f"error: voice {curriculum.voice!r} is not installed. "
                f"Run `say -v '?'` to see what is.",
                file=sys.stderr,
            )
            return 1
    except SpeakError as exc:
        print(f"error: could not list voices: {exc}", file=sys.stderr)
        return 1

    try:
        report = build_all(curriculum, args.out, only=only)
    except ManifestError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(format_report(report))

    # The feed lists whatever audio exists, so it is worth regenerating even
    # after a partial build -- but it must never mask a build failure.
    try:
        feed = build_feed(
            curriculum, args.out / "audio", args.out / "feed.xml", args.base_url
        )
        print(f"feed: {feed}")
    except FeedError as exc:
        print(f"warning: feed not written: {exc}", file=sys.stderr)

    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

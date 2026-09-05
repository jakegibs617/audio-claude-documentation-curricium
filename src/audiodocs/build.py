"""Orchestrate the episode pipeline. The only module that knows stage order."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .art import ArtError, render_png
from .fetch import fetch_doc
from .manifest import Curriculum, Episode, load_curriculum
from .script import build_script
from .speak import synthesize
from .tag import tag_audio

DIAGRAMS = Path("diagrams")


def build_episode(episode: Episode, curriculum: Curriculum, out_dir: Path) -> Path:
    out_dir = Path(out_dir)
    cache = out_dir / "cache"

    sources_text = "\n\n---\n\n".join(
        fetch_doc(slug, cache / "docs") for slug in episode.sources
    )
    script = build_script(episode, sources_text, cache / "scripts")

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
        except ArtError as exc:
            # Audio is the primary deliverable; artwork degrades rather than fails.
            print(
                f"warning: artwork skipped for episode {episode.number}: {exc}",
                file=sys.stderr,
            )

    tag_audio(audio, episode.title, episode.number, curriculum.album, artwork=artwork)
    return audio


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build audio course episodes.")
    parser.add_argument("--curriculum", type=Path, default=Path("curriculum.yaml"))
    parser.add_argument("--out", type=Path, default=Path("out"))
    parser.add_argument("--episode", type=int, required=True)
    args = parser.parse_args(argv)

    curriculum = load_curriculum(args.curriculum)
    episode = curriculum.episode(args.episode)

    print(f"Building episode {episode.number}: {episode.title}")
    path = build_episode(episode, curriculum, args.out)
    print(f"Wrote {path} ({path.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

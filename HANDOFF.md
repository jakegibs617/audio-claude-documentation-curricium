# Handoff

You are picking up a working system, not a half-built one. Forty-three episodes
exist as audio and as a chaptered audiobook. Read `INTENT.md` first — it is
short, and every judgment call below descends from it.

## Verify the state before you trust this document

```bash
python3 -m pytest -q                      # 115 passed
ls out/audio/*.m4a | wc -l                # 43
ffprobe -v error -show_chapters -of csv out/claude-code-narrated.m4b | wc -l   # 43
```

If those three disagree with this file, believe the commands. This was written
on 2026-09-06 at commit `3c14f54`, PR #1 open with 26 commits.

## What exists

Twelve modules in `src/audiodocs/`, each with one job:

| Module | Job |
|---|---|
| `manifest` | Load and validate `curriculum.yaml`. Rejects bad input before spending. |
| `fetch` | Doc markdown, cached with a 24h expiry and an offline fallback. |
| `script` | `claude -p` rewrites a doc into narration. Caches on content. |
| `sanitize` | Refuses anything unspeakable. Raises, never warns. |
| `segments` | Splits a script into role-labelled blocks. |
| `speak` | Kokoro. The only module that touches a speech engine. |
| `art` | SVG to PNG via headless Chrome. |
| `tag` | MP4 atoms and cover artwork. |
| `book` | Assembles episodes into one chaptered `.m4b`. |
| `feed` | Podcast RSS. |
| `build` | Orchestration. The only module that knows stage order. |

Output lives in `out/` and is disposable. Nothing there is hand-edited; if you
want to change it, change what produced it.

## What to do next, in the order I would do it

**1. Listen to it.** Nobody has heard past episode 3. Seven hours exist on the
strength of one approved sample. `INTENT.md` names "it gets built and never
listened to" as the most likely failure, and that risk is currently live. Every
item below is speculative until someone confirms the thing is good.

**2. The other 42 diagrams.** Only episode 3 has real artwork; the rest inherit
the cover. The design treats the visual layer as half the product — narration
carries mental models, the diagram carries the syntax and shape that narration
cannot. Right now half the product does not exist. The spec lists 12 episodes
worth crafting by hand and a shared card template for the remaining 31.

**3. The Artifact site.** Curriculum map and show notes, per the spec. This is
where the diagrams become reachable. Do not start it before the diagrams exist.

**4. Hosting, only if you want the RSS feed.** The `.m4b` already solves phone
listening, so the feed is currently redundant. It needs an HTTP host to work at
all — podcast apps reject `file://`. Skip unless someone actually wants it.

## Things learned the hard way

Each of these cost a real failure. They are guardrails, not preferences.

**The sanitizer must run on every path.** It once ran only on cache misses, so
every script written under looser rules would have been permanently exempt from
stricter ones. If you add a path that returns a script, sanitize it there too.

**Cache keys must include what shapes the output.** The script key hashes the
prompt *and* the sanitizer's own patterns, because tightening the sanitizer
without invalidating caches wedges episodes: they raise forever and never
regenerate. The audio stamp covers script, cast, pace, album and diagram. Add a
new input to either stage and add it to the key, or you will ship stale output
that looks fine.

**Exclude, do not enumerate.** The flag detector once listed allowed wrappers
and let `**--print**` through. Anything nobody thought to list was an exemption.

**Report both streams on a subprocess failure.** A run failed 31 times with an
empty reason because the cause was on stdout and only stderr was read.

**Calibrate on real content.** Voice pace calibrated on a 94-word clip produced
audio 20% slower than intended, because a short sample never exercises
sentence-boundary pauses. Measure on a real episode.

**Look at rendered images.** Two artwork defects — an illegible label, and a
cover too thin at thumbnail size — were invisible in the SVG source and obvious
in the PNG. Render it and open it.

## Fragility worth knowing about

The speech engine has two non-obvious install steps, both in `README-SETUP.md`,
both failing with unhelpful errors: `espeakng-loader` ships a path from its own
build machine, and Kokoro's tokenizer shells out to `uv` for a spaCy model and
takes the process down if it is missing.

`ffmpeg` on this machine has broken twice from Homebrew dependency drift
(`libjxl`, then `libx265`). If audiobook assembly fails, check `ffmpeg -version`
before suspecting the code.

## Open decisions that are not mine

- **PR #1 is unmerged**, 26 commits. Merge or keep stacking.
- **The repo name reads `curricium`.** Probably a typo for `curriculum`.
  Renaming is cheap now and annoying later.
- **Four exercises are thin** — episodes 2, 6, 9 and 36 are either unbounded in
  time or presuppose something the listener may not have. They are not wrong,
  just weak, and `INTENT.md` holds that the exercise is the point of the
  episode. Fixing one costs a rebuild of that episode.
- **Publishing.** YouTube was explored and set aside. If it comes back, note
  that it turns a personal project into redistribution of Anthropic's docs, and
  should be labelled unofficial and point back at the real documentation.

## How to run things

```bash
PYTHONPATH=src python3 -m audiodocs.build --all --out out \
  --base-url "http://localhost:8000/audio/"
```

Built episodes are skipped by content stamp, so a rerun costs minutes, not
hours. One episode failing never aborts the batch, and failures print as they
happen — watch stderr, not the summary.

A full build from empty is roughly 43 model calls and about three hours, and it
will stop when it hits a usage limit. That is survivable: finished episodes are
kept, and resuming picks up exactly where it stopped.

# Claude Code Docs — Audio Curriculum

**Date:** 2026-09-04
**Status:** Approved design, pending implementation plan

## Problem

The Claude Code documentation has no audio experience. There is no podcast, no
text-to-speech, and no "listen" affordance anywhere in the doc set. Consuming
166 pages hands-free currently requires pointing a third-party screen reader at
the page text, which reads navigation chrome, code blocks, and URLs aloud and
produces something nobody finishes.

Separately, the doc set has no learning sequence. It is organized for lookup —
sidebar groupings by subject area — not for someone trying to build competence
in order. A reader has no signal about what to read before what.

This project solves both: a sequenced curriculum through the docs, delivered as
narrated audio with a complementary visual layer.

## Goals

- A listenable, sequenced course through the practitioner-relevant docs
- Audio that is written to be heard, not text mechanically spoken aloud
- A visual layer carrying exactly what audio cannot (syntax, structure, hierarchy)
- Regenerable: docs change weekly, so rebuilds must be cheap and incremental
- Zero paid dependencies; one Python package (`mutagen`) is the only install

## Non-goals

- Not a replacement for the docs as reference material
- Not covering Administration, gateways, cloud provider deployment, self-hosted
  environments, enterprise networking, or troubleshooting (~95 pages cut)
- Not hosting audio publicly or distributing the course to anyone else
- Not a general-purpose docs-to-podcast tool for arbitrary sites

## Key insight

Every documentation page ships a clean markdown twin at the same URL plus `.md`
(`/docs/en/overview` → `/docs/en/overview.md`), and `https://code.claude.com/docs/llms.txt`
is a complete machine-readable index of all 166 pages with their groupings.

There is therefore no scraping problem. The engineering effort belongs entirely
in the rewrite step — turning reference prose into narration — not in acquisition.

## Design decisions

| Decision | Choice | Rationale |
|---|---|---|
| TTS engine | macOS `say`, voice `Samantha` | Free, offline, built in, no API key. Behind an interface so a paid engine is a one-file swap. |
| Scope | Practitioner path, ~70 pages | Drops enterprise IT content the reader does not touch. |
| Audio delivery | Local MP3s + RSS feed | Offline playback, resume, and 2x speed come free from a real podcast player. |
| Visual home | Published Artifact | Readable on phone while audio plays; nothing to host. |
| Diagram craft | 12 crafted + template for the rest | The twelve are the concepts that are hard in prose *and* hard in audio. |

## Curriculum

43 episodes, roughly 8–12 minutes each, ~7 hours total. Sequenced by what makes
the next thing comprehensible, not by sidebar order. Every episode ends with a
"try this" — one concrete action in a real session, because passive listening
does not build the skill.

### Module 0 · Orientation
| # | Episode | Sources |
|---|---|---|
| 01 | What all of this is called | `glossary`, `features-overview` |

### Module 1 · Foundations — the mental model
| # | Episode | Sources |
|---|---|---|
| 02 | How Claude Code actually works | `how-claude-code-works` |
| 03 | The context window | `context-window` |
| 04 | Prompt caching | `prompt-caching` |
| 05 | Inside the .claude directory | `claude-directory` |

The module most people skip and should not. Understanding the context window and
the cache is what separates steering the tool from fighting it.

### Module 2 · Daily practice
| # | Episode | Sources |
|---|---|---|
| 06 | Your first real task | `quickstart` |
| 07 | How Claude remembers your project | `memory` |
| 08 | Sessions, resuming, and checkpoints | `sessions`, `checkpointing` |
| 09 | Common workflows | `common-workflows` |
| 10 | Best practices and the prompt library | `best-practices`, `prompt-library` |

### Module 3 · The control surface
| # | Episode | Sources |
|---|---|---|
| 11 | Settings and precedence | `settings`, `settings-reference`, `settings-example` |
| 12 | Permissions | `permissions`, `permission-modes` |
| 13 | Sandboxing | `sandboxing`, `sandbox-environments` |
| 14 | Models, fast mode, and the advisor | `model-config`, `fast-mode`, `advisor` |
| 15 | The CLI surface | `cli-reference`, `commands`, `interactive-mode`, `env-vars`, `tools-reference` |

### Module 4 · Extending — the core
| # | Episode | Sources |
|---|---|---|
| 16 | Skills | `skills` |
| 17 | Hooks — the guide | `hooks-guide` |
| 18 | Hooks — the reference | `hooks` |
| 19 | MCP | `mcp-quickstart`, `mcp` |
| 20 | Plugins | `plugins`, `plugins-reference` |
| 21 | Distribution and output styles | `discover-plugins`, `plugin-marketplaces`, `output-styles` |

Weighted heaviest deliberately. This is the material the reader already practices
by inference; the module supplies the documented model behind it.

### Module 5 · Orchestration
| # | Episode | Sources |
|---|---|---|
| 22 | Running agents in parallel | `agents` |
| 23 | Custom subagents | `sub-agents` |
| 24 | Agent teams and cross-session messaging | `agent-teams`, `cross-session-messaging` |
| 25 | Dynamic workflows | `workflows` |
| 26 | Agent view and worktrees | `agent-view`, `worktrees` |

### Module 6 · Automation
| # | Episode | Sources |
|---|---|---|
| 27 | Headless mode | `headless` |
| 28 | Schedules and routines | `scheduled-tasks`, `routines` |
| 29 | Keeping Claude on a goal | `goal` |
| 30 | Channels and deep links | `channels`, `channels-reference`, `deep-links` |
| 31 | CI, code review, and security | `github-actions`, `code-review`, `security-guidance`, `claude-security`, `ultrareview` |

### Module 7 · Surfaces
| # | Episode | Sources |
|---|---|---|
| 32 | The surface map | `platforms` |
| 33 | Remote control and mobile | `remote-control`, `mobile` |
| 34 | Chrome and computer use | `chrome`, `computer-use` |
| 35 | Desktop, web, Slack, artifacts | `desktop`, `desktop-quickstart`, `web-quickstart`, `claude-code-on-the-web`, `slack`, `claude-tag`, `artifacts` |

### Module 8 · Agent SDK — building your own
| # | Episode | Sources |
|---|---|---|
| 36 | SDK overview and quickstart | `agent-sdk/overview`, `agent-sdk/quickstart` |
| 37 | How the agent loop works | `agent-sdk/agent-loop` |
| 38 | Sessions and persistence | `agent-sdk/sessions`, `agent-sdk/session-storage` |
| 39 | Streaming and structured output | `agent-sdk/streaming-vs-single-mode`, `agent-sdk/streaming-output`, `agent-sdk/user-input`, `agent-sdk/structured-outputs` |
| 40 | Custom tools and tool search | `agent-sdk/custom-tools`, `agent-sdk/tool-search`, `agent-sdk/mcp` |
| 41 | Subagents, skills, and plugins in the SDK | `agent-sdk/subagents`, `agent-sdk/skills`, `agent-sdk/plugins`, `agent-sdk/modifying-system-prompts` |
| 42 | Permissions, hooks, and checkpointing | `agent-sdk/permissions`, `agent-sdk/hooks`, `agent-sdk/file-checkpointing` |
| 43 | Cost, observability, and deployment | `agent-sdk/cost-tracking`, `agent-sdk/observability`, `agent-sdk/todo-tracking`, `agent-sdk/hosting`, `agent-sdk/secure-deployment` |

### Module 9 · Staying current — recurring
A weekly digest episode generated from `whats-new` and `changelog`. Unnumbered
and appended as published. This is the part that keeps earning after the course
is finished.

## Architecture

```
curriculum.yaml
      |
      v
  fetch  ->  .md cache
      |
      v
  script ->  narration cache      (claude -p, headless)
      |
      v
   speak ->  AIFF -> M4A          (say + afconvert)
      |
   art   ->  SVG -> PNG           (headless Chrome)
      |
      v
    tag  ->  M4A + tags + artwork
      |
      +----> feed.xml
      +----> site (Artifact)
```

### Components

Each is independently testable with one clear responsibility.

- **`manifest`** — parses and validates `curriculum.yaml`. Owns the episode
  schema: number, title, source page slugs, exercise text, diagram id.
  Depends on nothing.
- **`fetch`** — resolves a slug to `https://code.claude.com/docs/en/<slug>.md`,
  retrieves it, caches by slug and content hash. Pure I/O.
- **`script`** — the interesting component. Sends source markdown to `claude -p`
  with a narration prompt, receives a spoken-word script, runs it through a
  sanitizer. Cached by hash of (sources + prompt version).
- **`sanitize`** — pure function, no I/O. Strips or rewrites what cannot be
  spoken: fenced code, bare URLs, tables, "see below" references, markdown
  syntax. Fails loudly rather than silently emitting a URL for TTS to spell out.
- **`speak`** — a single `synthesize(text, out_path)` interface. The macOS
  implementation shells to `say` then `afconvert`. Output is AAC in an MP4
  container (`.m4a`) because `afconvert` cannot produce MPEG-1 Layer III;
  podcast players handle m4a natively. Swapping to a paid engine replaces this
  file only.
- **`art`** — renders an episode's SVG to PNG via headless Chrome.
- **`tag`** — writes ID3 title, track number, album, and embedded artwork via
  `mutagen`. This is the project's only third-party dependency: macOS ships no
  built-in that writes ID3 artwork (`afconvert` converts audio but does not tag),
  and artwork is what puts the diagram on the lock screen.
- **`feed`** — generates `feed.xml` from the manifest and rendered files.
- **`site`** — builds the Artifact HTML: curriculum map plus 43 episode cards.
- **`build`** — orchestrates the above; the only component that knows the order.

### Caching

Every stage caches on a content hash of its inputs. A doc page that has not
changed is not refetched, not rescripted, and not respoken. This matters: a full
rebuild is 43 TTS runs and 43 model calls, and the weekly digest must not trigger one.

## Narration rules

The rewrite prompt enforces these; the sanitizer verifies them.

- Concepts, trade-offs, and decision rules spoken in full prose
- Code described, never read — "a hooks block keyed by event name, each holding
  a matcher and a command", not the JSON
- No bare URLs, no `--flag` spelling-out, no "as shown above"
- Each episode opens by connecting to the previous one and closes with the exercise
- Target 1,200–1,800 words, which lands at 8–12 minutes

## Visual system

The visual layer carries the residue audio drops. It is not a restatement.

**Episode artwork.** Each episode's diagram renders to PNG and embeds as the
MP3's ID3 artwork, so podcast players display it during playback. The
context-window diagram is on screen while the narration explains it.

**Show notes.** Per episode: exact commands the narration refused to speak,
config shapes, file paths, and the exercise.

**Curriculum map.** All 9 modules and 43 episodes in one view with progress.

**Diagram vocabulary.** A shared visual grammar reused across episodes so it
accumulates meaning — the context-window bar introduced in Module 1 reappears in
the subagent episode in Module 5 and is already legible. One token set, theme-aware,
accessible contrast, authored as inline SVG.

Twelve diagrams receive full craft:

| Diagram | Module |
|---|---|
| Context window anatomy — prompt, CLAUDE.md, tools, history, cache breakpoints | 1 |
| Prompt caching — breakpoints and TTL | 1 |
| `.claude/` tree — user vs project vs plugin precedence | 1 |
| Settings cascade — managed, user, project, local | 3 |
| Permission resolution — mode x rule to allow/ask/deny | 3 |
| Hook lifecycle — firing order around a tool call | 4 |
| Skill and plugin resolution order | 4 |
| MCP wiring — client, transport, server | 4 |
| Subagent fan-out — and why a fresh agent starts cold | 5 |
| Dynamic workflow orchestration | 5 |
| Surface topology — one engine, many front ends | 7 |
| SDK agent loop with custom tools and hooks | 8 |

The remaining 31 episodes use a shared card template: module color, title, key
commands, exercise. Consistent and cheap.

## Error handling

- **Fetch failure** — retry with backoff, then fail that episode and continue.
  A broken page must not abort a 43-episode build. Build report lists failures.
- **Removed page** — a slug that 404s is reported as a manifest error, not
  silently skipped. Docs change; the manifest must be told.
- **Sanitizer rejection** — if a script still contains code fences or bare URLs
  after rewriting, fail that episode loudly. Silently narrating a URL is the
  exact failure mode this project exists to avoid.
- **TTS failure** — `say` failing is fatal for that episode, reported, build continues.
- **Voice not installed** — `speak` verifies the configured voice exists before
  synthesizing and names the System Settings path to install it. Only 25 legacy
  voices are present on this machine; the premium voices (`Ava`, `Zoe`) require a
  manual download and must never be assumed.
- **Chrome unavailable** — diagram rendering degrades to no artwork rather than
  failing the audio build. Audio is the primary deliverable.

## Testing

Following the repository's test-first default. The seams worth testing:

- `manifest` — valid file parses; missing fields, duplicate episode numbers, and
  unknown slugs are rejected with useful messages
- `sanitize` — pure function, the densest test target. Code fences removed, bare
  URLs removed, tables flattened, "see above" caught. Given known-bad input it
  must reject rather than pass through.
- `feed` — well-formed RSS, correct enclosure lengths and MIME types, stable
  episode ordering
- `tag` — write then read back; title, track, and artwork round-trip
- `cache` — unchanged input skips work; changed input invalidates

`speak` and `art` shell out to system binaries and get one smoke test each, not
unit tests. `script` calls a model and is verified through `sanitize` on its output.

## Risks and open issues

- **RSS on phone.** Podcast apps will not subscribe to a `file://` feed. Desktop
  listening works immediately over a local HTTP server. Phone playback
  realistically means syncing MP3s or putting the folder in a cloud drive and
  pointing a player at it. The feed is cheap enough to build regardless, but it
  does not by itself deliver phone subscription.
- **`say` voice quality — the largest practical risk.** This machine has only the
  25 legacy voices; `Samantha` is the sole usable en_US narration voice and is
  noticeably synthetic across seven hours. The premium voices (`Ava`, `Zoe`) are a
  free but manual GUI download. Phase 1 opens with a voice audition for exactly
  this reason. The engine interface exists so a paid engine remains available.
- **Docs drift.** 166 pages change weekly. Content hashing detects drift, but a
  restructured page can silently change what an episode teaches. The build report
  should surface which episodes changed.
- **Rewrite quality is unproven.** Whether `claude -p` reliably produces good
  narration across 43 varied pages is the largest unknown in this design. The
  implementation plan should front-load one real episode end to end before
  building the other 42.

## Phasing

The work decomposes into three phases with a decision point after each. Phase 1
exists to retire the rewrite-quality risk before any breadth work is committed.

1. **One episode, end to end** — manifest, fetch, script, sanitize, speak, tag,
   and a single crafted diagram, for episode 03 (the context window). Listen to
   it. If the narration is not good, the design changes before 42 more are built.
2. **Breadth** — the remaining 42 episodes, feed generation, caching, build report.
3. **Visual layer** — the other 11 crafted diagrams, the card template, the
   Artifact site with curriculum map and show notes.

## Next step

Implementation plan for phase 1 via the writing-plans skill.

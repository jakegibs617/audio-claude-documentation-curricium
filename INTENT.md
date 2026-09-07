# Intent

## The problem

The Claude Code documentation has no audio experience — no podcast, no
text-to-speech, no "listen" affordance anywhere in 166 pages. Pointing a screen
reader at the page text produces something nobody finishes, because it reads
navigation chrome, code blocks, and URLs aloud.

It also has no learning sequence. The docs are organized for lookup, not for
building competence in order. A reader has no signal about what to read before
what.

This project fixes both. It is a sequenced course through the docs, narrated,
with a visual layer alongside.

## Who it is for

One person, learning deliberately. This is a personal instrument, not a product.
It is not distributed, not hosted publicly, and not generalized into a
docs-to-podcast tool for arbitrary sites. Every decision should be made for the
listener, who is one specific person walking or driving with their hands full.

## What done looks like

Forty-three episodes, roughly seven hours, that the listener actually finishes —
and a weekly digest that keeps the thing alive after the course ends.

Finishing is the bar. A technically complete course nobody listens to has failed.

## Principles

These exist to settle arguments the spec does not answer.

**Audio and visuals split by what each medium can carry.** Narration is good at
mental models, trade-offs, and why-this-exists. It physically cannot carry flag
syntax, config shape, directory nesting, or a branching sequence. The visual
layer carries exactly that residue. Neither medium repeats the other — a diagram
that restates the audio is waste, and narration that spells out a URL is worse
than silence.

**The sanitizer fails loudly.** Silently narrating a code fence or a URL is the
precise failure this project exists to prevent. A violation raises; it never
warns. If that feels strict during a build, the strictness is working.

**Sequence over coverage.** This is a course, not a mirror of the doc set. Order
is chosen by what makes the next thing comprehensible. Ninety-five pages of
enterprise deployment were cut deliberately, and cutting more is always on the
table. Coverage is not the goal; competence is.

**Every episode ends in action.** Passive listening does not build the skill.
The exercise is not a nicety at the end of the script — it is the point of the
episode, and the narration exists to make it make sense.

**Regenerable, not precious.** The docs change weekly. Every stage caches on a
content hash so a rebuild redoes only what moved. Nothing in `out/` is ever
hand-edited or committed. If a fix requires editing generated output, the fix
belongs upstream — usually in the narration prompt.

**The engine is swappable; the curriculum is the asset.** Text-to-speech sits
behind one function for a reason. Voices and vendors will change. What is worth
keeping is `curriculum.yaml`, the narration prompt, and the diagrams. That
promise was cashed once already: the engine moved from the macOS `say` command
to Kokoro, and only `speak.py` changed.

**A voice change means something.** Three voices, and each one carries the same
meaning in every episode: the narrator explains, a second voice names the
trade-off, and a third always closes on the exercise. Audio cannot show a
heading, so a change of speaker is the only structural signal available -- which
is exactly why it must never be spent on variety. A listener learns the exercise
voice once and then recognises it for the rest of the course.

## Non-goals

- Replacing the docs as reference material. This teaches; it does not answer
  lookups.
- Enterprise content — administration, gateways, cloud provider deployment,
  self-hosted environments, networking.
- Publishing, hosting, or distributing the audio to anyone else.
- A general-purpose tool. Every shortcut that assumes these specific docs is
  allowed and encouraged.

## How this fails

Worth naming plainly, so the failure is recognizable early:

- **The narration is boring.** The largest real risk. Documentation rewritten
  faithfully is still documentation. The fix is always the prompt, never the
  pipeline.
- **The voice is unbearable.** Seven hours is a long time. The engine interface
  exists so this stays reversible, but re-synthesizing 43 episodes is expensive
  once they exist.
- **The cast becomes noise.** Three voices only work while each one means one
  thing. The moment a voice change is decoration, every change stops carrying
  information and the whole device is worse than a single narrator.
- **It gets built and never listened to.** The most likely failure of all, and
  the one no test catches.

## Where the details live

- Design and decisions: `docs/superpowers/specs/2026-09-04-docs-audio-curriculum-design.md`
- Phase 1 execution: `docs/superpowers/plans/2026-09-04-docs-audio-phase-1.md`
- The course itself: `curriculum.yaml`
- The narration rules, enforced: `src/audiodocs/script.py` and `src/audiodocs/sanitize.py`

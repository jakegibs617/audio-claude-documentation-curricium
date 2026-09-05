# Docs Audio Curriculum — Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce one finished episode — episode 03, "The context window" — as a tagged MP3 with embedded diagram artwork, through a pipeline whose every stage is independently tested.

**Architecture:** A linear pipeline of small, single-responsibility modules — `manifest → fetch → script → sanitize → speak → art → tag` — orchestrated by `build`. Each stage caches on a content hash of its inputs. The TTS engine sits behind a one-function interface so a paid engine is a single-file swap. Phase 1 builds the whole pipeline but drives only one episode through it, because the unproven part of this design is narration quality, not plumbing.

**Tech Stack:** Python 3.11.6 (stdlib + PyYAML, both already present), `mutagen` (the only install), macOS `say` and `afconvert` for TTS, headless Google Chrome for SVG→PNG, `claude -p` for the rewrite step, pytest 9.0.3.

**Spec:** `docs/superpowers/specs/2026-09-04-docs-audio-curriculum-design.md`

## Global Constraints

- Python 3.11.6. `tomllib` is available but the manifest is YAML; PyYAML is already installed.
- `mutagen` is the **only** permitted third-party runtime dependency. Everything else is stdlib or a macOS system binary.
- Voice is configuration, never hardcoded. Default `Samantha` — it is the only usable en_US narration voice installed on this machine. `Ava`/`Zoe` are premium voices requiring a manual GUI download and MUST NOT be assumed present.
- Podcast artwork is square, 1400x1400 px minimum (Apple Podcasts requirement).
- Album name for all ID3 tags: `Claude Code, Narrated`
- Doc source URL pattern: `https://code.claude.com/docs/en/<slug>.md`
- Generated output (`out/`) is never committed.
- The sanitizer FAILS LOUDLY. Silently narrating a URL or a code fence is the precise failure this project exists to prevent; never downgrade a violation to a warning.

---

## File Structure

| File | Responsibility |
|---|---|
| `pyproject.toml` | Package metadata, pytest config |
| `curriculum.yaml` | Episode manifest (Module 1 episodes in phase 1) |
| `src/audiodocs/manifest.py` | Parse and validate the manifest. No I/O beyond reading the file. |
| `src/audiodocs/fetch.py` | Slug → doc markdown, cached on disk |
| `src/audiodocs/sanitize.py` | Pure functions: strip markdown, detect unspeakable content |
| `src/audiodocs/script.py` | Drive `claude -p` to rewrite docs into narration |
| `src/audiodocs/speak.py` | TTS interface + macOS `say` implementation |
| `src/audiodocs/art.py` | SVG → PNG via headless Chrome |
| `src/audiodocs/tag.py` | ID3 tags and embedded artwork via mutagen |
| `src/audiodocs/build.py` | Orchestration; the only module that knows stage order |
| `diagrams/ep03-context-window.svg` | The first crafted diagram |
| `tests/` | One test module per source module |

---

## Task 0: Voice audition (do this first, before any code)

This task exists to retire the cheapest-to-check risk in the project. Seven hours of
narration in an intolerable voice is worthless no matter how good the pipeline is.

- [ ] **Step 1: Hear the default voice on real content**

```bash
say -v Samantha "The context window is not a filing cabinet. It is a desk. \
Everything Claude can see right now sits on that desk: the system prompt, your \
CLAUDE dot M D files, the tool definitions, and every message so far."
```

- [ ] **Step 2: Decide and record the decision**

If Samantha is good enough, continue — no change needed.

If it is not, open System Settings → Accessibility → Spoken Content → System Voice
→ Manage Voices, download **Ava (Premium)** and **Zoe (Premium)**, then re-run:

```bash
say -v Ava "The context window is not a filing cabinet. It is a desk."
```

Then set the chosen voice in `curriculum.yaml` `voice:` in Task 1. If neither is
acceptable, STOP and escalate — the spec's engine interface exists for this, but
switching to a paid engine is a design decision, not an implementation one.

---

## Task 1: Project scaffold and manifest

**Files:**
- Create: `pyproject.toml`, `.gitignore`, `curriculum.yaml`
- Create: `src/audiodocs/__init__.py`, `src/audiodocs/manifest.py`
- Test: `tests/test_manifest.py`

**Interfaces:**
- Consumes: nothing
- Produces:
  - `Episode` dataclass with fields `number: int`, `title: str`, `sources: list[str]`, `exercise: str`, `diagram: str | None`
  - `Curriculum` dataclass with fields `album: str`, `voice: str`, `episodes: list[Episode]`
  - `load_curriculum(path: Path) -> Curriculum`
  - `ManifestError(Exception)`

- [ ] **Step 1: Initialize the repository**

The project directory is not yet a git repository. The plan requires frequent commits.

```bash
cd /Users/jacobgiberson/Desktop/ai_projects_private
git init
git add docs/
git commit -m "docs: add audio curriculum spec and phase 1 plan"
```

- [ ] **Step 2: Create the package scaffold**

```bash
mkdir -p src/audiodocs tests diagrams
touch src/audiodocs/__init__.py
```

`pyproject.toml`:

```toml
[project]
name = "audiodocs"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = ["PyYAML", "mutagen"]

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
markers = ["smoke: exercises a real system binary (say, afconvert, Chrome)"]
```

`.gitignore`:

```
out/
__pycache__/
*.pyc
.pytest_cache/
```

- [ ] **Step 3: Install the one dependency**

```bash
python3 -m pip install mutagen
python3 -c "import mutagen; print(mutagen.version_string)"
```
Expected: a version string, e.g. `1.47.0`

- [ ] **Step 4: Write the failing test**

`tests/test_manifest.py`:

```python
import pytest
from pathlib import Path
from audiodocs.manifest import load_curriculum, ManifestError


def write(tmp_path: Path, body: str) -> Path:
    p = tmp_path / "curriculum.yaml"
    p.write_text(body)
    return p


VALID = """
album: Claude Code, Narrated
voice: Samantha
episodes:
  - number: 3
    title: The context window
    sources: [context-window]
    exercise: Run /context in a long session and read the breakdown.
    diagram: ep03-context-window
  - number: 4
    title: Prompt caching
    sources: [prompt-caching]
    exercise: Run /cost after a long session.
"""


def test_loads_valid_curriculum(tmp_path):
    c = load_curriculum(write(tmp_path, VALID))
    assert c.album == "Claude Code, Narrated"
    assert c.voice == "Samantha"
    assert len(c.episodes) == 2
    assert c.episodes[0].number == 3
    assert c.episodes[0].sources == ["context-window"]
    assert c.episodes[0].diagram == "ep03-context-window"
    assert c.episodes[1].diagram is None


def test_rejects_duplicate_episode_numbers(tmp_path):
    body = VALID.replace("  - number: 4", "  - number: 3")
    with pytest.raises(ManifestError, match="duplicate episode number: 3"):
        load_curriculum(write(tmp_path, body))


def test_rejects_missing_required_field(tmp_path):
    body = VALID.replace("    title: The context window\n", "")
    with pytest.raises(ManifestError, match="episode 3 missing required field: title"):
        load_curriculum(write(tmp_path, body))


def test_rejects_empty_sources(tmp_path):
    body = VALID.replace("    sources: [context-window]", "    sources: []")
    with pytest.raises(ManifestError, match="episode 3 has no sources"):
        load_curriculum(write(tmp_path, body))
```

- [ ] **Step 5: Run the test to verify it fails**

Run: `python3 -m pytest tests/test_manifest.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'audiodocs.manifest'`

- [ ] **Step 6: Write the minimal implementation**

`src/audiodocs/manifest.py`:

```python
"""Parse and validate the episode manifest."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


class ManifestError(Exception):
    """The curriculum file is malformed."""


@dataclass(frozen=True)
class Episode:
    number: int
    title: str
    sources: list[str]
    exercise: str
    diagram: str | None = None

    @property
    def slug(self) -> str:
        """Filesystem-safe stem, e.g. '03-the-context-window'."""
        safe = "".join(c if c.isalnum() else "-" for c in self.title.lower())
        while "--" in safe:
            safe = safe.replace("--", "-")
        return f"{self.number:02d}-{safe.strip('-')}"


@dataclass(frozen=True)
class Curriculum:
    album: str
    voice: str
    episodes: list[Episode]

    def episode(self, number: int) -> Episode:
        for ep in self.episodes:
            if ep.number == number:
                return ep
        raise ManifestError(f"no episode numbered {number}")


REQUIRED = ("number", "title", "sources", "exercise")


def load_curriculum(path: Path) -> Curriculum:
    data = yaml.safe_load(Path(path).read_text())
    if not isinstance(data, dict):
        raise ManifestError("curriculum must be a mapping")

    episodes: list[Episode] = []
    seen: set[int] = set()

    for raw in data.get("episodes") or []:
        number = raw.get("number")
        for field in REQUIRED:
            if field not in raw:
                raise ManifestError(f"episode {number} missing required field: {field}")
        if not raw["sources"]:
            raise ManifestError(f"episode {number} has no sources")
        if number in seen:
            raise ManifestError(f"duplicate episode number: {number}")
        seen.add(number)
        episodes.append(
            Episode(
                number=number,
                title=raw["title"],
                sources=list(raw["sources"]),
                exercise=raw["exercise"],
                diagram=raw.get("diagram"),
            )
        )

    return Curriculum(
        album=data.get("album", "Claude Code, Narrated"),
        voice=data.get("voice", "Samantha"),
        episodes=episodes,
    )
```

- [ ] **Step 7: Run the tests to verify they pass**

Run: `python3 -m pytest tests/test_manifest.py -v`
Expected: 4 passed

- [ ] **Step 8: Create the real curriculum file**

`curriculum.yaml` — Module 1 only for phase 1; the remaining 39 episodes are data
added in phase 2.

```yaml
album: Claude Code, Narrated
voice: Samantha
episodes:
  - number: 2
    title: How Claude Code actually works
    sources: [how-claude-code-works]
    exercise: Run claude with no arguments and watch what loads before your first prompt.
  - number: 3
    title: The context window
    sources: [context-window]
    exercise: Run /context in a session that has been going a while, and read the breakdown out loud.
    diagram: ep03-context-window
  - number: 4
    title: Prompt caching
    sources: [prompt-caching]
    exercise: Run /cost after a long session and find what the cache saved you.
  - number: 5
    title: Inside the .claude directory
    sources: [claude-directory]
    exercise: Run ls -R ~/.claude and name the purpose of every top-level entry.
```

- [ ] **Step 9: Commit**

```bash
git add pyproject.toml .gitignore curriculum.yaml src/audiodocs tests/test_manifest.py
git commit -m "feat: add curriculum manifest parsing and validation"
```

---

## Task 2: Fetch documentation pages with caching

**Files:**
- Create: `src/audiodocs/fetch.py`
- Test: `tests/test_fetch.py`

**Interfaces:**
- Consumes: nothing from earlier tasks
- Produces:
  - `doc_url(slug: str) -> str`
  - `fetch_doc(slug: str, cache_dir: Path, opener=None) -> str`
  - `FetchError(Exception)`

`opener` is an injection seam for tests: a callable taking a URL string and
returning the page text. Production passes `None`, which uses `urllib`.

- [ ] **Step 1: Write the failing test**

`tests/test_fetch.py`:

```python
import pytest
from audiodocs.fetch import doc_url, fetch_doc, FetchError


def test_doc_url_appends_md_suffix():
    assert doc_url("context-window") == "https://code.claude.com/docs/en/context-window.md"


def test_doc_url_handles_nested_slug():
    assert doc_url("agent-sdk/overview") == "https://code.claude.com/docs/en/agent-sdk/overview.md"


def test_fetches_and_caches(tmp_path):
    calls = []

    def opener(url):
        calls.append(url)
        return "# Context window\n\nBody text."

    first = fetch_doc("context-window", tmp_path, opener=opener)
    second = fetch_doc("context-window", tmp_path, opener=opener)

    assert first == second == "# Context window\n\nBody text."
    assert len(calls) == 1, "second call must be served from cache"


def test_nested_slug_caches_without_path_collision(tmp_path):
    def opener(url):
        return url

    fetch_doc("agent-sdk/overview", tmp_path, opener=opener)
    cached = list(tmp_path.rglob("*.md"))
    assert len(cached) == 1


def test_raises_on_empty_response(tmp_path):
    with pytest.raises(FetchError, match="empty response"):
        fetch_doc("context-window", tmp_path, opener=lambda url: "")
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m pytest tests/test_fetch.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'audiodocs.fetch'`

- [ ] **Step 3: Write the minimal implementation**

`src/audiodocs/fetch.py`:

```python
"""Retrieve documentation pages as markdown, cached on disk."""
from __future__ import annotations

import urllib.error
import urllib.request
from pathlib import Path

BASE = "https://code.claude.com/docs/en"
USER_AGENT = "audiodocs/0.1 (personal learning curriculum builder)"


class FetchError(Exception):
    """A documentation page could not be retrieved."""


def doc_url(slug: str) -> str:
    return f"{BASE}/{slug}.md"


def _default_opener(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        raise FetchError(f"{url} returned HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise FetchError(f"{url} unreachable: {exc.reason}") from exc


def fetch_doc(slug: str, cache_dir: Path, opener=None) -> str:
    """Return the markdown for `slug`, fetching only on a cache miss."""
    cache_dir = Path(cache_dir)
    cached = cache_dir / f"{slug.replace('/', '__')}.md"

    if cached.exists():
        return cached.read_text()

    text = (opener or _default_opener)(doc_url(slug))
    if not text.strip():
        raise FetchError(f"{doc_url(slug)} returned an empty response")

    cached.parent.mkdir(parents=True, exist_ok=True)
    cached.write_text(text)
    return text
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m pytest tests/test_fetch.py -v`
Expected: 5 passed

- [ ] **Step 5: Verify against the live site once**

```bash
python3 -c "
from pathlib import Path
from audiodocs.fetch import fetch_doc
import sys; sys.path.insert(0, 'src')
text = fetch_doc('context-window', Path('out/cache/docs'))
print(len(text), 'characters')
print(text[:200])
"
```
Expected: several thousand characters, beginning with markdown frontmatter or a heading.

- [ ] **Step 6: Commit**

```bash
git add src/audiodocs/fetch.py tests/test_fetch.py
git commit -m "feat: add cached documentation fetching"
```

---

## Task 3: The sanitizer

The densest test target in the project, and the component that enforces the
project's whole reason for existing. Pure functions, no I/O.

**Files:**
- Create: `src/audiodocs/sanitize.py`
- Test: `tests/test_sanitize.py`

**Interfaces:**
- Consumes: nothing
- Produces:
  - `find_violations(text: str) -> list[str]` — human-readable violation descriptions
  - `assert_speakable(text: str) -> None` — raises `UnspeakableError` if any exist
  - `UnspeakableError(Exception)`

- [ ] **Step 1: Write the failing test**

`tests/test_sanitize.py`:

```python
import pytest
from audiodocs.sanitize import find_violations, assert_speakable, UnspeakableError

CLEAN = (
    "The context window is not a filing cabinet, it is a desk. "
    "Everything Claude can see right now sits on that desk at once. "
    "When the desk fills up, older messages get summarized to make room."
)


def test_clean_narration_has_no_violations():
    assert find_violations(CLEAN) == []


def test_detects_fenced_code_block():
    text = CLEAN + "\n\n```bash\nclaude --resume\n```\n"
    violations = find_violations(text)
    assert any("code fence" in v for v in violations)


def test_detects_bare_url():
    text = CLEAN + " See https://code.claude.com/docs/en/context-window for more."
    violations = find_violations(text)
    assert any("URL" in v for v in violations)


def test_detects_markdown_table():
    text = CLEAN + "\n\n| Flag | Meaning |\n| --- | --- |\n| -p | print |\n"
    violations = find_violations(text)
    assert any("table" in v for v in violations)


def test_detects_dangling_reference():
    for phrase in ("as shown above", "see the table below", "in the diagram below"):
        violations = find_violations(CLEAN + " " + phrase)
        assert any("dangling reference" in v for v in violations), phrase


def test_detects_command_flag():
    violations = find_violations(CLEAN + " Pass the --resume flag.")
    assert any("flag" in v for v in violations)


def test_assert_speakable_passes_clean_text():
    assert_speakable(CLEAN) is None


def test_assert_speakable_raises_and_names_every_violation():
    text = CLEAN + "\n\n```python\nx = 1\n```\nSee https://example.com as shown above."
    with pytest.raises(UnspeakableError) as excinfo:
        assert_speakable(text)
    message = str(excinfo.value)
    assert "code fence" in message
    assert "URL" in message
    assert "dangling reference" in message
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m pytest tests/test_sanitize.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'audiodocs.sanitize'`

- [ ] **Step 3: Write the minimal implementation**

`src/audiodocs/sanitize.py`:

```python
"""Detect content that must never reach a text-to-speech engine.

A narration script is meant to be heard. Code fences, bare URLs, tables, and
references to things the listener cannot see are all failures of the rewrite
step. This module names them; it never silently repairs them.
"""
from __future__ import annotations

import re

CODE_FENCE = re.compile(r"```")
BARE_URL = re.compile(r"https?://\S+")
TABLE_ROW = re.compile(r"^\s*\|.*\|\s*$", re.MULTILINE)
DANGLING = re.compile(
    r"\b(?:as (?:shown|seen) (?:above|below)"
    r"|see the \w+ (?:above|below)"
    r"|in the \w+ (?:above|below)"
    r"|(?:above|below))\b",
    re.IGNORECASE,
)
COMMAND_FLAG = re.compile(r"(?:^|\s)--?[a-zA-Z][\w-]*")


class UnspeakableError(Exception):
    """A script contains content that cannot be spoken aloud."""


def find_violations(text: str) -> list[str]:
    """Return a description for each kind of unspeakable content present."""
    violations: list[str] = []

    if CODE_FENCE.search(text):
        violations.append("contains a code fence; code must be described, not read")
    if BARE_URL.search(text):
        violations.append("contains a URL; a spoken URL is unusable")
    if TABLE_ROW.search(text):
        violations.append("contains a markdown table; tables must be prose")
    if DANGLING.search(text):
        violations.append("contains a dangling reference to unseen content")
    if COMMAND_FLAG.search(text):
        violations.append("contains a command flag; flags must be named in words")

    return violations


def assert_speakable(text: str) -> None:
    """Raise if `text` contains anything that must not be narrated."""
    violations = find_violations(text)
    if violations:
        raise UnspeakableError(
            "script is not speakable:\n" + "\n".join(f"  - {v}" for v in violations)
        )
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m pytest tests/test_sanitize.py -v`
Expected: 8 passed

If `test_clean_narration_has_no_violations` fails because `DANGLING` matches a
bare "above"/"below" in ordinary prose, tighten the final alternation rather than
loosening the others — false negatives here are worse than false positives.

- [ ] **Step 5: Commit**

```bash
git add src/audiodocs/sanitize.py tests/test_sanitize.py
git commit -m "feat: add narration sanitizer with loud failure on unspeakable content"
```

---

## Task 4: The rewrite step

**Files:**
- Create: `src/audiodocs/script.py`
- Test: `tests/test_script.py`

**Interfaces:**
- Consumes: `Episode` from `audiodocs.manifest`, `assert_speakable` from `audiodocs.sanitize`
- Produces:
  - `NARRATION_PROMPT: str`
  - `build_script(episode: Episode, sources_text: str, cache_dir: Path, runner=None) -> str`
  - `ScriptError(Exception)`

`runner` is the injection seam: a callable taking `(prompt: str, stdin: str)` and
returning the model's text output.

- [ ] **Step 1: Write the failing test**

`tests/test_script.py`:

```python
import pytest
from audiodocs.manifest import Episode
from audiodocs.script import build_script, ScriptError, NARRATION_PROMPT

EPISODE = Episode(
    number=3,
    title="The context window",
    sources=["context-window"],
    exercise="Run /context and read the breakdown.",
    diagram="ep03-context-window",
)

GOOD = (
    "The context window is not a filing cabinet, it is a desk. Everything Claude "
    "can see sits there at once. When it fills, older turns get summarized."
)


def test_returns_model_output(tmp_path):
    script = build_script(EPISODE, "# Context window\n\nBody.", tmp_path,
                          runner=lambda prompt, stdin: GOOD)
    assert script == GOOD


def test_prompt_includes_title_and_exercise(tmp_path):
    seen = {}

    def runner(prompt, stdin):
        seen["prompt"] = prompt
        seen["stdin"] = stdin
        return GOOD

    build_script(EPISODE, "SOURCE BODY", tmp_path, runner=runner)
    assert "The context window" in seen["prompt"]
    assert "Run /context and read the breakdown." in seen["prompt"]
    assert seen["stdin"] == "SOURCE BODY"


def test_rejects_unspeakable_output(tmp_path):
    bad = GOOD + "\n\n```bash\nclaude --resume\n```"
    with pytest.raises(ScriptError, match="code fence"):
        build_script(EPISODE, "body", tmp_path, runner=lambda p, s: bad)


def test_caches_result(tmp_path):
    calls = []

    def runner(prompt, stdin):
        calls.append(1)
        return GOOD

    build_script(EPISODE, "body", tmp_path, runner=runner)
    build_script(EPISODE, "body", tmp_path, runner=runner)
    assert len(calls) == 1


def test_changed_source_invalidates_cache(tmp_path):
    calls = []

    def runner(prompt, stdin):
        calls.append(1)
        return GOOD

    build_script(EPISODE, "body one", tmp_path, runner=runner)
    build_script(EPISODE, "body two", tmp_path, runner=runner)
    assert len(calls) == 2


def test_narration_prompt_forbids_code_and_urls():
    assert "code" in NARRATION_PROMPT.lower()
    assert "url" in NARRATION_PROMPT.lower()
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m pytest tests/test_script.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'audiodocs.script'`

- [ ] **Step 3: Write the minimal implementation**

`src/audiodocs/script.py`:

```python
"""Rewrite reference documentation into spoken-word narration."""
from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

from .manifest import Episode
from .sanitize import UnspeakableError, assert_speakable

PROMPT_VERSION = "1"

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
- Never include a URL, and never write a command flag like a double dash followed \
by a word. Name flags in words: "the print flag", "the resume flag".
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
        timeout=600,
    )
    if result.returncode != 0:
        raise ScriptError(f"claude -p failed: {result.stderr.strip()}")
    return result.stdout.strip()


def _cache_key(episode: Episode, sources_text: str) -> str:
    digest = hashlib.sha256()
    digest.update(PROMPT_VERSION.encode())
    digest.update(episode.title.encode())
    digest.update(episode.exercise.encode())
    digest.update(sources_text.encode())
    return digest.hexdigest()[:16]


def build_script(
    episode: Episode, sources_text: str, cache_dir: Path, runner=None
) -> str:
    """Return narration for `episode`, calling the model only on a cache miss."""
    cache_dir = Path(cache_dir)
    cached = cache_dir / f"{episode.slug}-{_cache_key(episode, sources_text)}.txt"

    if cached.exists():
        return cached.read_text()

    prompt = NARRATION_PROMPT.format(title=episode.title, exercise=episode.exercise)
    script = (runner or _default_runner)(prompt, sources_text)

    if not script.strip():
        raise ScriptError(f"episode {episode.number}: model returned nothing")

    try:
        assert_speakable(script)
    except UnspeakableError as exc:
        raise ScriptError(f"episode {episode.number}: {exc}") from exc

    cached.parent.mkdir(parents=True, exist_ok=True)
    cached.write_text(script)
    return script
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m pytest tests/test_script.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add src/audiodocs/script.py tests/test_script.py
git commit -m "feat: add documentation-to-narration rewrite step"
```

---

## Task 5: Text to speech

**Files:**
- Create: `src/audiodocs/speak.py`
- Test: `tests/test_speak.py`

**Interfaces:**
- Consumes: nothing
- Produces:
  - `synthesize(text: str, out_path: Path, voice: str = "Samantha") -> Path`
  - `available_voices() -> list[str]`
  - `SpeakError(Exception)`

This module is the swap point for a paid engine. Nothing else in the codebase may
shell out to `say`.

- [ ] **Step 1: Write the failing test**

`tests/test_speak.py`:

```python
import pytest
from pathlib import Path
from audiodocs.speak import synthesize, available_voices, SpeakError


def test_available_voices_includes_samantha():
    assert "Samantha" in available_voices()


def test_rejects_unavailable_voice(tmp_path):
    with pytest.raises(SpeakError, match="voice not installed"):
        synthesize("hello", tmp_path / "x.m4a", voice="NoSuchVoice")


def test_rejects_empty_text(tmp_path):
    with pytest.raises(SpeakError, match="empty"):
        synthesize("   ", tmp_path / "x.m4a")


@pytest.mark.smoke
def test_produces_a_playable_audio_file(tmp_path):
    out = synthesize("Testing one two three.", tmp_path / "smoke.m4a")
    assert out.exists()
    assert out.stat().st_size > 1000
    assert not (tmp_path / "smoke.aiff").exists(), "intermediate must be cleaned up"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m pytest tests/test_speak.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'audiodocs.speak'`

- [ ] **Step 3: Write the minimal implementation**

`src/audiodocs/speak.py`:

```python
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
        ["afconvert", "-f", "mp4f", "-d", "aac", "-b", "64000", str(aiff), str(m4a)],
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
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m pytest tests/test_speak.py -v`
Expected: 4 passed

**Note on the container format:** `afconvert` cannot produce MPEG-1 Layer III,
so this pipeline produces AAC in an MP4 container with the `.m4a` extension, and
Task 7 tags it with mutagen's `MP4`/`covr` atoms rather than `ID3`/`APIC`. Podcast
players and Apple Podcasts handle m4a natively. Do not rename these files to
`.mp3` — the extension would not match the bytes.

- [ ] **Step 5: Commit**

```bash
git add src/audiodocs/speak.py tests/test_speak.py
git commit -m "feat: add macOS text-to-speech behind a swappable interface"
```

---

## Task 6: The first diagram and SVG rendering

**Files:**
- Create: `diagrams/ep03-context-window.svg`
- Create: `src/audiodocs/art.py`
- Test: `tests/test_art.py`

**Interfaces:**
- Consumes: nothing
- Produces:
  - `render_png(svg_path: Path, png_path: Path, size: int = 1400) -> Path`
  - `ArtError(Exception)`

- [ ] **Step 1: Author the diagram**

`diagrams/ep03-context-window.svg` — a 1400x1400 square showing the context window
as a stacked bar: system prompt, CLAUDE.md, tool definitions, conversation history,
free space, with the cache breakpoint marked. Square because it becomes podcast
artwork. Use a fixed palette with contrast of at least 4.5:1 against the background,
and font sizes no smaller than 28px so it survives being shown at lock-screen size.

```xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1400 1400" width="1400" height="1400">
  <rect width="1400" height="1400" fill="#1a1a1a"/>
  <text x="100" y="150" fill="#f5f5f5" font-family="Helvetica, sans-serif"
        font-size="64" font-weight="600">The context window</text>
  <text x="100" y="215" fill="#9a9a9a" font-family="Helvetica, sans-serif"
        font-size="32">Everything Claude can see, all at once</text>

  <rect x="100" y="300"  width="1200" height="150" fill="#4a6fa5"/>
  <text x="130" y="392" fill="#ffffff" font-family="Helvetica, sans-serif" font-size="40">System prompt</text>

  <rect x="100" y="460"  width="1200" height="150" fill="#5a8a6f"/>
  <text x="130" y="552" fill="#ffffff" font-family="Helvetica, sans-serif" font-size="40">CLAUDE.md files</text>

  <rect x="100" y="620"  width="1200" height="150" fill="#8a7a4a"/>
  <text x="130" y="712" fill="#ffffff" font-family="Helvetica, sans-serif" font-size="40">Tool definitions</text>

  <rect x="100" y="780"  width="1200" height="330" fill="#7a5a7a"/>
  <text x="130" y="900" fill="#ffffff" font-family="Helvetica, sans-serif" font-size="40">Conversation history</text>
  <text x="130" y="955" fill="#e0d0e0" font-family="Helvetica, sans-serif" font-size="30">grows every turn</text>

  <rect x="100" y="1120" width="1200" height="120" fill="#2a2a2a" stroke="#4a4a4a" stroke-width="3"/>
  <text x="130" y="1195" fill="#8a8a8a" font-family="Helvetica, sans-serif" font-size="40">Free space</text>

  <line x1="100" y1="775" x2="1300" y2="775" stroke="#e0a030" stroke-width="6" stroke-dasharray="18 12"/>
  <text x="1300" y="760" fill="#e0a030" font-family="Helvetica, sans-serif"
        font-size="30" text-anchor="end">cache breakpoint</text>
</svg>
```

- [ ] **Step 2: Write the failing test**

`tests/test_art.py`:

```python
import pytest
from pathlib import Path
from audiodocs.art import render_png, ArtError

SVG = Path("diagrams/ep03-context-window.svg")


def test_diagram_source_exists():
    assert SVG.exists(), "the episode 03 diagram must be authored first"


def test_rejects_missing_svg(tmp_path):
    with pytest.raises(ArtError, match="no such diagram"):
        render_png(tmp_path / "nope.svg", tmp_path / "out.png")


@pytest.mark.smoke
def test_renders_a_square_png(tmp_path):
    out = render_png(SVG, tmp_path / "ep03.png", size=1400)
    assert out.exists()
    assert out.stat().st_size > 5000
    header = out.read_bytes()[:8]
    assert header == b"\x89PNG\r\n\x1a\n", "output must be a real PNG"
```

- [ ] **Step 3: Run the test to verify it fails**

Run: `python3 -m pytest tests/test_art.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'audiodocs.art'`

- [ ] **Step 4: Write the minimal implementation**

`src/audiodocs/art.py`:

```python
"""Render episode diagrams to PNG artwork using headless Chrome."""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


class ArtError(Exception):
    """Diagram rendering failed."""


def render_png(svg_path: Path, png_path: Path, size: int = 1400) -> Path:
    svg_path = Path(svg_path)
    png_path = Path(png_path)

    if not svg_path.exists():
        raise ArtError(f"no such diagram: {svg_path}")
    if not Path(CHROME).exists():
        raise ArtError(f"Chrome not found at {CHROME}")

    png_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as workdir:
        shot = Path(workdir) / "screenshot.png"
        result = subprocess.run(
            [
                CHROME,
                "--headless",
                "--disable-gpu",
                "--hide-scrollbars",
                f"--window-size={size},{size}",
                f"--screenshot={shot}",
                svg_path.resolve().as_uri(),
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if not shot.exists():
            raise ArtError(
                f"Chrome produced no screenshot: {result.stderr.strip()[:400]}"
            )
        shutil.move(str(shot), str(png_path))

    return png_path
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `python3 -m pytest tests/test_art.py -v`
Expected: 3 passed

If Chrome rejects `--headless`, use `--headless=new` — newer builds renamed the mode.

- [ ] **Step 6: Look at the rendered artwork**

```bash
PYTHONPATH=src python3 -c "
from pathlib import Path
from audiodocs.art import render_png
print(render_png(Path('diagrams/ep03-context-window.svg'), Path('out/art/ep03.png')))
"
open out/art/ep03.png
```
Expected: a legible square diagram. If text is clipped or tiny, fix the SVG now —
this image is what appears on the lock screen.

- [ ] **Step 7: Commit**

```bash
git add diagrams/ep03-context-window.svg src/audiodocs/art.py tests/test_art.py
git commit -m "feat: add episode 03 diagram and headless Chrome PNG rendering"
```

---

## Task 7: ID3 tagging with embedded artwork

**Files:**
- Create: `src/audiodocs/tag.py`
- Test: `tests/test_tag.py`

**Interfaces:**
- Consumes: nothing from earlier tasks
- Produces:
  - `tag_audio(audio_path: Path, title: str, track: int, album: str, artwork: Path | None = None) -> None`
  - `read_tags(audio_path: Path) -> dict` — for verification; returns keys `title`, `track`, `album`, `has_artwork`
  - `TagError(Exception)`

- [ ] **Step 1: Write the failing test**

`tests/test_tag.py`:

```python
import pytest
from pathlib import Path
from audiodocs.speak import synthesize
from audiodocs.art import render_png
from audiodocs.tag import tag_audio, read_tags, TagError


def test_rejects_missing_audio(tmp_path):
    with pytest.raises(TagError, match="no such audio file"):
        tag_audio(tmp_path / "nope.m4a", "Title", 3, "Album")


@pytest.mark.smoke
def test_tags_round_trip(tmp_path):
    audio = synthesize("Testing tags.", tmp_path / "ep03.m4a")
    art = render_png(Path("diagrams/ep03-context-window.svg"), tmp_path / "ep03.png")

    tag_audio(audio, "The context window", 3, "Claude Code, Narrated", artwork=art)
    tags = read_tags(audio)

    assert tags["title"] == "The context window"
    assert tags["track"] == 3
    assert tags["album"] == "Claude Code, Narrated"
    assert tags["has_artwork"] is True
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m pytest tests/test_tag.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'audiodocs.tag'`

- [ ] **Step 3: Write the minimal implementation**

Task 5 produces AAC in an MP4 container, so this uses mutagen's MP4 atoms.

`src/audiodocs/tag.py`:

```python
"""Write episode metadata and cover artwork into audio files."""
from __future__ import annotations

from pathlib import Path

from mutagen.mp4 import MP4, MP4Cover


class TagError(Exception):
    """Tagging failed."""


def tag_audio(
    audio_path: Path,
    title: str,
    track: int,
    album: str,
    artwork: Path | None = None,
) -> None:
    audio_path = Path(audio_path)
    if not audio_path.exists():
        raise TagError(f"no such audio file: {audio_path}")

    try:
        audio = MP4(str(audio_path))
    except Exception as exc:
        raise TagError(f"could not open {audio_path}: {exc}") from exc

    audio["\xa9nam"] = [title]
    audio["\xa9alb"] = [album]
    audio["trkn"] = [(track, 0)]

    if artwork is not None:
        artwork = Path(artwork)
        if not artwork.exists():
            raise TagError(f"no such artwork: {artwork}")
        audio["covr"] = [
            MP4Cover(artwork.read_bytes(), imageformat=MP4Cover.FORMAT_PNG)
        ]

    audio.save()


def read_tags(audio_path: Path) -> dict:
    audio = MP4(str(Path(audio_path)))
    return {
        "title": (audio.get("\xa9nam") or [None])[0],
        "album": (audio.get("\xa9alb") or [None])[0],
        "track": (audio.get("trkn") or [(None, 0)])[0][0],
        "has_artwork": bool(audio.get("covr")),
    }
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m pytest tests/test_tag.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add src/audiodocs/tag.py tests/test_tag.py
git commit -m "feat: add audio tagging with embedded cover artwork"
```

---

## Task 8: Orchestration and the first real episode

**Files:**
- Create: `src/audiodocs/build.py`
- Test: `tests/test_build.py`

**Interfaces:**
- Consumes: everything above
- Produces:
  - `build_episode(episode: Episode, curriculum: Curriculum, out_dir: Path) -> Path`
  - `main(argv: list[str] | None = None) -> int`

- [ ] **Step 1: Write the failing test**

`tests/test_build.py`:

```python
from pathlib import Path
from audiodocs.manifest import load_curriculum
from audiodocs.build import build_episode


def test_builds_an_episode_from_cached_inputs(tmp_path, monkeypatch):
    """Full orchestration with the network and the model stubbed out."""
    import audiodocs.build as build_module

    narration = (
        "The context window is not a filing cabinet, it is a desk. Everything "
        "Claude can see sits on it at once, and when it fills, older turns get "
        "summarized to make room for new ones."
    )

    monkeypatch.setattr(build_module, "fetch_doc",
                        lambda slug, cache_dir: f"# {slug}\n\nBody.")
    monkeypatch.setattr(build_module, "build_script",
                        lambda ep, text, cache_dir: narration)

    curriculum = load_curriculum(Path("curriculum.yaml"))
    episode = curriculum.episode(3)

    out = build_episode(episode, curriculum, tmp_path)

    assert out.exists()
    assert out.stat().st_size > 1000
    assert out.name.startswith("03-")
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m pytest tests/test_build.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'audiodocs.build'`

- [ ] **Step 3: Write the minimal implementation**

`src/audiodocs/build.py`:

```python
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

    audio = synthesize(script, out_dir / "audio" / f"{episode.slug}.m4a",
                       voice=curriculum.voice)

    artwork = None
    if episode.diagram:
        try:
            artwork = render_png(
                DIAGRAMS / f"{episode.diagram}.svg",
                out_dir / "art" / f"{episode.diagram}.png",
            )
        except ArtError as exc:
            # Audio is the primary deliverable; artwork degrades rather than fails.
            print(f"warning: artwork skipped for episode {episode.number}: {exc}",
                  file=sys.stderr)

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
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m pytest tests/test_build.py -v`
Expected: 1 passed

- [ ] **Step 5: Run the whole suite**

Run: `python3 -m pytest -v`
Expected: all tests pass

- [ ] **Step 6: Build episode 03 for real**

```bash
PYTHONPATH=src python3 -m audiodocs.build --episode 3
```
Expected: `Wrote out/audio/03-the-context-window.m4a` at several megabytes.
This is the first real model call and the first real TTS run; it will take minutes.

- [ ] **Step 7: Read the script before listening**

```bash
cat out/cache/scripts/03-the-context-window-*.txt
```
Expected: continuous prose, no markdown, no code, no URLs, opening with a
connecting sentence and closing with the exercise. **This is the artifact the
whole phase exists to evaluate.** If the narration is weak, the fix is
`NARRATION_PROMPT` in `src/audiodocs/script.py`, not the pipeline.

- [ ] **Step 8: Listen to it**

```bash
open out/audio/03-the-context-window.m4a
```
Expected: roughly 8-12 minutes of narration, with the diagram visible as
artwork in the player.

- [ ] **Step 9: Commit**

```bash
git add src/audiodocs/build.py tests/test_build.py
git commit -m "feat: add pipeline orchestration and build episode 03"
```

---

## Phase 1 exit criteria

Phase 2 begins only when all of these hold:

1. `python3 -m pytest` passes with no failures
2. `out/audio/03-the-context-window.m4a` exists, plays, and shows its diagram as artwork
3. **You have listened to the whole episode and judged the narration good enough
   to hear another 42 times.** If not, iterate on `NARRATION_PROMPT` and rebuild —
   this is far cheaper now than after 43 episodes exist.

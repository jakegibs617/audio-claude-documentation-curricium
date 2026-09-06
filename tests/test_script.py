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
    bad = GOOD + "\n\n```bash\nclaude resume\n```"
    with pytest.raises(ScriptError, match="code fence"):
        build_script(EPISODE, "body", tmp_path, runner=lambda p, s: bad)


def test_rejects_empty_output(tmp_path):
    with pytest.raises(ScriptError, match="returned nothing"):
        build_script(EPISODE, "body", tmp_path, runner=lambda p, s: "   ")


def test_caches_result(tmp_path):
    calls = []
    build_script(EPISODE, "body", tmp_path,
                 runner=lambda p, s: (calls.append(1), GOOD)[1])
    build_script(EPISODE, "body", tmp_path,
                 runner=lambda p, s: (calls.append(1), GOOD)[1])
    assert len(calls) == 1


def test_changed_source_invalidates_cache(tmp_path):
    calls = []
    build_script(EPISODE, "body one", tmp_path,
                 runner=lambda p, s: (calls.append(1), GOOD)[1])
    build_script(EPISODE, "body two", tmp_path,
                 runner=lambda p, s: (calls.append(1), GOOD)[1])
    assert len(calls) == 2


def test_cached_script_is_still_sanitized(tmp_path):
    """A script cached before the sanitizer tightened must not stay exempt."""
    ep = Episode(number=3, title="The Context Window", sources=["x"], exercise="do it")
    cache = tmp_path / "scripts"
    cache.mkdir()
    key = build_script.__globals__["_cache_key"](ep, "SOURCES", None)
    (cache / f"{ep.slug}-{key}.txt").write_text("Use the `--print` flag.")

    def never(prompt, stdin):
        raise AssertionError("model must not be called on a cache hit")

    with pytest.raises(ScriptError) as exc:
        build_script(ep, "SOURCES", cache, runner=never)
    assert "--print" in str(exc.value)


def test_editing_the_prompt_invalidates_the_cache(tmp_path):
    """INTENT.md: the fix is always the prompt. A prompt edit must actually rebuild."""
    import audiodocs.script as script_mod

    ep = Episode(number=3, title="The Context Window", sources=["x"], exercise="do it")
    calls = []

    def runner(prompt, stdin):
        calls.append(prompt)
        return "Clean narration that says nothing unspeakable at all."

    original = script_mod.NARRATION_PROMPT
    try:
        build_script(ep, "SOURCES", tmp_path, runner=runner)
        script_mod.NARRATION_PROMPT = original + "\nAlways mention the weather. {title}{exercise}"
        build_script(ep, "SOURCES", tmp_path, runner=runner)
    finally:
        script_mod.NARRATION_PROMPT = original

    assert len(calls) == 2, "prompt changed but the cache was reused"


def test_rejected_script_is_kept_for_inspection(tmp_path):
    """A rejection costs a model call; discarding the evidence costs another."""
    ep = Episode(number=3, title="The Context Window", sources=["x"], exercise="do it")

    with pytest.raises(ScriptError):
        build_script(ep, "SOURCES", tmp_path, runner=lambda p, s: "Use --print now.")

    rejected = list(tmp_path.glob("*.rejected.txt"))
    assert rejected, "rejected script was discarded"
    assert "--print" in rejected[0].read_text()


def test_tightening_the_sanitizer_invalidates_cached_scripts(tmp_path, monkeypatch):
    """A cache key that ignores the rules wedges an episode permanently.

    Tighten the sanitizer and an old cached script stays key-valid but
    content-rejected: every rebuild raises, the model is never re-called, and
    the error names the rejected copy rather than the cache file to delete.
    """
    import audiodocs.sanitize as sanitize_mod
    import audiodocs.script as script_mod

    ep = Episode(number=3, title="The Context Window", sources=["x"], exercise="do it")
    calls = []

    def runner(prompt, stdin):
        calls.append(prompt)
        return "Clean narration with nothing unspeakable in it at all."

    build_script(ep, "SOURCES", tmp_path, runner=runner)
    assert len(calls) == 1

    monkeypatch.setattr(sanitize_mod, "RULES_FINGERPRINT", "a-stricter-sanitizer")
    build_script(ep, "SOURCES", tmp_path, runner=runner)

    assert len(calls) == 2, "sanitizer changed but the old cache key still matched"


def test_the_prompt_names_the_actual_previous_episode(tmp_path):
    """Told to connect to the previous episode but not which one it was, the
    model invents a plausible one. Across 43 episodes that is a course that
    continually misremembers itself."""
    ep = Episode(number=4, title="Prompt caching", sources=["x"], exercise="do it")
    seen = []

    build_script(
        ep, "SOURCES", tmp_path,
        runner=lambda p, s: seen.append(p) or "Clean narration, nothing unspeakable.",
        previous_title="The context window",
    )
    assert "The context window" in seen[0]


def test_the_first_episode_is_told_to_open_cold(tmp_path):
    """Episode 1 has no previous episode, and saying "last time" in the opening
    line of the first episode is the worst possible first impression."""
    ep = Episode(number=1, title="What it is called", sources=["x"], exercise="do it")
    seen = []

    build_script(
        ep, "SOURCES", tmp_path,
        runner=lambda p, s: seen.append(p) or "Clean narration, nothing unspeakable.",
        previous_title=None,
    )
    assert "first episode" in seen[0].lower()


def test_the_previous_episode_is_part_of_the_cache_key(tmp_path):
    """Reordering the curriculum changes every opening line."""
    ep = Episode(number=4, title="Prompt caching", sources=["x"], exercise="do it")
    calls = []
    runner = lambda p, s: calls.append(p) or "Clean narration, nothing unspeakable."

    build_script(ep, "SOURCES", tmp_path, runner=runner, previous_title="A")
    build_script(ep, "SOURCES", tmp_path, runner=runner, previous_title="B")
    assert len(calls) == 2

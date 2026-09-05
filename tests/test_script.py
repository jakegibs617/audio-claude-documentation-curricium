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


def test_narration_prompt_forbids_code_and_urls():
    assert "code" in NARRATION_PROMPT.lower()
    assert "url" in NARRATION_PROMPT.lower()

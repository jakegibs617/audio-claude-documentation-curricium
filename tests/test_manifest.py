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


def test_episode_slug_is_filesystem_safe(tmp_path):
    c = load_curriculum(write(tmp_path, VALID))
    assert c.episodes[0].slug == "03-the-context-window"

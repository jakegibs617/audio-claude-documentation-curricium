import pytest
from pathlib import Path
from audiodocs.manifest import load_curriculum, ManifestError

REPO_ROOT = Path(__file__).resolve().parent.parent
REAL_CURRICULUM = REPO_ROOT / "curriculum.yaml"
DIAGRAMS_DIR = REPO_ROOT / "diagrams"


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


def test_real_curriculum_has_exactly_43_episodes():
    c = load_curriculum(REAL_CURRICULUM)
    assert len(c.episodes) == 43


def test_real_curriculum_episode_numbers_are_1_to_43_with_no_gaps():
    c = load_curriculum(REAL_CURRICULUM)
    numbers = sorted(ep.number for ep in c.episodes)
    assert numbers == list(range(1, 44))


def test_real_curriculum_every_episode_has_exercise_and_source():
    c = load_curriculum(REAL_CURRICULUM)
    for ep in c.episodes:
        assert ep.exercise and ep.exercise.strip(), f"episode {ep.number} has no exercise"
        assert len(ep.sources) >= 1, f"episode {ep.number} has no sources"


def test_only_episode_3_declares_a_diagram_and_its_svg_exists():
    c = load_curriculum(REAL_CURRICULUM)
    diagrammed = [ep for ep in c.episodes if ep.diagram]
    assert [ep.number for ep in diagrammed] == [3]
    for ep in diagrammed:
        svg_path = DIAGRAMS_DIR / f"{ep.diagram}.svg"
        assert svg_path.exists(), f"missing diagram file: {svg_path}"

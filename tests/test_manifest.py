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
pace: 165
cast:
  narrator: af_heart
  tradeoff: bf_emma
  exercise: am_michael
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
    assert c.cast["narrator"] == "af_heart"
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


def test_every_exercise_in_the_real_curriculum_is_speakable():
    """Exercises are interpolated into the narration prompt and the model is told
    to close on them. An unspeakable exercise asks the model to produce exactly
    what the sanitizer will reject -- after a paid call."""
    from audiodocs.sanitize import find_violations

    curriculum = load_curriculum(Path("curriculum.yaml"))
    bad = {e.number: find_violations(e.exercise) for e in curriculum.episodes}
    assert not {n: v for n, v in bad.items() if v}


def test_unspeakable_exercise_is_a_manifest_error(tmp_path):
    """Catch it at load, in microseconds, not per-episode after payment."""
    path = tmp_path / "c.yaml"
    path.write_text(
        "album: A\npace: 165\ncast:\n  narrator: af_heart\n  tradeoff: bf_emma\n  exercise: am_michael\nepisodes:\n"
        "  - number: 1\n    title: T\n    sources: [x]\n"
        "    exercise: Run ls -R and look at it.\n"
    )
    with pytest.raises(ManifestError) as exc:
        load_curriculum(path)
    assert "-R" in str(exc.value)


def _yaml(tmp_path, body):
    path = tmp_path / "c.yaml"
    path.write_text(body)
    return path


CAST_BODY = (
    "album: A\npace: 165\n"
    "cast:\n  narrator: af_heart\n  tradeoff: bf_emma\n  exercise: am_michael\n"
    "episodes:\n  - number: 1\n    title: T\n    sources: [x]\n"
    "    exercise: Open a session and look at what loaded.\n"
)


def test_loads_the_cast_and_pace(tmp_path):
    c = load_curriculum(_yaml(tmp_path, CAST_BODY))
    assert c.cast == {"narrator": "af_heart", "tradeoff": "bf_emma",
                      "exercise": "am_michael"}
    assert c.pace == 165


def test_a_cast_missing_a_role_is_an_error(tmp_path):
    """A script can label any role, so every role needs a voice before the
    build starts -- not partway through episode 9."""
    body = CAST_BODY.replace("  exercise: am_michael\n", "")
    with pytest.raises(ManifestError) as exc:
        load_curriculum(_yaml(tmp_path, body))
    assert "exercise" in str(exc.value)


def test_an_unknown_cast_role_is_an_error(tmp_path):
    body = CAST_BODY.replace("  tradeoff: bf_emma", "  tradeof: bf_emma")
    with pytest.raises(ManifestError) as exc:
        load_curriculum(_yaml(tmp_path, body))
    assert "tradeof" in str(exc.value)


def test_the_real_curriculum_defines_a_full_cast():
    c = load_curriculum(Path("curriculum.yaml"))
    from audiodocs.segments import ROLES

    assert set(c.cast) == set(ROLES)
    assert 140 <= c.pace <= 200

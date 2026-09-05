from pathlib import Path
from audiodocs.manifest import load_curriculum
from audiodocs.build import build_episode
from audiodocs.tag import read_tags


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

    tags = read_tags(out)
    assert tags["title"] == "The context window"
    assert tags["track"] == 3
    assert tags["has_artwork"] is True

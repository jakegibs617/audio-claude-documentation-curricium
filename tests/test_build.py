from pathlib import Path
from audiodocs.manifest import load_curriculum
from audiodocs.build import build_episode
from audiodocs.tag import read_tags


def _stub_pipeline(monkeypatch, build_module, fail_titles=None):
    """Stub fetch/script/speak/art/tag so build_episode never touches the
    network, the model, TTS, or Chrome. Returns the list of paths passed to
    the synthesize stub, so tests can assert whether TTS actually ran.
    """
    fail_titles = fail_titles or set()

    def fake_build_script(ep, text, cache_dir):
        if ep.title in fail_titles:
            raise RuntimeError(f"synthetic failure for {ep.title}")
        return "Narration text, long enough, with no code or urls in it."

    synth_calls: list[Path] = []

    def fake_synthesize(text, out_path, voice="Samantha"):
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(b"fake-audio-bytes")
        synth_calls.append(out_path)
        return out_path

    def fake_render_png(svg_path, png_path, size=1400):
        png_path = Path(png_path)
        png_path.parent.mkdir(parents=True, exist_ok=True)
        png_path.write_bytes(b"fake-png-bytes")
        return png_path

    monkeypatch.setattr(
        build_module, "fetch_doc", lambda slug, cache_dir: f"# {slug}\n\nBody."
    )
    monkeypatch.setattr(build_module, "build_script", fake_build_script)
    monkeypatch.setattr(build_module, "synthesize", fake_synthesize)
    monkeypatch.setattr(build_module, "render_png", fake_render_png)
    monkeypatch.setattr(build_module, "tag_audio", lambda *a, **k: None)

    return synth_calls


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


def test_batch_build_isolates_one_failure(tmp_path, monkeypatch):
    """One episode raising must not abort the batch; the others still build
    and the report marks exactly the broken one as failed."""
    import audiodocs.build as build_module

    _stub_pipeline(monkeypatch, build_module, fail_titles={"Prompt caching"})

    curriculum = load_curriculum(Path("curriculum.yaml"))
    report = build_module.build_all(curriculum, tmp_path, only=[2, 3, 4])

    assert report.ok is False
    assert len(report.failed) == 1
    assert report.failed[0].number == 4
    assert "synthetic failure" in report.failed[0].error
    assert {r.number for r in report.built} == {2, 3}


def test_cached_episode_is_reported_cached_not_rebuilt(tmp_path, monkeypatch):
    """An episode whose audio file already exists must be skipped, not
    resynthesized, and reported as cached."""
    import audiodocs.build as build_module

    synth_calls = _stub_pipeline(monkeypatch, build_module)

    curriculum = load_curriculum(Path("curriculum.yaml"))
    episode = curriculum.episode(4)
    existing = tmp_path / "audio" / f"{episode.slug}.m4a"
    existing.parent.mkdir(parents=True)
    existing.write_bytes(b"already built")

    report = build_module.build_all(curriculum, tmp_path, only=[4])

    assert len(report.results) == 1
    assert report.results[0].status == "cached"
    assert report.results[0].path == existing
    assert synth_calls == []
    assert report.ok is True


def test_only_builds_the_requested_episode(tmp_path, monkeypatch):
    import audiodocs.build as build_module

    _stub_pipeline(monkeypatch, build_module)

    curriculum = load_curriculum(Path("curriculum.yaml"))
    report = build_module.build_all(curriculum, tmp_path, only=[3])

    assert [r.number for r in report.results] == [3]
    assert report.results[0].status == "built"
    assert report.results[0].path.exists()


def test_format_report_names_failed_episode_and_error(tmp_path, monkeypatch):
    import audiodocs.build as build_module

    _stub_pipeline(
        monkeypatch, build_module, fail_titles={"Inside the .claude directory"}
    )

    curriculum = load_curriculum(Path("curriculum.yaml"))
    report = build_module.build_all(curriculum, tmp_path, only=[5])

    text = build_module.format_report(report)

    assert "5" in text
    assert "Inside the .claude directory" in text
    assert "synthetic failure" in text
    # Failures should be unmissable, not buried in a plain list.
    assert "FAIL" in text.upper()


def test_main_all_returns_nonzero_on_failure(tmp_path, monkeypatch):
    import audiodocs.build as build_module

    _stub_pipeline(monkeypatch, build_module, fail_titles={"Prompt caching"})

    exit_code = build_module.main(["--all", "--out", str(tmp_path)])

    assert exit_code != 0


def test_main_all_returns_zero_when_everything_builds(tmp_path, monkeypatch):
    import audiodocs.build as build_module

    _stub_pipeline(monkeypatch, build_module)

    exit_code = build_module.main(["--all", "--out", str(tmp_path)])

    assert exit_code == 0


def test_main_episode_flag_can_repeat(tmp_path, monkeypatch):
    import audiodocs.build as build_module

    _stub_pipeline(monkeypatch, build_module)

    exit_code = build_module.main(
        ["--episode", "2", "--episode", "4", "--out", str(tmp_path)]
    )

    assert exit_code == 0
    assert (tmp_path / "audio" / "02-how-claude-code-actually-works.m4a").exists()
    assert (tmp_path / "audio" / "04-prompt-caching.m4a").exists()
    assert not (tmp_path / "audio" / "05-inside-the-claude-directory.m4a").exists()

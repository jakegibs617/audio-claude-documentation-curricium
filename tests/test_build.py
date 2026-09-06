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
        return f"Narration text, long enough, with no code or urls in it. {ep.exercise}"

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


def test_audio_of_unknown_provenance_is_rebuilt_not_trusted(tmp_path, monkeypatch):
    """A stray .m4a is not evidence the episode is current.

    Only a stamp matching the script that would be generated now proves that.
    An unstamped file could be a half-written run, a hand-copied file, or audio
    from a curriculum edit ago -- rebuilding costs seconds, trusting it wrongly
    means shipping the wrong narration forever.
    """
    import audiodocs.build as build_module

    synth_calls = _stub_pipeline(monkeypatch, build_module)

    curriculum = load_curriculum(Path("curriculum.yaml"))
    episode = curriculum.episode(4)
    existing = tmp_path / "audio" / f"{episode.slug}.m4a"
    existing.parent.mkdir(parents=True)
    existing.write_bytes(b"already built, but by what?")

    report = build_module.build_all(curriculum, tmp_path, only=[4])

    assert report.results[0].status == "built"
    assert synth_calls == [existing]
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


def test_edited_exercise_rebuilds_stale_audio(tmp_path, monkeypatch):
    """INTENT.md: regenerable, not precious. Nothing in out/ is protected.

    Existence of the .m4a is not proof it is current. Edit an episode's exercise
    or the narration prompt -- same number, same title, same slug, same path --
    and the old audio must be replaced, not preserved forever with no way to
    force it short of deleting files by hand.
    """
    import audiodocs.build as build_module
    from dataclasses import replace

    synth_calls = _stub_pipeline(monkeypatch, build_module)
    curriculum = load_curriculum(Path("curriculum.yaml"))

    build_module.build_all(curriculum, tmp_path, only=[3])
    assert len(synth_calls) == 1

    edited = replace(curriculum.episode(3), exercise="a completely different exercise")
    curriculum2 = replace(curriculum, episodes=[edited])
    report = build_module.build_all(curriculum2, tmp_path, only=[3])

    assert len(synth_calls) == 2, "stale audio was kept after the exercise changed"
    assert len(report.built) == 1


def test_unchanged_episode_is_still_reported_cached(tmp_path, monkeypatch):
    """The staleness check must not cost a resynthesis when nothing moved."""
    import audiodocs.build as build_module

    synth_calls = _stub_pipeline(monkeypatch, build_module)
    curriculum = load_curriculum(Path("curriculum.yaml"))

    build_module.build_all(curriculum, tmp_path, only=[3])
    report = build_module.build_all(curriculum, tmp_path, only=[3])

    assert len(synth_calls) == 1
    assert len(report.cached) == 1


def test_chrome_hanging_degrades_rather_than_aborting(tmp_path, monkeypatch):
    """A headless Chrome that hangs raises TimeoutExpired, not ArtError -- and a
    hang is the canonical Chrome failure. If the documented artwork degradation
    does not cover it, one stuck render kills a 43-episode run."""
    import subprocess

    import audiodocs.build as build_module

    _stub_pipeline(monkeypatch, build_module)
    monkeypatch.setattr(
        build_module,
        "render_png",
        lambda *a, **k: (_ for _ in ()).throw(
            subprocess.TimeoutExpired(cmd="chrome", timeout=120)
        ),
    )

    curriculum = load_curriculum(Path("curriculum.yaml"))
    report = build_module.build_all(curriculum, tmp_path, only=[3])

    assert report.ok is True
    assert report.results[0].status == "built"


def test_build_all_writes_a_feed(tmp_path, monkeypatch):
    """The feed is the delivery mechanism; a build that does not emit one leaves
    the audio unreachable from a phone."""
    import xml.etree.ElementTree as ET

    import audiodocs.build as build_module

    _stub_pipeline(monkeypatch, build_module)
    rc = build_module.main(
        [
            "--curriculum", "curriculum.yaml",
            "--out", str(tmp_path),
            "--episode", "3",
            "--base-url", "https://example.test/audio/",
        ]
    )

    assert rc == 0
    feed = tmp_path / "feed.xml"
    assert feed.exists()
    channel = ET.parse(feed).getroot().find("channel")
    assert len(channel.findall("item")) == 1


def test_a_bad_voice_fails_before_any_model_call(tmp_path, monkeypatch):
    """The voice check lived inside synthesize, which runs after the model call.
    One typo in curriculum.yaml burned all 43 calls for zero audio."""
    import audiodocs.build as build_module

    _stub_pipeline(monkeypatch, build_module)
    monkeypatch.setattr(build_module, "available_voices", lambda: ("Samantha",))

    calls = []
    real = build_module.build_script
    monkeypatch.setattr(
        build_module, "build_script", lambda *a: calls.append(1) or real(*a)
    )

    rc = build_module.main(
        ["--curriculum", str(_curriculum_with_voice(tmp_path, "Samanthaa")),
         "--out", str(tmp_path), "--all"]
    )
    assert rc == 1
    assert calls == [], "the model was called despite an unusable voice"


def _curriculum_with_voice(tmp_path, voice):
    path = tmp_path / "c.yaml"
    path.write_text(
        f"album: A\nvoice: {voice}\nepisodes:\n"
        "  - number: 1\n    title: T\n    sources: [overview]\n"
        "    exercise: Open a session and look at what loaded.\n"
    )
    return path


def test_failures_are_reported_as_they_happen(tmp_path, monkeypatch, capsys):
    """Progress output exists so a hang is distinguishable from work. If failures
    only surface in the final summary, a totally failing hour-long build looks
    exactly like a healthy one until it ends."""
    import audiodocs.build as build_module

    _stub_pipeline(monkeypatch, build_module, fail_titles={"Prompt caching"})
    curriculum = load_curriculum(Path("curriculum.yaml"))
    build_module.build_all(curriculum, tmp_path, only=[2, 4])

    assert "FAILED" in capsys.readouterr().err


def test_a_changed_diagram_rebuilds_the_episode(tmp_path, monkeypatch):
    """INTENT.md names diagrams as a kept asset. If the stamp ignores them, an
    edited diagram never reaches the audio it is embedded in."""
    import audiodocs.build as build_module

    synth_calls = _stub_pipeline(monkeypatch, build_module)
    curriculum = load_curriculum(Path("curriculum.yaml"))
    svg = Path("diagrams/ep03-context-window.svg")

    monkeypatch.setattr(build_module, "_diagram_fingerprint", lambda ep: "first")
    build_module.build_all(curriculum, tmp_path, only=[3])
    monkeypatch.setattr(build_module, "_diagram_fingerprint", lambda ep: "edited")
    report = build_module.build_all(curriculum, tmp_path, only=[3])

    assert len(synth_calls) == 2, "edited diagram left the old episode in place"
    assert len(report.built) == 1


def test_a_failed_episode_is_not_advertised_in_the_feed(tmp_path, monkeypatch):
    """synthesize writes the .m4a before tagging. If tagging fails, the audio is
    on disk but incomplete -- the feed must not enclose it."""
    import xml.etree.ElementTree as ET

    import audiodocs.build as build_module

    _stub_pipeline(monkeypatch, build_module)
    monkeypatch.setattr(
        build_module,
        "tag_audio",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("tagging blew up")),
    )

    rc = build_module.main(
        ["--curriculum", "curriculum.yaml", "--out", str(tmp_path),
         "--episode", "3", "--base-url", "https://x.test/a/"]
    )

    assert rc == 1
    channel = ET.parse(tmp_path / "feed.xml").getroot().find("channel")
    assert channel.findall("item") == [], "feed advertised a failed episode"


def test_unknown_episode_number_is_an_error_not_a_traceback(tmp_path, monkeypatch):
    import audiodocs.build as build_module

    _stub_pipeline(monkeypatch, build_module)
    rc = build_module.main(
        ["--curriculum", "curriculum.yaml", "--out", str(tmp_path), "--episode", "99"]
    )
    assert rc == 1

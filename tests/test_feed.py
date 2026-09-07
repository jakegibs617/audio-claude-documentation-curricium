import shutil
import subprocess
from pathlib import Path
import xml.etree.ElementTree as ET

import pytest

from audiodocs.manifest import Curriculum, Episode, load_curriculum
from audiodocs.feed import build_feed, FeedError

ITUNES_NS = "http://www.itunes.com/dtds/podcast-1.0.dtd"


def qn(tag: str) -> str:
    return f"{{{ITUNES_NS}}}{tag}"


def make_curriculum(episodes):
    return Curriculum(
        album="Claude Code, Narrated",
        cast={"narrator": "af_heart", "tradeoff": "bf_emma",
              "exercise": "am_michael"},
        pace=165,
        episodes=episodes,
    )


# Deliberately out of number order, and one episode ("9") is never built.
EPISODES = [
    Episode(number=5, title="Fifth Episode", sources=["x"], exercise="do a thing"),
    Episode(number=2, title="Second Episode", sources=["x"], exercise="do a thing"),
    Episode(number=9, title="Never Built", sources=["x"], exercise="do a thing"),
]


def write_fake_audio(audio_dir, episode, size=1234):
    audio_dir.mkdir(parents=True, exist_ok=True)
    path = audio_dir / f"{episode.slug}.m4a"
    path.write_bytes(b"\x00" * size)
    return path


def build_populated_feed(tmp_path, base_url="https://example.com/audio"):
    audio_dir = tmp_path / "audio"
    write_fake_audio(audio_dir, EPISODES[0], size=1111)
    write_fake_audio(audio_dir, EPISODES[1], size=2222)
    # EPISODES[2] ("Never Built") intentionally has no file.
    curriculum = make_curriculum(EPISODES)
    out_path = tmp_path / "feed.xml"
    build_feed(curriculum, audio_dir, out_path, base_url)
    return curriculum, audio_dir, out_path


def test_feed_is_well_formed_xml(tmp_path):
    _, _, out_path = build_populated_feed(tmp_path)
    tree = ET.parse(out_path)
    root = tree.getroot()
    assert root.tag == "rss"


def test_channel_title_comes_from_album(tmp_path):
    _, _, out_path = build_populated_feed(tmp_path)
    root = ET.parse(out_path).getroot()
    title = root.find("channel/title")
    assert title is not None
    assert title.text == "Claude Code, Narrated"


def test_only_built_episodes_get_items(tmp_path):
    _, _, out_path = build_populated_feed(tmp_path)
    root = ET.parse(out_path).getroot()
    items = root.findall("channel/item")
    assert len(items) == 2
    titles = {item.find("title").text for item in items}
    assert titles == {"Fifth Episode", "Second Episode"}
    assert "Never Built" not in titles


def test_items_ordered_by_episode_number_ascending(tmp_path):
    _, _, out_path = build_populated_feed(tmp_path)
    root = ET.parse(out_path).getroot()
    items = root.findall("channel/item")
    numbers = [int(item.find(qn("episode")).text) for item in items]
    assert numbers == sorted(numbers)
    assert numbers == [2, 5]


def test_enclosure_length_and_type(tmp_path):
    _, audio_dir, out_path = build_populated_feed(tmp_path)
    root = ET.parse(out_path).getroot()
    for item in root.findall("channel/item"):
        title = item.find("title").text
        enclosure = item.find("enclosure")
        assert enclosure.get("type") == "audio/mp4"
        slug = "02-second-episode" if title == "Second Episode" else "05-fifth-episode"
        real_size = (audio_dir / f"{slug}.m4a").stat().st_size
        assert int(enclosure.get("length")) == real_size


def test_base_url_with_and_without_trailing_slash_match(tmp_path):
    _, _, out_a = build_populated_feed(tmp_path / "a", base_url="https://example.com/audio")
    (tmp_path / "b").mkdir()
    audio_dir_b = tmp_path / "b" / "audio"
    write_fake_audio(audio_dir_b, EPISODES[0], size=1111)
    write_fake_audio(audio_dir_b, EPISODES[1], size=2222)
    curriculum = make_curriculum(EPISODES)
    out_b = tmp_path / "b" / "feed.xml"
    build_feed(curriculum, audio_dir_b, out_b, base_url="https://example.com/audio/")

    urls_a = sorted(
        item.find("enclosure").get("url")
        for item in ET.parse(out_a).getroot().findall("channel/item")
    )
    urls_b = sorted(
        item.find("enclosure").get("url")
        for item in ET.parse(out_b).getroot().findall("channel/item")
    )
    assert urls_a == urls_b
    for url in urls_a:
        assert "//audio/" not in url.split("://", 1)[1]  # no doubled slash after join


def test_guids_are_unique(tmp_path):
    _, _, out_path = build_populated_feed(tmp_path)
    root = ET.parse(out_path).getroot()
    guids = [item.find("guid").text for item in root.findall("channel/item")]
    assert len(guids) == len(set(guids))


def test_guids_are_stable_across_rebuilds(tmp_path):
    audio_dir = tmp_path / "audio"
    write_fake_audio(audio_dir, EPISODES[0])
    write_fake_audio(audio_dir, EPISODES[1])
    curriculum = make_curriculum(EPISODES)

    out1 = tmp_path / "feed1.xml"
    out2 = tmp_path / "feed2.xml"
    build_feed(curriculum, audio_dir, out1, "https://example.com/audio")
    build_feed(curriculum, audio_dir, out2, "https://example.com/audio")

    guids1 = sorted(item.find("guid").text for item in ET.parse(out1).getroot().findall("channel/item"))
    guids2 = sorted(item.find("guid").text for item in ET.parse(out2).getroot().findall("channel/item"))
    assert guids1 == guids2


def test_duration_omitted_when_unreadable(tmp_path):
    """Fake .m4a files are not real audio, so mutagen can't read a duration.
    The feed must still be produced, just without itunes:duration on that item."""
    _, _, out_path = build_populated_feed(tmp_path)
    root = ET.parse(out_path).getroot()
    for item in root.findall("channel/item"):
        assert item.find(qn("duration")) is None


def test_missing_audio_dir_raises_feed_error(tmp_path):
    curriculum = make_curriculum(EPISODES)
    with pytest.raises(FeedError):
        build_feed(curriculum, tmp_path / "nonexistent", tmp_path / "feed.xml", "https://example.com/audio")


def test_itunes_namespace_is_declared(tmp_path):
    _, _, out_path = build_populated_feed(tmp_path)
    text = out_path.read_text()
    assert 'xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd"' in text


@pytest.mark.smoke
def test_duration_is_read_from_a_real_audio_file(tmp_path):
    if shutil.which("say") is None or shutil.which("afconvert") is None:
        pytest.skip("say/afconvert not available")

    audio_dir = tmp_path / "audio"
    audio_dir.mkdir()
    episode = Episode(number=1, title="Real Audio Episode", sources=["x"], exercise="listen")
    aiff = tmp_path / "speech.aiff"
    m4a = audio_dir / f"{episode.slug}.m4a"
    subprocess.run(["say", "-o", str(aiff), "Testing one two three."], check=True)
    subprocess.run(
        ["afconvert", "-f", "m4af", "-d", "aac", "-b", "64000", str(aiff), str(m4a)],
        check=True,
    )

    curriculum = make_curriculum([episode])
    out_path = tmp_path / "feed.xml"
    build_feed(curriculum, audio_dir, out_path, "https://example.com/audio")

    root = ET.parse(out_path).getroot()
    item = root.find("channel/item")
    duration_el = item.find(qn("duration"))
    assert duration_el is not None
    assert duration_el.text
    # Format is either "M:SS" or "H:MM:SS" — just sanity check it parses as such.
    parts = duration_el.text.split(":")
    assert 2 <= len(parts) <= 3
    assert all(p.isdigit() for p in parts)


RSS2_REQUIRED = ("title", "link", "description")


def _channel(tmp_path, audio_dir):
    curriculum = load_curriculum(Path("curriculum.yaml"))
    out = build_feed(curriculum, audio_dir, tmp_path / "feed.xml", "https://x.test/a/")
    return ET.parse(out).getroot().find("channel")


def test_channel_has_every_rss2_required_element(tmp_path):
    """RSS 2.0 requires title, link, and description on <channel>.
    A feed missing them is rejected outright by strict readers."""
    audio = tmp_path / "audio"
    audio.mkdir()
    channel = _channel(tmp_path, audio)
    for tag in RSS2_REQUIRED:
        assert channel.find(tag) is not None, f"<channel> missing <{tag}>"
        assert (channel.find(tag).text or "").strip(), f"<{tag}> is empty"


def test_items_carry_pubdate_in_episode_order(tmp_path):
    """Podcast apps order by pubDate, not itunes:episode. Without it a
    sequenced course arrives shuffled, which defeats the whole point."""
    from email.utils import parsedate_to_datetime

    audio = tmp_path / "audio"
    audio.mkdir()
    curriculum = load_curriculum(Path("curriculum.yaml"))
    for number in (1, 2, 3):
        (audio / f"{curriculum.episode(number).slug}.m4a").write_bytes(b"x")

    channel = _channel(tmp_path, audio)
    dates = [
        parsedate_to_datetime(item.find("pubDate").text)
        for item in channel.findall("item")
    ]
    assert len(dates) == 3
    assert dates == sorted(dates), "episode 1 must be the oldest, so apps play it first"


def test_feed_is_byte_stable_across_rebuilds(tmp_path):
    """A pubDate derived from the clock would rewrite every guid's date on each
    build and re-notify subscribers about episodes they already have."""
    audio = tmp_path / "audio"
    audio.mkdir()
    curriculum = load_curriculum(Path("curriculum.yaml"))
    (audio / f"{curriculum.episode(1).slug}.m4a").write_bytes(b"x")

    first = build_feed(curriculum, audio, tmp_path / "a.xml", "https://x.test/a/")
    second = build_feed(curriculum, audio, tmp_path / "b.xml", "https://x.test/a/")
    assert first.read_bytes() == second.read_bytes()

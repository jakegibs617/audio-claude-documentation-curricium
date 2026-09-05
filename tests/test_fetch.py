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


def test_stale_cache_is_refetched(tmp_path):
    """INTENT.md: the docs change weekly and a rebuild redoes what moved.
    A cache keyed on slug alone with no expiry returns 2026's copy forever."""
    import os
    import time

    calls = []

    def opener(url):
        calls.append(url)
        return f"VERSION {len(calls)}"

    assert fetch_doc("overview", tmp_path, opener=opener) == "VERSION 1"
    assert fetch_doc("overview", tmp_path, opener=opener) == "VERSION 1"

    cached = tmp_path / "overview.md"
    old = time.time() - 60 * 60 * 24 * 7
    os.utime(cached, (old, old))

    assert fetch_doc("overview", tmp_path, opener=opener) == "VERSION 2"


def test_network_failure_falls_back_to_the_stale_copy(tmp_path):
    """Being offline should not stop a rebuild of already-fetched docs."""
    import os
    import time

    fetch_doc("overview", tmp_path, opener=lambda url: "CACHED BODY")
    cached = tmp_path / "overview.md"
    old = time.time() - 60 * 60 * 24 * 7
    os.utime(cached, (old, old))

    def offline(url):
        raise FetchError("no network")

    assert fetch_doc("overview", tmp_path, opener=offline) == "CACHED BODY"

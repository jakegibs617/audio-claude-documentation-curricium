import pytest
from audiodocs.fetch import OfflineError, doc_url, fetch_doc, FetchError


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
        raise OfflineError("no network")

    assert fetch_doc("overview", tmp_path, opener=offline) == "CACHED BODY"


def test_a_deleted_page_is_not_masked_by_a_stale_cache(tmp_path):
    """The spec: a slug that 404s is reported, not silently skipped.

    Being unreachable and being deleted look identical to a bare except, and
    the second one means the manifest is now wrong.
    """
    import os
    import time

    fetch_doc("gone", tmp_path, opener=lambda url: "OLD BODY")
    cached = tmp_path / "gone.md"
    old = time.time() - 60 * 60 * 24 * 7
    os.utime(cached, (old, old))

    def deleted(url):
        raise FetchError(f"{url} returned HTTP 404")

    with pytest.raises(FetchError):
        fetch_doc("gone", tmp_path, opener=deleted)


def test_a_programming_error_is_not_swallowed(tmp_path):
    """A mis-signatured opener must surface, not quietly serve stale bytes."""
    import os
    import time

    fetch_doc("overview", tmp_path, opener=lambda url: "OLD BODY")
    cached = tmp_path / "overview.md"
    old = time.time() - 60 * 60 * 24 * 7
    os.utime(cached, (old, old))

    with pytest.raises(TypeError):
        fetch_doc("overview", tmp_path, opener=lambda url, extra: "x")


def test_offline_fallback_does_not_re_pay_the_timeout(tmp_path):
    """93 unique slugs times a 30s timeout is 46 minutes of dead waiting."""
    import os
    import time

    fetch_doc("overview", tmp_path, opener=lambda url: "BODY")
    cached = tmp_path / "overview.md"
    old = time.time() - 60 * 60 * 24 * 7
    os.utime(cached, (old, old))

    calls = []

    def offline(url):
        calls.append(url)
        raise OfflineError("no network")

    fetch_doc("overview", tmp_path, opener=offline)
    fetch_doc("overview", tmp_path, opener=offline)
    assert len(calls) == 1, "the stale copy was not refreshed after falling back"

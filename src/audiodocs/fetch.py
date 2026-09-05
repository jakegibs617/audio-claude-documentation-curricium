"""Retrieve documentation pages as markdown, cached on disk."""
from __future__ import annotations

import urllib.error
import urllib.request
from pathlib import Path

BASE = "https://code.claude.com/docs/en"
USER_AGENT = "audiodocs/0.1 (personal learning curriculum builder)"


class FetchError(Exception):
    """A documentation page could not be retrieved."""


def doc_url(slug: str) -> str:
    return f"{BASE}/{slug}.md"


def _default_opener(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        raise FetchError(f"{url} returned HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise FetchError(f"{url} unreachable: {exc.reason}") from exc


def fetch_doc(slug: str, cache_dir: Path, opener=None) -> str:
    """Return the markdown for `slug`, fetching only on a cache miss."""
    cache_dir = Path(cache_dir)
    cached = cache_dir / f"{slug.replace('/', '__')}.md"

    if cached.exists():
        return cached.read_text()

    text = (opener or _default_opener)(doc_url(slug))
    if not text.strip():
        raise FetchError(f"{doc_url(slug)} returned an empty response")

    cached.parent.mkdir(parents=True, exist_ok=True)
    cached.write_text(text)
    return text

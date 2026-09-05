"""Detect content that must never reach a text-to-speech engine.

A narration script is meant to be heard. Code fences, bare URLs, tables, and
references to things the listener cannot see are all failures of the rewrite
step. This module names them; it never silently repairs them.
"""
from __future__ import annotations

import re

CODE_FENCE = re.compile(r"```")
BARE_URL = re.compile(r"https?://\S+")
TABLE_ROW = re.compile(r"^\s*\|.*\|\s*$", re.MULTILINE)

# Deliberately narrow. A bare "above" is ordinary English ("the layer above the
# model"); only a reference pointing at content the listener cannot see counts.
DANGLING = re.compile(
    r"\b(?:"
    r"as (?:shown|seen|described|listed) (?:above|below)"
    r"|see the \w+ (?:above|below)"
    r"|in the \w+ (?:above|below)"
    r"|the (?:table|diagram|example|list|code|figure|snippet|section) (?:above|below)"
    r")\b",
    re.IGNORECASE,
)

# Requires a word boundary before the dash so hyphenated compounds such as
# "well-defined" and "trade-offs" are not mistaken for command flags.
COMMAND_FLAG = re.compile(r"(?:^|\s)--?[a-zA-Z][\w-]*")


class UnspeakableError(Exception):
    """A script contains content that cannot be spoken aloud."""


def find_violations(text: str) -> list[str]:
    """Return a description for each kind of unspeakable content present."""
    violations: list[str] = []

    if CODE_FENCE.search(text):
        violations.append("contains a code fence; code must be described, not read")
    if BARE_URL.search(text):
        violations.append("contains a URL; a spoken URL is unusable")
    if TABLE_ROW.search(text):
        violations.append("contains a markdown table; tables must be prose")
    if DANGLING.search(text):
        violations.append("contains a dangling reference to unseen content")
    if COMMAND_FLAG.search(text):
        violations.append("contains a command flag; flags must be named in words")

    return violations


def assert_speakable(text: str) -> None:
    """Raise if `text` contains anything that must not be narrated."""
    violations = find_violations(text)
    if violations:
        raise UnspeakableError(
            "script is not speakable:\n" + "\n".join(f"  - {v}" for v in violations)
        )

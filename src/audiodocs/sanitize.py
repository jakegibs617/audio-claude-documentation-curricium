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

# The character before the dash must not be alphanumeric, so hyphenated
# compounds ("well-defined", "trade-offs") are safe -- but a flag wrapped in a
# backtick, quote, or bracket is still a flag. `say` reads `--print` and
# --print as bit-identical audio, so the wrapper must not buy an exemption.
COMMAND_FLAG = re.compile(r"(?:^|[\s`\"'(\[{])(--?[a-zA-Z][\w-]*)")


class UnspeakableError(Exception):
    """A script contains content that cannot be spoken aloud."""


def _excerpt(match: re.Match) -> str:
    """The offending text, trimmed, for a message someone can act on."""
    found = match.group(match.lastindex or 0).strip()
    return found if len(found) <= 60 else found[:57] + "..."


def find_violations(text: str) -> list[str]:
    """Return a description for each kind of unspeakable content present.

    Each description names the offending substring: a bare category is not
    actionable on a 1,500-word script.
    """
    checks = (
        (CODE_FENCE, "contains a code fence; code must be described, not read"),
        (BARE_URL, "contains a URL; a spoken URL is unusable"),
        (TABLE_ROW, "contains a markdown table; tables must be prose"),
        (DANGLING, "contains a dangling reference to unseen content"),
        (COMMAND_FLAG, "contains a command flag; flags must be named in words"),
    )

    violations: list[str] = []
    for pattern, description in checks:
        match = pattern.search(text)
        if match:
            violations.append(f"{description}: {_excerpt(match)!r}")

    return violations


def assert_speakable(text: str) -> None:
    """Raise if `text` contains anything that must not be narrated."""
    violations = find_violations(text)
    if violations:
        raise UnspeakableError(
            "script is not speakable:\n" + "\n".join(f"  - {v}" for v in violations)
        )

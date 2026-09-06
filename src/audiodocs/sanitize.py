"""Detect content that must never reach a text-to-speech engine.

A narration script is meant to be heard. Code fences, bare URLs, tables, and
references to things the listener cannot see are all failures of the rewrite
step. This module names them; it never silently repairs them.
"""
from __future__ import annotations

import hashlib
import re

CODE_FENCE = re.compile(r"```|~~~")
# Four-space indents are CommonMark code blocks. Spoken narration is continuous
# prose, so an indented line is never legitimate here.
INDENTED_CODE = re.compile(r"^ {4,}\S", re.MULTILINE)
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

# Exclude, do not enumerate. Only a word character or another dash makes a dash
# innocent -- that is what "well-defined" and "trade-offs" have and what a flag
# never does. An allowlist of wrappers passes whatever nobody thought to list,
# and `**--print**` is the likeliest deviation of all: a model told "no
# markdown" still reaching for bold.
COMMAND_FLAG = re.compile(r"(?<![\w-])(--?[a-zA-Z][\w-]*)")

# Doubled typographic dashes are a flag someone's editor prettified. Single ones
# are left alone: an em dash joined to a word is ordinary prose ("the
# model—which reads the file—has no memory") and must never be a false positive.
UNICODE_FLAG = re.compile(r"([\u2010-\u2015\u2212]{2}[a-zA-Z][\w-]*)")


def _fingerprint() -> str:
    """Identify the current rules, so a cache keyed on this expires when they
    tighten. Hand-maintained version numbers get forgotten; the patterns cannot.
    """
    digest = hashlib.sha256()
    for pattern in (
        CODE_FENCE, INDENTED_CODE, BARE_URL, TABLE_ROW, DANGLING,
        COMMAND_FLAG, UNICODE_FLAG,
    ):
        digest.update(pattern.pattern.encode())
    return digest.hexdigest()[:16]


RULES_FINGERPRINT = _fingerprint()


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
        (INDENTED_CODE, "contains an indented code block; code must be described"),
        (BARE_URL, "contains a URL; a spoken URL is unusable"),
        (TABLE_ROW, "contains a markdown table; tables must be prose"),
        (DANGLING, "contains a dangling reference to unseen content"),
        (COMMAND_FLAG, "contains a command flag; flags must be named in words"),
        (UNICODE_FLAG, "contains a command flag; flags must be named in words"),
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

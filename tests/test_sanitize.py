import pytest
from audiodocs.sanitize import find_violations, assert_speakable, UnspeakableError

CLEAN = (
    "The context window is not a filing cabinet, it is a desk. "
    "Everything Claude can see right now sits on that desk at once. "
    "When the desk fills up, older messages get summarized to make room."
)


def test_clean_narration_has_no_violations():
    assert find_violations(CLEAN) == []


def test_detects_fenced_code_block():
    text = CLEAN + "\n\n```bash\nclaude resume\n```\n"
    assert any("code fence" in v for v in find_violations(text))


def test_detects_bare_url():
    text = CLEAN + " See https://code.claude.com/docs/en/context-window for more."
    assert any("URL" in v for v in find_violations(text))


def test_detects_markdown_table():
    text = CLEAN + "\n\n| Flag | Meaning |\n| --- | --- |\n| p | print |\n"
    assert any("table" in v for v in find_violations(text))


def test_detects_dangling_reference():
    for phrase in ("as shown above", "see the table below", "in the diagram below"):
        violations = find_violations(CLEAN + " " + phrase)
        assert any("dangling reference" in v for v in violations), phrase


def test_detects_command_flag():
    assert any("flag" in v for v in find_violations(CLEAN + " Pass the --resume flag."))


def test_assert_speakable_passes_clean_text():
    assert assert_speakable(CLEAN) is None


def test_assert_speakable_raises_and_names_every_violation():
    text = CLEAN + "\n\n```python\nx = 1\n```\nSee https://example.com as shown above."
    with pytest.raises(UnspeakableError) as excinfo:
        assert_speakable(text)
    message = str(excinfo.value)
    assert "code fence" in message
    assert "URL" in message
    assert "dangling reference" in message


def test_ordinary_prose_using_above_is_not_a_false_positive():
    """Narration legitimately says things like 'layers above'. Only dangling
    references to unseen content are violations."""
    prose = "Each layer above the model sees a little less of the raw request."
    assert not any("dangling" in v for v in find_violations(prose))


def test_hyphenated_words_are_not_mistaken_for_flags():
    prose = "A well-defined, purpose-built interface keeps the trade-offs visible."
    assert find_violations(prose) == []


def test_detects_flags_behind_any_wrapper():
    """Nothing but a word character makes a dash innocent.

    An allowlist of wrappers is the wrong shape: it passes whatever nobody
    thought to enumerate. `say` reads every one of these as "dash dash print".
    """
    wrapped = [
        "`--print`", '"--print"', "(--print)", "[--print]", "{--print}",
        "**--print**", "*--print*", "<--print>", ",--print", ":--print",
        "=--print", ";--print", "/--print", "!--print", "~--print",
    ]
    for form in wrapped:
        text = f"{CLEAN} Use the {form} flag."
        assert any("flag" in v for v in find_violations(text)), form


def test_doubled_unicode_dashes_are_flags_but_prose_em_dashes_are_not():
    """A model that types en dashes still means a flag. But an em dash joined to
    a word is ordinary prose and must never be a false positive."""
    for dash in ("\u2013\u2013", "\u2014\u2014", "\u2011\u2011", "\u2212\u2212"):
        assert find_violations(f"{CLEAN} Use {dash}print now."), dash

    prose = CLEAN + " The model\u2014which reads the whole file\u2014has no memory."
    assert find_violations(prose) == []


def test_detects_tilde_fences_and_indented_code():
    """Tilde fences and four-space indents are valid CommonMark that models emit,
    and a JSON blob reaching the speech engine is the loud-failure case."""
    assert any("code" in v for v in find_violations(CLEAN + '\n~~~json\n{"a":1}\n~~~'))
    assert any("code" in v for v in find_violations(CLEAN + '\n\n    {"hooks": {}}\n'))


def test_violation_names_the_offending_text():
    """A rejection on a 1,500-word script is only actionable if it says what to look for."""
    violations = find_violations(CLEAN + " Pass the --resume flag.")
    assert any("--resume" in v for v in violations), violations

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

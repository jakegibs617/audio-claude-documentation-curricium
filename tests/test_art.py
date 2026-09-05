import pytest
from pathlib import Path
from audiodocs.art import render_png, ArtError

SVG = Path("diagrams/ep03-context-window.svg")


def test_diagram_source_exists():
    assert SVG.exists(), "the episode 03 diagram must be authored first"


def test_rejects_missing_svg(tmp_path):
    with pytest.raises(ArtError, match="no such diagram"):
        render_png(tmp_path / "nope.svg", tmp_path / "out.png")


@pytest.mark.smoke
def test_renders_a_square_png(tmp_path):
    out = render_png(SVG, tmp_path / "ep03.png", size=1400)
    assert out.exists()
    assert out.stat().st_size > 5000
    assert out.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n", "output must be a real PNG"

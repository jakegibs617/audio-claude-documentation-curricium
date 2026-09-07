"""Render episode diagrams to PNG artwork using headless Chrome."""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


class ArtError(Exception):
    """Diagram rendering failed."""


def render_png(svg_path: Path, png_path: Path, size: int = 1400) -> Path:
    svg_path = Path(svg_path)
    png_path = Path(png_path)

    if not svg_path.exists():
        raise ArtError(f"no such diagram: {svg_path}")
    if not Path(CHROME).exists():
        raise ArtError(f"Chrome not found at {CHROME}")

    png_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as workdir:
        shot = Path(workdir) / "screenshot.png"
        result = subprocess.run(
            [
                CHROME,
                "--headless",
                "--disable-gpu",
                "--hide-scrollbars",
                f"--window-size={size},{size}",
                f"--screenshot={shot}",
                svg_path.resolve().as_uri(),
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if not shot.exists():
            raise ArtError(
                f"Chrome produced no screenshot: {result.stderr.strip()[:400]}"
            )
        shutil.move(str(shot), str(png_path))

    return png_path

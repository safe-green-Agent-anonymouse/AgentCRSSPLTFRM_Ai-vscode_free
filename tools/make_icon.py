"""Genere assets/icon.ico (multi-resolutions) sans ressource binaire versionnee.

Usage : python tools/make_icon.py
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

SIZES = (16, 24, 32, 48, 64, 128, 256)
BACKGROUND = (18, 24, 38, 255)
ACCENT = (56, 189, 248, 255)
ACCENT_SOFT = (94, 234, 212, 255)


def draw(size: int) -> Image.Image:
    """Dessine un chevron '>' et un curseur sur fond arrondi."""
    scale = 4
    canvas = Image.new("RGBA", (size * scale, size * scale), (0, 0, 0, 0))
    pen = ImageDraw.Draw(canvas)
    edge = size * scale
    radius = int(edge * 0.22)
    pen.rounded_rectangle((0, 0, edge - 1, edge - 1), radius=radius, fill=BACKGROUND)

    width = max(2, int(edge * 0.09))
    pen.line(
        [(edge * 0.26, edge * 0.32), (edge * 0.48, edge * 0.5), (edge * 0.26, edge * 0.68)],
        fill=ACCENT,
        width=width,
        joint="curve",
    )
    pen.line(
        [(edge * 0.56, edge * 0.70), (edge * 0.76, edge * 0.70)],
        fill=ACCENT_SOFT,
        width=width,
    )
    return canvas.resize((size, size), Image.LANCZOS)


def main() -> None:
    target = Path(__file__).resolve().parent.parent / "assets" / "icon.ico"
    target.parent.mkdir(parents=True, exist_ok=True)
    images = [draw(size) for size in SIZES]
    images[-1].save(target, format="ICO", sizes=[(s, s) for s in SIZES])
    print(f"icone ecrite : {target}")


if __name__ == "__main__":
    main()

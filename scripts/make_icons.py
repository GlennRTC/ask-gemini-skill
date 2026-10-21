"""Regenerates the skill icons (a generic friendly robot). Needs Pillow, which is NOT a
project dependency: install it only on the machine where you regenerate the icons."""
from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parent.parent / "skill-package" / "assets"
BG, BODY, DARK, ACCENT = "#1F6FEB", "#F4F7FB", "#16324F", "#FFB703"


def draw(size):
    s = size * 4  # supersample for smooth edges
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    u = s / 100
    d.rectangle([0, 0, s, s], fill=BG)  # full square: Alexa applies its own rounding
    # antenna
    d.line([50 * u, 22 * u, 50 * u, 31 * u], fill=BODY, width=int(3 * u))
    d.ellipse([45 * u, 14 * u, 55 * u, 24 * u], fill=ACCENT)
    # ears and head
    d.rounded_rectangle([17 * u, 46 * u, 24 * u, 62 * u], radius=3 * u, fill=BODY)
    d.rounded_rectangle([76 * u, 46 * u, 83 * u, 62 * u], radius=3 * u, fill=BODY)
    d.rounded_rectangle([22 * u, 30 * u, 78 * u, 78 * u], radius=12 * u, fill=BODY)
    # face
    d.ellipse([34 * u, 44 * u, 46 * u, 56 * u], fill=DARK)
    d.ellipse([54 * u, 44 * u, 66 * u, 56 * u], fill=DARK)
    d.arc([36 * u, 54 * u, 64 * u, 72 * u], start=20, end=160, fill=DARK, width=int(3.2 * u))
    return img.resize((size, size), Image.LANCZOS)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for size in (108, 512):
        draw(size).save(OUT / f"icon_{size}.png")
        print("wrote", OUT / f"icon_{size}.png")

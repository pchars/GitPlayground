"""One-off generator: static/img/favicon.ico from the GitPlayground logo geometry."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "static" / "img" / "favicon.ico"
SIZE = 64


def _draw_logo(draw: ImageDraw.ImageDraw, scale: float) -> None:
    def s(value: float) -> float:
        return value * scale

    margin = s(4)
    radius = s(14)
    draw.rounded_rectangle(
        (margin, margin, SIZE * scale - margin, SIZE * scale - margin),
        radius=radius,
        fill="#111111",
    )
    stroke = max(1, int(s(4)))
    x_main = s(24)
    y_top = s(18)
    y_mid = s(30)
    y_bot = s(46)
    x_branch = s(40)
    y_branch = s(41)
    draw.line((x_main, y_top, x_main, y_bot), fill="#ffffff", width=stroke)
    draw.line((x_main, y_mid, s(33), y_mid), fill="#ffffff", width=stroke)
    draw.line((s(33), y_mid, x_branch, y_mid, x_branch, s(39)), fill="#ffffff", width=stroke)
    r = s(5.5)
    for cx, cy in ((x_main, y_top), (x_main, y_bot), (x_branch, y_branch)):
        draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill="#ffffff")


def main() -> None:
    frames: list[Image.Image] = []
    for dimension in (16, 32, 48):
        image = Image.new("RGBA", (dimension, dimension), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        _draw_logo(draw, dimension / SIZE)
        frames.append(image)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(
        OUT,
        format="ICO",
        sizes=[(frame.width, frame.height) for frame in frames],
        append_images=frames[1:],
    )
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Generate a polished macOS .icns icon for the desktop app."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


def lerp(a: int, b: int, t: float) -> int:
    return int(a + (b - a) * t)


def gradient_background(size: int) -> Image.Image:
    top_left = (48, 125, 108)
    bottom_right = (245, 164, 92)
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    px = img.load()
    for y in range(size):
        for x in range(size):
            t = (x + y) / (2 * (size - 1))
            r = lerp(top_left[0], bottom_right[0], t)
            g = lerp(top_left[1], bottom_right[1], t)
            b = lerp(top_left[2], bottom_right[2], t)
            px[x, y] = (r, g, b, 255)
    return img


def draw_icon_canvas(size: int) -> Image.Image:
    img = gradient_background(size)
    draw = ImageDraw.Draw(img)

    # Soft glow for depth.
    glow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    glow_draw.ellipse(
        (size * 0.12, size * 0.08, size * 0.88, size * 0.84),
        fill=(255, 245, 226, 140),
    )
    glow = glow.filter(ImageFilter.GaussianBlur(radius=size * 0.03))
    img.alpha_composite(glow)

    # Card shadow.
    shadow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    shadow_draw.rounded_rectangle(
        (size * 0.23, size * 0.21, size * 0.77, size * 0.79),
        radius=size * 0.09,
        fill=(0, 0, 0, 115),
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=size * 0.018))
    img.alpha_composite(shadow)

    # Birthday card body.
    draw.rounded_rectangle(
        (size * 0.22, size * 0.2, size * 0.76, size * 0.76),
        radius=size * 0.09,
        fill=(255, 255, 255, 246),
    )

    # Card header band.
    draw.rounded_rectangle(
        (size * 0.22, size * 0.2, size * 0.76, size * 0.34),
        radius=size * 0.09,
        fill=(235, 102, 86, 245),
    )
    draw.rectangle(
        (size * 0.22, size * 0.29, size * 0.76, size * 0.34),
        fill=(235, 102, 86, 245),
    )

    # Binding dots.
    ring_color = (255, 240, 220, 240)
    for cx in (0.32, 0.43, 0.54, 0.65):
        x = size * cx
        y = size * 0.27
        r = size * 0.018
        draw.ellipse((x - r, y - r, x + r, y + r), fill=ring_color)

    # Cake base.
    cake_fill = (246, 210, 150, 255)
    icing_fill = (255, 242, 229, 255)
    draw.rounded_rectangle(
        (size * 0.33, size * 0.51, size * 0.65, size * 0.65),
        radius=size * 0.03,
        fill=cake_fill,
    )
    draw.rounded_rectangle(
        (size * 0.325, size * 0.47, size * 0.655, size * 0.54),
        radius=size * 0.03,
        fill=icing_fill,
    )

    # Candle.
    draw.rounded_rectangle(
        (size * 0.48, size * 0.39, size * 0.52, size * 0.52),
        radius=size * 0.01,
        fill=(102, 168, 194, 255),
    )
    draw.ellipse(
        (size * 0.465, size * 0.33, size * 0.535, size * 0.41),
        fill=(255, 187, 92, 255),
    )
    draw.ellipse(
        (size * 0.482, size * 0.352, size * 0.518, size * 0.395),
        fill=(255, 233, 169, 255),
    )

    # Confetti accents.
    confetti = [
        (0.28, 0.42, (93, 166, 141, 235)),
        (0.68, 0.45, (227, 126, 100, 235)),
        (0.35, 0.68, (245, 172, 80, 235)),
        (0.62, 0.67, (77, 145, 170, 235)),
    ]
    for cx, cy, color in confetti:
        r = size * 0.013
        draw.ellipse((size * cx - r, size * cy - r, size * cx + r, size * cy + r), fill=color)

    return img


def build_iconset(master_png: Path, iconset_dir: Path) -> None:
    iconset_dir.mkdir(parents=True, exist_ok=True)
    sizes = [
        (16, 1),
        (16, 2),
        (32, 1),
        (32, 2),
        (128, 1),
        (128, 2),
        (256, 1),
        (256, 2),
        (512, 1),
        (512, 2),
    ]

    src = Image.open(master_png).convert("RGBA")
    for base, scale in sizes:
        pixel = base * scale
        out_name = f"icon_{base}x{base}.png" if scale == 1 else f"icon_{base}x{base}@2x.png"
        out_path = iconset_dir / out_name
        resized = src.resize((pixel, pixel), Image.Resampling.LANCZOS)
        resized.save(out_path, format="PNG")


def build_icns(iconset_dir: Path, output_icns: Path) -> None:
    output_icns.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["iconutil", "-c", "icns", str(iconset_dir), "-o", str(output_icns)]
    subprocess.run(cmd, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate app icon files for macOS")
    parser.add_argument(
        "--output-icns",
        default="assets/生辰灯塔.icns",
        help="output .icns path",
    )
    parser.add_argument(
        "--workdir",
        default="assets",
        help="directory for intermediate icon files",
    )
    args = parser.parse_args()

    workdir = Path(args.workdir).resolve()
    master_png = workdir / "app_icon_source.png"
    iconset_dir = workdir / "AppIcon.iconset"
    output_icns = Path(args.output_icns).resolve()

    workdir.mkdir(parents=True, exist_ok=True)
    master = draw_icon_canvas(1024)
    master.save(master_png, format="PNG")
    build_iconset(master_png, iconset_dir)
    build_icns(iconset_dir, output_icns)
    print(output_icns)


if __name__ == "__main__":
    main()

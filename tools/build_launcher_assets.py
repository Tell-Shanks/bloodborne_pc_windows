# SPDX-License-Identifier: GPL-2.0-or-later
"""Build launcher image assets from the artwork in the repository root.

Run with any Python that has Pillow (the launcher itself does not need Pillow):
    py tools/build_launcher_assets.py

Outputs to launcher_assets/:
    hero_dark.png / hero_dark@2x.png    header artwork, fades into the dark theme
    hero_light.png / hero_light@2x.png  header artwork, fades into the light theme

The header crop keeps the moon, the clock tower and the rooftops from the
textless poster, away from the hunter so no figure is half-cut at the edges.
"""

from PIL import Image, ImageDraw

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / 'bloodborne_hi_res_textless_poster__by_phetvanburton_d7lswrs-fullview.jpg'
OUTPUT = ROOT / 'launcher_assets'

# Crop of the 1024x1440 poster: the skyline band with moon and clock tower.
CROP = (0, 80, 1024, 558)
# Logical size of the framed artwork in the header; the @2x files double it.
SIZE = (300, 140)
RADIUS = 10          # logical corner radius
FADE = 0.66          # fraction of the width where the fade to the theme starts

THEMES = {
    'dark': (0x14, 0x16, 0x1a),
    'light': (0xf2, 0xf1, 0xec),
}


def rounded_mask(size, radius):
    mask = Image.new('L', size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle([0, 0, size[0] - 1, size[1] - 1], radius=radius, fill=255)
    return mask


def fade_layer(width, height, background, start_ratio):
    """A background-coloured layer whose horizontal alpha rises past start_ratio."""
    layer = Image.new('RGB', (width, height), background)
    mask = Image.new('L', (width, height), 0)
    pixels = mask.load()
    start = width * start_ratio
    span = max(1.0, width - start)
    column = []
    for x in range(width):
        t = (x - start) / span
        t = 0.0 if t < 0 else (1.0 if t > 1 else t)
        column.append(int(255 * (t * t * (3 - 2 * t))))  # smoothstep
    for x, value in enumerate(column):
        for y in range(height):
            pixels[x, y] = value
    return layer, mask


def build(theme, size, radius):
    width, height = size
    base = Image.open(SOURCE).convert('RGB').crop(CROP).resize(size, Image.LANCZOS)
    layer, mask = fade_layer(width, height, THEMES[theme], FADE)
    art = Image.composite(layer, base, mask).convert('RGBA')
    art.putalpha(rounded_mask(size, radius))
    return art


def main():
    OUTPUT.mkdir(exist_ok=True)
    for theme in THEMES:
        for scale, suffix in ((1, ''), (2, '@2x')):
            size = (SIZE[0] * scale, SIZE[1] * scale)
            radius = RADIUS * scale
            if scale == 2:
                # Downscale the same master so both files match exactly.
                master = build(theme, size, radius).resize(
                    (SIZE[0], SIZE[1]), Image.LANCZOS)
                art = build(theme, size, radius)
                art.save(OUTPUT / f'hero_{theme}@2x.png')
                master.save(OUTPUT / f'hero_{theme}.png')
            else:
                continue
    print(f'assets written to {OUTPUT}')


if __name__ == '__main__':
    main()

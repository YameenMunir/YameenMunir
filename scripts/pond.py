"""Place the git-koi GIF in an animated pixel-art pond.

Usage: python scripts/pond.py koi/koi.gif koi/pond.gif

The pond is drawn at half resolution and scaled 2x so it matches the koi's
pixel size. Every animated element completes a whole number of cycles over
the koi's frame count, so the GIF loops without a seam.
"""

import math
import sys

from PIL import Image, ImageChops, ImageDraw

SCALE = 2
BAYER = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]

WATER = [(9, 42, 56), (11, 52, 66), (14, 64, 77), (18, 78, 89), (23, 92, 101)]
CAUSTIC = [(28, 98, 106), (64, 142, 144)]
RIM_DARK, RIM_MID, RIM_LIGHT, MOSS = (52, 56, 60), (96, 101, 104), (140, 145, 146), (78, 112, 62)
PAD_DARK, PAD, PAD_LIGHT = (34, 92, 46), (58, 136, 64), (104, 178, 88)
PETAL, PETAL_LIGHT, PETAL_CORE = (226, 120, 160), (250, 196, 214), (248, 214, 92)
RIPPLE = (120, 196, 196)
BUBBLE = (150, 214, 214)


def rounded_mask(size, radius):
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, size - 1, size - 1), radius, fill=255)
    return mask


def water(size, t, inner):
    """Dithered depth gradient with drifting caustic light."""
    img = Image.new("RGB", (size, size))
    px = img.load()
    c = size / 2
    for y in range(size):
        for x in range(size):
            if not inner.getpixel((x, y)):
                continue
            # Shallower towards the top left, deeper towards the edges.
            depth = 0.55 * (1 - (x + y) / (2 * size)) + 0.45 * (1 - math.hypot(x - c, y - c) / (c * 1.45))
            level = depth * (len(WATER) - 1) + (BAYER[y % 4][x % 4] / 16 - 0.5)
            colour = WATER[max(0, min(len(WATER) - 1, round(level)))]
            # Caustics are the zero contours of a moving wave sum: a net of thin lines.
            v = abs(
                math.sin(x * 0.09 + math.sin(y * 0.05 + t) + t)
                + math.sin(y * 0.11 + math.sin(x * 0.06 - t) - t)
                + 0.6 * math.sin((x + y) * 0.06 + 2 * t)
            )
            if v < 0.07 and depth > 0.35:
                colour = CAUSTIC[1]
            elif v < 0.2:
                colour = CAUSTIC[0] if depth > 0.3 else WATER[min(len(WATER) - 1, round(level) + 1)]
            px[x, y] = colour
    return img


def draw_rim(draw, size, radius, width):
    for i, colour in enumerate([RIM_DARK, RIM_MID, RIM_MID, RIM_LIGHT, RIM_MID, RIM_MID, RIM_DARK]):
        if i >= width:
            break
        draw.rounded_rectangle((i, i, size - 1 - i, size - 1 - i), max(1, radius - i), outline=colour)
    # Moss and pebble flecks scattered round the rim.
    for k in range(70):
        a = k * 2.399963
        d = (k * 37) % width
        x = int((size / 2) + math.cos(a) * size)
        y = int((size / 2) + math.sin(a) * size)
        x = max(d, min(size - 1 - d, x))
        y = max(d, min(size - 1 - d, y))
        draw.point((x, y), fill=MOSS if k % 3 else RIM_LIGHT)


def lily_pad(draw, cx, cy, r, notch, flower):
    draw.ellipse((cx - r + 2, cy - r + 3, cx + r + 2, cy + r + 3), fill=WATER[0])  # shadow
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=PAD, outline=PAD_DARK)
    a0 = math.radians(notch)
    draw.polygon(
        [(cx, cy), (cx + math.cos(a0 - 0.28) * (r + 1), cy + math.sin(a0 - 0.28) * (r + 1)),
         (cx + math.cos(a0 + 0.28) * (r + 1), cy + math.sin(a0 + 0.28) * (r + 1))],
        fill=(0, 0, 0, 0),
    )
    for k in range(5):  # veins
        a = a0 + 0.7 + k * 1.0
        draw.line((cx, cy, cx + math.cos(a) * (r - 2), cy + math.sin(a) * (r - 2)), fill=PAD_DARK)
    draw.arc((cx - r + 2, cy - r + 2, cx + r - 2, cy + r - 2), 200, 260, fill=PAD_LIGHT)
    if flower:
        for k in range(6):
            a = k * math.pi / 3
            px, py = cx + math.cos(a) * 3, cy - 2 + math.sin(a) * 3
            draw.ellipse((px - 2, py - 2, px + 2, py + 2), fill=PETAL, outline=(176, 72, 112))
        for k in range(5):
            a = k * 2 * math.pi / 5 + 0.6
            px, py = cx + math.cos(a) * 1.5, cy - 3 + math.sin(a) * 1.5
            draw.ellipse((px - 1.5, py - 1.5, px + 1.5, py + 1.5), fill=PETAL_LIGHT)
        draw.rectangle((cx - 1, cy - 3, cx, cy - 2), fill=PETAL_CORE)


def main(src, dst):
    koi = Image.open(src)
    frames, durations = [], []
    for i in range(koi.n_frames):
        koi.seek(i)
        frames.append(koi.convert("RGBA"))
        durations.append(koi.info.get("duration", 70))
    n = len(frames)
    full = frames[0].width
    size = full // SCALE
    radius, rim = 26, 7

    outer = rounded_mask(size, radius)
    inner = Image.new("L", (size, size), 0)
    ImageDraw.Draw(inner).rounded_rectangle((rim, rim, size - 1 - rim, size - 1 - rim), radius - rim, fill=255)
    outer_full = outer.resize((full, full), Image.NEAREST)
    inner_full = inner.resize((full, full), Image.NEAREST)

    pads = [  # x, y, radius, notch angle, flower, drift phase
        (196, 58, 17, 210, True, 0.0),
        (62, 196, 14, 330, False, 2.1),
        (214, 196, 10, 120, True, 4.0),
    ]
    ripple_sources = [(110, 70, 0), (176, 150, 40), (70, 120, 80)]
    bubbles = [(88, 230, 0), (150, 216, 30), (196, 140, 60), (120, 110, 90)]

    out = []
    for i, koi_frame in enumerate(frames):
        t = 2 * math.pi * i / n
        base = water(size, t, inner)
        d = ImageDraw.Draw(base)

        for sx, sy, offset in ripple_sources:
            p = ((i + offset) % n) / n
            if p < 0.5:
                r = 3 + p * 2 * 26
                fade = RIPPLE if p < 0.3 else CAUSTIC[0]
                d.ellipse((sx - r, sy - r * 0.6, sx + r, sy + r * 0.6), outline=fade)
                if r > 10:
                    r2 = r - 7
                    d.ellipse((sx - r2, sy - r2 * 0.6, sx + r2, sy + r2 * 0.6), outline=CAUSTIC[0])

        for bx, by, offset in bubbles:
            p = ((i + offset) % n) / n
            if p < 0.35:
                rise = p / 0.35
                y = by - rise * 30
                x = bx + math.sin(rise * 6) * 2
                s = 1 + (rise > 0.5)
                d.ellipse((x - s, y - s, x + s, y + s), outline=BUBBLE)

        canvas = base.resize((full, full), Image.NEAREST).convert("RGBA")

        # The koi's shadow on the pond floor, then the koi itself.
        alpha = koi_frame.getchannel("A")
        shadow = Image.new("RGBA", (full, full), (4, 22, 30, 0))
        shadow.putalpha(ImageChops.offset(alpha, 10, 14).point(lambda a: 110 if a else 0))
        canvas = Image.alpha_composite(canvas, shadow)
        canvas = Image.alpha_composite(canvas, koi_frame)

        # Lily pads float above the koi so it swims beneath them.
        top = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        td = ImageDraw.Draw(top)
        for x, y, r, notch, flower, phase in pads:
            dx = math.sin(t + phase) * 2
            dy = math.cos(t + phase) * 1.5
            lily_pad(td, round(x + dx), round(y + dy), r, notch + math.sin(t + phase) * 8, flower)
        top.putalpha(ImageChops.multiply(top.getchannel("A"), inner))
        canvas = Image.alpha_composite(canvas, top.resize((full, full), Image.NEAREST))

        rim_layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw_rim(ImageDraw.Draw(rim_layer), size, radius, rim)
        rim_layer.putalpha(ImageChops.multiply(rim_layer.getchannel("A"), ImageChops.subtract(outer, inner)))
        canvas = Image.alpha_composite(canvas, rim_layer.resize((full, full), Image.NEAREST))

        canvas.putalpha(outer_full)
        out.append(canvas)

    # One shared palette with index 255 kept for the transparent corners.
    sample = Image.new("RGB", (full, full * 4))
    for k in range(4):
        sample.paste(out[k * n // 4].convert("RGB"), (0, full * k))
    palette = sample.quantize(255, method=Image.MEDIANCUT)
    pal = palette.getpalette()[: 255 * 3] + [0, 0, 0]
    palette.putpalette(pal)

    gif_frames = []
    for frame in out:
        p = frame.convert("RGB").quantize(palette=palette, dither=Image.NONE)
        p.paste(255, mask=ImageChops.invert(outer_full))
        p.info["transparency"] = 255
        gif_frames.append(p)

    gif_frames[0].save(
        dst, save_all=True, append_images=gif_frames[1:], duration=durations,
        loop=0, transparency=255, disposal=2, optimize=False,
    )


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])

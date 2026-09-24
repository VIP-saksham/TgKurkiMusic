# KeyaraMusic — "Glass Player" thumbnail engine
#
# Reference: floating glassmorphic player card on a blurred concert backdrop —
#   1. Background: artwork blur + neon glow blobs + sparkles (club-lights vibe)
#   2. Glass card: dark translucent panel with neon accent glow + thin border
#   3. Header: track title, channel + verified badge, two round glass buttons
#   4. Artwork: wide rounded-rect panel with equalizer bars along the bottom
#   5. Progress bar with knob + elapsed / remaining time labels
#   6. Controls row: shuffle / prev / big play / next / repeat
#
# Deterministic: same video-ID = same poster (accent, sparkles, equalizer,
# progress sab videoid se seed hote hain). Sirf stdlib + Pillow.

import hashlib
import math
import random
import traceback
from pathlib import Path

import aiofiles
import aiohttp
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

from KeyaraMusic import app
from py_yt import VideosSearch

CACHE_DIR = Path("cache")
CACHE_DIR.mkdir(exist_ok=True)

CANVAS_W, CANVAS_H = 1320, 760

FONT_REGULAR_PATH = "KeyaraMusic/assets/font2.ttf"
FONT_BOLD_PATH = "KeyaraMusic/assets/font3.ttf"
DEFAULT_THUMB = "KeyaraMusic/assets/ShrutiBots.jpg"

# ----- glass card geometry -------------------------------------------------
CARD_X0, CARD_Y0, CARD_X1, CARD_Y1 = 190, 70, 1130, 690
CARD_R = 44
PAD = 46
CX = (CARD_X0 + CARD_X1) // 2

# ----- palette --------------------------------------------------------------
WHITE = (248, 248, 252, 242)
SOFT = (232, 232, 242, 190)
FAINT = (232, 232, 242, 120)
TRACK = (255, 255, 255, 65)
FILL = (255, 255, 255, 235)
BADGE_BLUE = (86, 152, 255, 255)
GLASS_FILL = (12, 12, 22, 152)
GLASS_BORDER = (255, 255, 255, 72)

ACCENTS = [
    (255, 64, 129),    # hot pink (reference vibe)
    (96, 145, 255),    # electric blue
    (0, 210, 255),     # cyan
    (172, 92, 255),    # violet
    (255, 150, 60),    # amber
]

ART_X0, ART_Y0, ART_X1, ART_Y1 = CARD_X0 + PAD, 210, CARD_X1 - PAD, 472
ART_R = 26
BAR_Y = 514
CTRL_CY = 604
PLAY_R = 44


def _rng_for(videoid: str) -> random.Random:
    seed = int(hashlib.sha256(videoid.encode()).hexdigest()[:16], 16)
    return random.Random(seed)


def _fmt_time(sec) -> str:
    sec = max(0, int(sec))
    m, s = divmod(sec, 60)
    if m >= 60:
        h, m = divmod(m, 60)
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def _parse_seconds(duration):
    if not duration or ":" not in duration:
        return None
    try:
        parts = [int(p) for p in duration.split(":")]
    except ValueError:
        return None
    if len(parts) == 2:
        return parts[0] * 60 + parts[1]
    if len(parts) == 3:
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    return None


# ----- primitives ------------------------------------------------------------


def _cover_crop(img, w, h):
    scale = max(w / img.width, h / img.height)
    img = img.resize((int(img.width * scale) + 1, int(img.height * scale) + 1), Image.LANCZOS)
    x = (img.width - w) // 2
    y = (img.height - h) // 2
    return img.crop((x, y, x + w, y + h))


def _rounded_mask(w, h, radius):
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, w - 1, h - 1], radius=radius, fill=255)
    return m


def _fit_text(draw, text, path, max_w, start_size, min_size=26):
    """Single line: shrink to fit, phir ellipsize."""
    size = start_size
    while size >= min_size:
        font = ImageFont.truetype(path, size)
        if draw.textlength(text, font=font) <= max_w:
            return text, font
        size -= 2
    font = ImageFont.truetype(path, min_size)
    if draw.textlength(text, font=font) <= max_w:
        return text, font
    while text and draw.textlength(text + "…", font=font) > max_w:
        text = text[:-1]
    return text + "…", font


def _arrow(draw, x0, y0, x1, y1, color, width=3, head=7):
    """Line + arrowhead pointing at (x1, y1)."""
    draw.line([(x0, y0), (x1, y1)], fill=color, width=width)
    ang = math.atan2(y1 - y0, x1 - x0)
    a1 = ang + math.radians(153)
    a2 = ang - math.radians(153)
    draw.polygon(
        [
            (x1, y1),
            (x1 + head * math.cos(a1), y1 + head * math.sin(a1)),
            (x1 + head * math.cos(a2), y1 + head * math.sin(a2)),
        ],
        fill=color,
    )


def _check_badge(draw, cx, cy, r=11):
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=BADGE_BLUE)
    draw.line([(cx - 4, cy), (cx - 1, cy + 4)], fill=(255, 255, 255, 255), width=2)
    draw.line([(cx - 1, cy + 4), (cx + 5, cy - 4)], fill=(255, 255, 255, 255), width=2)


# ----- background ------------------------------------------------------------


def _background(art, rng, accent):
    # Black theme — kaafi dark background, subtle glow
    bg = _cover_crop(art, CANVAS_W, CANVAS_H).filter(ImageFilter.GaussianBlur(48))
    bg = ImageEnhance.Brightness(bg).enhance(0.28)
    bg = ImageEnhance.Color(bg).enhance(0.7)
    black = Image.new("RGBA", (CANVAS_W, CANVAS_H), (5, 5, 8, 235))
    canvas = Image.alpha_composite(bg.convert("RGBA"), black)

    # neon glow blobs — dim, black-theme vibe
    for (gx, gy), color, rad, alpha in [
        ((rng.randint(90, 260), rng.randint(430, 640)), (*accent, 45), rng.randint(240, 320), None),
        ((rng.randint(1050, 1230), rng.randint(80, 280)), (70, 110, 255, 40), rng.randint(260, 340), None),
        ((rng.randint(400, 900), rng.randint(600, 740)), (*accent, 25), rng.randint(200, 260), None),
    ]:
        blob = Image.new("RGBA", (rad * 2, rad * 2), (0, 0, 0, 0))
        ImageDraw.Draw(blob).ellipse([0, 0, rad * 2, rad * 2], fill=color)
        blob = blob.filter(ImageFilter.GaussianBlur(70))
        canvas.alpha_composite(blob, (int(gx - rad), int(gy - rad)))

    # sparkle dust
    dust = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0, 0, 0, 0))
    dd = ImageDraw.Draw(dust)
    for _ in range(90):
        x, y = rng.randint(0, CANVAS_W - 1), rng.randint(0, CANVAS_H - 1)
        r = rng.choice([1, 1, 1, 2, 2, 3])
        a = rng.randint(28, 130)
        col = (255, 255, 255, a) if rng.random() < 0.6 else (*accent, a)
        dd.ellipse([x - r, y - r, x + r, y + r], fill=col)
    dust = dust.filter(ImageFilter.GaussianBlur(0.6))
    canvas.alpha_composite(dust)
    return canvas


def _glass_card(canvas, accent):
    x0, y0, x1, y1 = CARD_X0, CARD_Y0, CARD_X1, CARD_Y1
    w, h = x1 - x0, y1 - y0

    # drop shadow
    sh = Image.new("RGBA", (w + 160, h + 160), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle(
        [80, 84, 80 + w, 84 + h], radius=CARD_R, fill=(0, 0, 0, 160)
    )
    canvas.alpha_composite(sh.filter(ImageFilter.GaussianBlur(34)), (x0 - 80, y0 - 80))

    # neon accent glow ring (2 passes, strong like the reference)
    glow = Image.new("RGBA", (w + 160, h + 160), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.rounded_rectangle([80, 80, 80 + w, 80 + h], radius=CARD_R, outline=(*accent, 255), width=16)
    glow = glow.filter(ImageFilter.GaussianBlur(30))
    canvas.alpha_composite(glow, (x0 - 80, y0 - 80))

    glow2 = Image.new("RGBA", (w + 80, h + 80), (0, 0, 0, 0))
    ImageDraw.Draw(glow2).rounded_rectangle(
        [40, 40, 40 + w, 40 + h], radius=CARD_R, outline=(130, 170, 255, 190), width=8
    )
    canvas.alpha_composite(glow2.filter(ImageFilter.GaussianBlur(16)), (x0 - 40, y0 - 40))

    # crisp inner border on top of the glow
    edge = Image.new("RGBA", (w + 8, h + 8), (0, 0, 0, 0))
    ImageDraw.Draw(edge).rounded_rectangle(
        [4, 4, 4 + w, 4 + h], radius=CARD_R, outline=(210, 225, 255, 200), width=3
    )
    canvas.alpha_composite(edge, (x0 - 4, y0 - 4))

    # glass body
    body = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    bd = ImageDraw.Draw(body)
    bd.rounded_rectangle([0, 0, w - 1, h - 1], radius=CARD_R, fill=GLASS_FILL)
    bd.rounded_rectangle([0, 0, w - 1, h - 1], radius=CARD_R, outline=GLASS_BORDER, width=2)
    canvas.alpha_composite(body, (x0, y0))
    return canvas


# ----- header -----------------------------------------------------------------


def _note_glyph(draw, cx, cy, color=(255, 255, 255, 225)):
    draw.ellipse([cx - 10, cy + 2, cx + 2, cy + 12], fill=color)
    draw.line([(cx + 2, cy + 7), (cx + 2, cy - 10)], fill=color, width=3)
    draw.line([(cx + 2, cy - 10), (cx + 10, cy - 5)], fill=color, width=3)


def _heart_glyph(draw, cx, cy, color=(255, 255, 255, 225)):
    draw.ellipse([cx - 12, cy - 10, cx, cy + 2], fill=color)
    draw.ellipse([cx, cy - 10, cx + 12, cy + 2], fill=color)
    draw.polygon([(cx - 11, cy - 1), (cx + 11, cy - 1), (cx, cy + 11)], fill=color)


def _circle_button(canvas, cx, cy, r, glyph_draw):
    btn = Image.new("RGBA", (r * 2 + 8, r * 2 + 8), (0, 0, 0, 0))
    bd = ImageDraw.Draw(btn)
    bd.ellipse([2, 2, 2 + r * 2, 2 + r * 2], fill=(255, 255, 255, 30))
    bd.ellipse([2, 2, 2 + r * 2, 2 + r * 2], outline=(255, 255, 255, 70), width=2)
    glyph_draw(bd, r + 2, r + 2)
    canvas.alpha_composite(btn, (int(cx - r - 2), int(cy - r - 2)))


def _header(canvas, title, channel):
    draw = ImageDraw.Draw(canvas)
    max_w = (CARD_X1 - PAD - 190) - (CARD_X0 + PAD)
    title, tfont = _fit_text(draw, title, FONT_BOLD_PATH, max_w, 44, 28)
    draw.text((CARD_X0 + PAD, CARD_Y0 + 34), title, font=tfont, fill=WHITE)

    cfont = ImageFont.truetype(FONT_REGULAR_PATH, 27)
    cname, _ = _fit_text(draw, channel, FONT_REGULAR_PATH, max_w - 60, 27, 22)
    cyy = CARD_Y0 + 100
    draw.text((CARD_X0 + PAD, cyy), cname, font=cfont, fill=SOFT)
    cw = draw.textlength(cname, font=cfont)
    _check_badge(draw, int(CARD_X0 + PAD + cw + 22), int(cyy + 15))

    _circle_button(canvas, CARD_X1 - 64, CARD_Y0 + 64, 27, _note_glyph)
    _circle_button(canvas, CARD_X1 - 136, CARD_Y0 + 64, 27, _heart_glyph)


# ----- artwork + equalizer ----------------------------------------------------


def _equalizer(canvas, rng):
    w, h = ART_X1 - ART_X0, ART_Y1 - ART_Y0
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    bar_w, gap, base = 9, 6, 14
    bottom = h - 16
    x = 18
    level = rng.randint(20, 40)
    while x + bar_w <= w - 18:
        level = max(10, min(88, level + rng.randint(-16, 16)))
        alpha = rng.randint(130, 175)
        d.rounded_rectangle(
            [x, bottom - level, x + bar_w, bottom], radius=4, fill=(255, 255, 255, alpha)
        )
        x += bar_w + gap
    canvas.alpha_composite(
        Image.composite(layer, Image.new("RGBA", (w, h), (0, 0, 0, 0)), _rounded_mask(w, h, ART_R)),
        (ART_X0, ART_Y0),
    )


def _art_panel(canvas, art, rng):
    w, h = ART_X1 - ART_X0, ART_Y1 - ART_Y0
    # soft shadow
    sh = Image.new("RGBA", (w + 80, h + 80), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle(
        [40, 46, 40 + w, 46 + h], radius=ART_R, fill=(0, 0, 0, 140)
    )
    canvas.alpha_composite(sh.filter(ImageFilter.GaussianBlur(20)), (ART_X0 - 40, ART_Y0 - 40))

    art_img = _cover_crop(art, w, h).convert("RGBA")
    art_img.putalpha(_rounded_mask(w, h, ART_R))
    canvas.alpha_composite(art_img, (ART_X0, ART_Y0))

    # subtle glass sheen on top of artwork
    sheen = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(sheen).polygon(
        [(0, 0), (w, 0), (w, int(h * 0.16)), (0, int(h * 0.34))], fill=(255, 255, 255, 14)
    )
    canvas.alpha_composite(
        Image.composite(sheen, Image.new("RGBA", (w, h), (0, 0, 0, 0)), _rounded_mask(w, h, ART_R)),
        (ART_X0, ART_Y0),
    )
    _equalizer(canvas, rng)


# ----- progress + controls ------------------------------------------------------


def _progress_and_times(canvas, progress, total):
    draw = ImageDraw.Draw(canvas)
    x0, x1 = ART_X0, ART_X1
    draw.rounded_rectangle([x0, BAR_Y, x1, BAR_Y + 6], radius=3, fill=TRACK)
    fx = x0 + (x1 - x0) * progress
    if fx - x0 > 14:
        draw.rounded_rectangle([x0, BAR_Y, fx, BAR_Y + 6], radius=3, fill=FILL)
    draw.ellipse([fx - 9, BAR_Y - 5, fx + 9, BAR_Y + 11], fill=FILL)

    tfont = ImageFont.truetype(FONT_REGULAR_PATH, 24)
    if total:
        draw.text((x0, BAR_Y + 16), _fmt_time(progress * total), font=tfont, fill=FAINT)
        right = f"-{_fmt_time(total - progress * total)}"
    else:
        draw.text((x0, BAR_Y + 16), "0:00", font=tfont, fill=FAINT)
        right = "LIVE"
    rw = draw.textlength(right, font=tfont)
    draw.text((x1 - rw, BAR_Y + 16), right, font=tfont, fill=FAINT)


def _glyph_prev(d, cx, cy, color):
    d.rectangle([cx - 12, cy - 12, cx - 7, cy + 12], fill=color)
    d.polygon([(cx + 11, cy - 12), (cx + 11, cy + 12), (cx - 4, cy)], fill=color)


def _glyph_next(d, cx, cy, color):
    d.rectangle([cx + 7, cy - 12, cx + 12, cy + 12], fill=color)
    d.polygon([(cx - 11, cy - 12), (cx - 11, cy + 12), (cx + 4, cy)], fill=color)


def _glyph_play(d, cx, cy, color):
    d.polygon([(cx - 15, cy - 20), (cx - 15, cy + 20), (cx + 18, cy)], fill=color)


def _glyph_shuffle(d, cx, cy, color):
    _arrow(d, cx - 11, cy - 7, cx + 9, cy + 7, color)
    _arrow(d, cx - 11, cy + 7, cx + 9, cy - 7, color)
    d.line([(cx - 11, cy - 7), (cx - 11, cy + 2)], fill=color, width=3)
    d.line([(cx + 9, cy - 7), (cx + 9, cy - 2)], fill=color, width=3)


def _glyph_repeat(d, cx, cy, color):
    bbox = [cx - 12, cy - 9, cx + 12, cy + 9]
    d.arc(bbox, start=-40, end=160, fill=color, width=3)
    d.arc(bbox, start=140, end=320, fill=color, width=3)
    # arrowheads
    d.polygon([(cx + 11, cy + 2), (cx + 1, cy - 1), (cx + 8, cy + 9)], fill=color)
    d.polygon([(cx - 11, cy - 2), (cx - 1, cy + 1), (cx - 8, cy - 9)], fill=color)


def _controls(canvas):
    draw = ImageDraw.Draw(canvas)
    col = (245, 245, 250, 215)
    col2 = (245, 245, 250, 190)

    # big glass play button
    pr = PLAY_R
    btn = Image.new("RGBA", (pr * 2 + 12, pr * 2 + 12), (0, 0, 0, 0))
    bd = ImageDraw.Draw(btn)
    bd.ellipse([4, 4, 4 + pr * 2, 4 + pr * 2], fill=(255, 255, 255, 38))
    bd.ellipse([4, 4, 4 + pr * 2, 4 + pr * 2], outline=(255, 255, 255, 95), width=2)
    canvas.alpha_composite(btn, (CX - pr - 6, CTRL_CY - pr - 6))
    _glyph_play(draw, CX, CTRL_CY, (255, 255, 255, 245))

    _glyph_prev(draw, CX - 128, CTRL_CY, col2)
    _glyph_next(draw, CX + 128, CTRL_CY, col2)
    _glyph_shuffle(draw, CARD_X0 + 108, CTRL_CY, col)
    _glyph_repeat(draw, CARD_X1 - 108, CTRL_CY, col)


# ----- main ---------------------------------------------------------------------


async def gen_thumb(videoid: str):
    url = f"https://www.youtube.com/watch?v={videoid}"
    raw_art_path = None
    try:
        results = VideosSearch(url, limit=1)
        result = (await results.next())["result"][0]

        title = result.get("title", "Unknown Title")
        duration = result.get("duration", "Unknown")
        thumburl = result["thumbnails"][0]["url"].split("?")[0]
        channel = result.get("channel", {}).get("name", "Unknown Channel")

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(thumburl) as resp:
                    if resp.status == 200:
                        raw_art_path = CACHE_DIR / f"raw_{videoid}.png"
                        async with aiofiles.open(raw_art_path, "wb") as f:
                            await f.write(await resp.read())
        except Exception:
            raw_art_path = None

        if raw_art_path and Path(raw_art_path).exists():
            base_img = Image.open(raw_art_path).convert("RGBA")
        else:
            base_img = Image.open(DEFAULT_THUMB).convert("RGBA")

    except Exception as e:
        print(f"[gen_thumb Error - Using Default] {e}")
        try:
            base_img = Image.open(DEFAULT_THUMB).convert("RGBA")
            title = "KeyaraMusic"
            duration = "Unknown"
            channel = "KiyaraBots"
        except Exception:
            traceback.print_exc()
            return None

    try:
        rng = _rng_for(videoid)
        accent = rng.choice(ACCENTS)
        total = _parse_seconds(duration)
        progress = rng.uniform(0.08, 0.9) if total else 0.0

        canvas = _background(base_img, rng, accent)
        canvas = _glass_card(canvas, accent)
        _header(canvas, title, channel)
        _art_panel(canvas, base_img, rng)
        _progress_and_times(canvas, progress, total)
        _controls(canvas)

        # brand — card ke neeche center, subtle
        draw = ImageDraw.Draw(canvas)
        bfont = ImageFont.truetype(FONT_REGULAR_PATH, 24)
        bw = draw.textlength(app.username, font=bfont)
        draw.text(((CANVAS_W - bw) / 2, CANVAS_H - 46), app.username, font=bfont, fill=FAINT)

        out = CACHE_DIR / f"{videoid}_final.png"
        canvas.convert("RGB").save(out, quality=95, optimize=True)

        if raw_art_path and Path(raw_art_path).exists():
            try:
                raw_art_path.unlink(missing_ok=True)
            except Exception:
                pass

        return str(out)

    except Exception as e:
        print(f"[gen_thumb Processing Error] {e}")
        traceback.print_exc()
        return None

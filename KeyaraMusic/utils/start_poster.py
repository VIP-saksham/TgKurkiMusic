# KeyaraMusic — iOS-style start page poster
#
# /start ka visual: iOS lock-screen design language me personalized poster.
#   1. Background: branded art / seeded gradient (deterministic per chat)
#   2. Rounded monogram avatar, white ring + soft shadow
#   3. Auto-fit bold title + secondary subtitle (center aligned)
#   4. Glass "chips" row: uptime / RAM / CPU stats
#   5. Footer hint line
#
# Robustness:
#   - Stylized unicode names (small-caps etc.) jo bundled font me missing hain
#     wo readable ASCII me transliterate hote hain — naam hamesha dikhta hai.
#   - app.username guard: client start nahi hua to fallback text.
#   - Koi bhi failure par None return -> caller START_IMG_URL par girta hai.

import hashlib
import random
import traceback
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from KeyaraMusic import app

CACHE_DIR = Path("cache")
CACHE_DIR.mkdir(exist_ok=True)

W, H = 1320, 760

FONT_REGULAR_PATH = "KeyaraMusic/assets/font2.ttf"
FONT_BOLD_PATH = "KeyaraMusic/assets/font3.ttf"
BG_PATH = "KeyaraMusic/assets/start_bg.jpg"

_BG_CACHE = None
_FONT_CACHE = {}

LABEL = (255, 255, 255, 250)
SECONDARY = (235, 235, 245, 175)
TERTIARY = (235, 235, 245, 120)
CHIP_FILL = (255, 255, 255, 28)
CHIP_BORDER = (255, 255, 255, 46)

PALETTES = [
    ((24, 18, 43), (67, 38, 91), (255, 138, 190)),
    ((6, 22, 38), (12, 60, 86), (108, 213, 255)),
    ((26, 14, 40), (96, 30, 74), (255, 121, 198)),
    ((10, 26, 24), (24, 74, 60), (128, 240, 190)),
    ((22, 16, 48), (70, 40, 120), (176, 148, 255)),
    ((38, 18, 20), (120, 50, 40), (255, 170, 120)),
    ((16, 20, 26), (46, 56, 70), (168, 200, 255)),
    ((30, 22, 12), (110, 78, 30), (255, 205, 120)),
]

# ---------- text sanitization (stylized-font fallback) ----------------------

# Small-caps and common mathematical-alphanumeric blocks often have no glyph
# in the bundled fonts -> blank name on the poster. Map them to plain ASCII.
_CHAR_MAP = {
    "ᴀ": "a", "ʙ": "b", "ᴄ": "c", "ᴅ": "d", "ᴇ": "e", "ꜰ": "f", "ɢ": "g",
    "ʜ": "h", "ɪ": "i", "ᴊ": "j", "ᴋ": "k", "ʟ": "l", "ᴍ": "m", "ɴ": "n",
    "ᴏ": "o", "ᴘ": "p", "ǫ": "q", "ʀ": "r", "ꜱ": "s", "ᴛ": "t", "ᴜ": "u",
    "ᴠ": "v", "ᴡ": "w", "x": "x", "ʏ": "y", "ᴢ": "z",
    "𝐀": "A", "𝐁": "B", "𝐂": "C", "𝐃": "D", "𝐄": "E", "𝐅": "F", "𝐆": "G",
    "𝐇": "H", "𝐈": "I", "𝐉": "J", "𝐊": "K", "𝐋": "L", "𝐌": "M", "𝐍": "N",
    "𝐎": "O", "𝐏": "P", "𝐐": "Q", "𝐑": "R", "𝐒": "S", "𝐓": "T", "𝐔": "U",
    "𝐕": "V", "𝐖": "W", "𝐗": "X", "𝐘": "Y", "𝐙": "Z",
    "𝐚": "a", "𝐛": "b", "𝐜": "c", "𝐝": "d", "𝐞": "e", "𝐟": "f", "𝐠": "g",
    "𝐡": "h", "𝐢": "i", "𝐣": "j", "𝐤": "k", "𝐥": "l", "𝐦": "m", "𝐧": "n",
    "𝐨": "o", "𝐩": "p", "𝐪": "q", "𝐫": "r", "𝐬": "s", "𝐭": "t", "𝐮": "u",
    "𝐯": "v", "𝐰": "w", "𝐱": "x", "𝐲": "y", "𝐳": "z",
    "’": "'", "‘": "'", "“": '"', "”": '"', "–": "-", "—": "-",
}


def _readable(text: str) -> str:
    """Transliterate stylized chars the font can't show; drop undrawables."""
    if not text:
        return text
    out = []
    changed = False
    for ch in text:
        if ch in _CHAR_MAP:
            out.append(_CHAR_MAP[ch])
            changed = True
        else:
            out.append(ch)
    txt = "".join(out)
    if changed or txt != text:
        # strip anything still outside latin-1 — those are glyphs our fonts
        # almost certainly lack (would render blank/tofu)
        txt = "".join(ch for ch in txt if ch.isascii() or ch in "éèêáàíóúñüöäç")
    return txt or text


def _bot_username() -> str:
    try:
        return app.username or "KeyaraMusicBot"
    except Exception:
        return "KeyaraMusicBot"


def _rng_for(seed: str) -> random.Random:
    s = int(hashlib.sha256(seed.encode()).hexdigest()[:16], 16)
    return random.Random(s)


def _lerp(a, b, t):
    return int(a + (b - a) * t)


def _mix(c1, c2, t):
    return tuple(_lerp(a, b, t) for a, b in zip(c1, c2))


def _font(path, size):
    key = (path, size)
    if key not in _FONT_CACHE:
        _FONT_CACHE[key] = ImageFont.truetype(path, size)
    return _FONT_CACHE[key]


# ---------- backgrounds -----------------------------------------------------


def _cover_crop(img, w, h):
    scale = max(w / img.width, h / img.height)
    img = img.resize((int(img.width * scale) + 1, int(img.height * scale) + 1), Image.LANCZOS)
    x = (img.width - w) // 2
    y = (img.height - h) // 2
    return img.crop((x, y, x + w, y + h))


def _photo_background():
    global _BG_CACHE
    if _BG_CACHE is None:
        try:
            _BG_CACHE = Image.open(BG_PATH).convert("RGBA")
        except Exception:
            _BG_CACHE = False
    if _BG_CACHE is False:
        return None
    return _cover_crop(_BG_CACHE, W, H).filter(ImageFilter.GaussianBlur(3))


def _gradient_background(rng):
    c0, c1, c2 = PALETTES[rng.randrange(len(PALETTES))]
    base = Image.new("RGBA", (W, H))
    d = ImageDraw.Draw(base)
    for y in range(H):
        t = y / H
        col = _mix(c0, c1, t) if t < 0.6 else _mix(c1, c2, (t - 0.6) / 0.4)
        d.line([(0, y), (W, y)], fill=(*col, 255))
    blobs = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bd = ImageDraw.Draw(blobs)
    for _ in range(4):
        x, y = rng.randint(100, W - 100), rng.randint(80, H - 80)
        r = rng.randint(160, 300)
        bd.ellipse([x - r, y - r, x + r, y + r], fill=(*c2, 46))
    blobs = blobs.filter(ImageFilter.GaussianBlur(90))
    return Image.alpha_composite(base, blobs)


def _scrim(canvas):
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    stops = [(0.0, 90), (0.45, 50), (1.0, 140)]
    for y in range(H):
        t = y / H
        for (t0, a0), (t1, a1) in zip(stops, stops[1:]):
            if t0 <= t <= t1:
                k = (t - t0) / (t1 - t0)
                d.line([(0, y), (W, y)], fill=(0, 0, 0, int(a0 + (a1 - a0) * k)))
                break
    return Image.alpha_composite(canvas, overlay)


# ---------- avatar ----------------------------------------------------------


def _rounded_mask(size, radius):
    m = Image.new("L", (size, size), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=255)
    return m


def _monogram_avatar(letter, color):
    size = 520
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([0, 0, size - 1, size - 1], fill=(*_mix(color, (0, 0, 0), 0.45), 255))
    font = _font(FONT_BOLD_PATH, 210)
    bb = d.textbbox((0, 0), letter, font=font)
    lw, lh = bb[2] - bb[0], bb[3] - bb[1]
    d.text(((size - lw) / 2 - bb[0], (size - lh) / 2 - bb[1]), letter,
           font=font, fill=(255, 255, 255, 240))
    return img


def _avatar_with_ring(canvas, avatar_img, cx, y):
    size = 264
    shadow = Image.new("RGBA", (size + 120, size + 120), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).ellipse([60, 60, 60 + size, 60 + size], fill=(0, 0, 0, 160))
    canvas.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(28)), (cx - 60, y - 60 + 14))

    img = avatar_img.resize((size, size), Image.LANCZOS).convert("RGBA")
    mask = _rounded_mask(size, size // 2)
    img.putalpha(mask)
    canvas.alpha_composite(img, (cx, y))

    d = ImageDraw.Draw(canvas)
    d.ellipse([cx - 5, y - 5, cx + size + 5, y + size + 5],
              outline=(255, 255, 255, 70), width=5)
    return size


# ---------- typography + chips ----------------------------------------------


def _fit_text(draw, text, max_width, sizes=(64, 54, 46, 40, 34)):
    for size in sizes:
        font = _font(FONT_BOLD_PATH, size)
        if draw.textlength(text, font=font) <= max_width:
            return text, font
    font = _font(FONT_BOLD_PATH, sizes[-1])
    words = text.split()
    while words and draw.textlength(" ".join(words) + "...", font=font) > max_width:
        words.pop()
    return (" ".join(words) + "..."), font


def _chip(draw, text, font):
    tw = draw.textlength(text, font=font)
    w, h = int(tw) + 56, 58
    chip = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    cd = ImageDraw.Draw(chip)
    cd.rounded_rectangle([0, 0, w - 1, h - 1], radius=h // 2, fill=CHIP_FILL)
    cd.rounded_rectangle([0, 0, w - 1, h - 1], radius=h // 2, outline=CHIP_BORDER, width=2)
    cd.text(((w - tw) / 2, (h - 30) / 2 - 2), text, font=font, fill=LABEL)
    return chip


# ---------- entry ------------------------------------------------------------


def render_start_poster(*, title, subtitle, chips=None, footer=None,
                        seed="keyara", **_ignored):
    """iOS-style start poster -> cache path, ya None (fallback par)."""
    try:
        title = _readable(str(title))
        subtitle = _readable(str(subtitle))
        chips = [_readable(str(c)) for c in chips] if chips else None
        footer = _readable(str(footer)) if footer else None

        rng = _rng_for(str(seed))
        accent = PALETTES[rng.randrange(len(PALETTES))][2]

        bg = _photo_background()
        if bg is None:
            bg = _gradient_background(rng)
        canvas = bg.copy()

        canvas = _scrim(canvas)
        draw = ImageDraw.Draw(canvas)
        top_font = _font(FONT_REGULAR_PATH, 26)
        top_txt = "@" + _bot_username()
        tw = draw.textlength(top_txt, font=top_font)
        draw.text(((W - tw) / 2, 34), top_txt, font=top_font, fill=TERTIARY)

        av_y = 96
        mono_img = _monogram_avatar((title[:1] or "K").upper(), accent)
        av_size = _avatar_with_ring(canvas, mono_img, (W - 264) // 2, av_y)
        draw = ImageDraw.Draw(canvas)

        title_y = av_y + av_size + 34
        title_txt, title_font = _fit_text(draw, title, W - 200)
        tw = draw.textlength(title_txt, font=title_font)
        draw.text(((W - tw) / 2, title_y), title_txt, font=title_font, fill=LABEL)

        sub_font = _font(FONT_REGULAR_PATH, 32)
        sub_txt, sub_font = _fit_text(draw, subtitle, W - 220, sizes=(32,))
        sw = draw.textlength(sub_txt, font=sub_font)
        sub_y = title_y + title_font.size + 22
        draw.text(((W - sw) / 2, sub_y), sub_txt, font=sub_font, fill=SECONDARY)

        cy = 0
        if chips:
            chip_font = _font(FONT_REGULAR_PATH, 27)
            made = [_chip(draw, c, chip_font) for c in chips][:3]
            total = sum(m.width for m in made) + 18 * (len(made) - 1)
            x = (W - total) // 2
            cy = sub_y + 66
            for m in made:
                canvas.alpha_composite(m, (x, cy))
                x += m.width + 18
            draw = ImageDraw.Draw(canvas)

        dly = (cy + 58 + 40) if chips else (sub_y + 70)
        draw.line([(W / 2 - 110, dly), (W / 2 + 110, dly)],
                  fill=(255, 255, 255, 60), width=3)
        if footer:
            f_font = _font(FONT_REGULAR_PATH, 27)
            fw = draw.textlength(footer, font=f_font)
            draw.text(((W - fw) / 2, dly + 26), footer, font=f_font, fill=TERTIARY)

        out = CACHE_DIR / f"start_{hashlib.md5(str(seed).encode()).hexdigest()[:12]}.png"
        canvas.convert("RGB").save(out, quality=95, optimize=True)
        return str(out)

    except Exception:
        traceback.print_exc()
        return None

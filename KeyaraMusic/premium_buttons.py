# KiyaraMusic — Premium Button Icons
#
# Bot API 9.4 (Feb 2026) se inline buttons me custom-emoji icon support aaya:
# InlineKeyboardButton.icon_custom_emoji_id — button text ke aage animated
# premium emoji icon dikhta hai, SAB viewers ko (bot ke owner ka Telegram
# Premium active hona chahiye — KiyaraMusic owner ke paas hai).
#
# Kaam kaise karta hai:
#   apply_premium_buttons() -> pyrogram.types.InlineKeyboardButton ko Pkb se
#   replace kar deti hai. Iske baad codebase ki HAR button (yml strings wali
#   bhi) automatically apne emoji ka premium icon attach kar leti hai.
#   - Jo emoji PREMIUM_ICON map me hai -> premium animated icon
#   - Jo nahi hai (ALIAS se closest match bhi nahi) -> plain unicode emoji
#     ki tarah hi dikhega, kuch bhi nahi toot-ta.
#   - Purana pyrogram (icon support se pehle ka) ho to gracefully plain
#     button banta hai — zero breakage.
#
# Kill-switch: env PREMIUM_BUTTON_ICONS=0 -> icons off, sab normal.

import inspect
import os

from pyrogram.types import InlineKeyboardButton

# Owner ke premium account se harvest kiye gaye custom emoji pack IDs
# (premium_emoji.py wale hi IDs — button icons ke liye reuse).
PREMIUM_ICON = {
    "🌟": "5382311255656648590",
    "🔥": "5402406965252989103",
    "💎": "5201914481671682382",
    "⚡": "5411590687663608498",
    "👑": "5433758796289685818",
    "✨": "5451636889717062286",
    "✅": "5352825278672412291",
    "🎯": "5256131095094652290",
    "🚀": "5800956853462504394",
    "🎉": "5226928895189598791",
    "💯": "5341498088408234504",
    "🔈": "5388632425314140043",
    "💬": "5193161806473864879",
    "📢": "5881895671069413861",
    "⏳": "5451732530048802485",
    "📌": "6035379578682217500",
    "🙏": "5472189549473963781",
    "❤️": "5260413856093598223",
    "🛡️": "5465154440287757794",
    "⚠️": "5447644880824181073",
    "👤": "5814586811917278517",
    "🎮": "5319120041780726017",
    "💠": "5258500400918587241",
}

# Button-text emojis jo pack me direct nahi hain — closest premium emoji ka ID.
ALIAS = {
    "🥂": "✨",   # close
    "🔔": "✨",
    "🔙": "🌟",   # back
    "🔚": "🌟",
    "👀": "🔥",   # youtube / watch
    "🔧": "🎮",   # admin
    "🧰": "🛡️",  # maintenance
    "📺": "📢",   # channel play / rtmp
    "📣": "📢",   # channel / broadcast
    "🚫": "⚠️",  # blacklist
    "🛂": "✅",   # auth
    "🔨": "⚠️",  # g-ban
    "🎧": "🔥",   # play
    "🎵": "💯",   # song
    "🎶": "💯",
    "🔀": "✨",   # shuffle
    "🌱": "🎮",   # games
    "📂": "⚠️",  # bans
    "📁": "💠",   # repository
    "📰": "📢",   # telegraph
    "🏓": "⏳",   # ping
    "🕒": "⏳",   # speed options
    "🕓": "⏳",
    "🕘": "⏳",
    "🕤": "⏳",
    "🕛": "⏳",
    "🌋": "🚀",   # add me
    "🎄": "🔥",
    "⏬": "✨",   # download
    "🗣": "💬",   # tts
    "📨": "✅",   # fsub
    "🧟": "🎮",   # zombies
    "🕵": "👤",   # user info
    "🎲": "🎉",   # truth-dare
    "🧬": "💠",   # mongodb
    "🔤": "✨",   # font
    "🤬": "⚠️",  # gali
    "🤖": "🎮",   # bots
    "🔰": "✨",   # markdown
    "⛩": "📌",   # wish tag
    "💑": "❤️",  # couple
}

# Plain-text buttons (yml me emoji nahi) ke liye keyword fallback.
# Order matters: pehla match jeet-ta hai.
_KEYWORDS = [
    ("close", "✨"), ("back", "🌟"), ("support", "💬"), ("channel", "📢"),
    ("broadcast", "📢"), ("developer", "👤"), ("profile", "👤"),
    ("user info", "👤"), ("info", "👤"), ("network", "💠"), ("source", "⚡"),
    ("add", "🚀"), ("command", "💎"), ("feature", "💎"), ("help", "💎"),
    ("audio", "🔈"), ("video", "🎮"), ("live", "⚡"), ("stream", "⚡"),
    ("speed", "🚀"), ("play", "🔥"), ("shuffle", "✨"), ("seek", "🎯"),
    ("song", "💯"), ("music", "💯"), ("policy", "🛡️"), ("privacy", "🛡️"),
    ("maintenance", "🛡️"), ("game", "🎮"), ("gban", "⚠️"), ("g-ban", "⚠️"),
    ("blacklist", "⚠️"), ("bl-", "⚠️"), ("ban", "⚠️"), ("block", "⚠️"),
    ("gali", "⚠️"), ("auth", "✅"), ("vote", "✅"), ("yes", "✅"),
    ("fsub", "✅"), ("ping", "⏳"), ("timer", "⏳"), ("loop", "✨"),
    ("stats", "💯"), ("quality", "💎"), ("download", "✨"), ("tag", "📌"),
    ("tts", "💬"), ("link", "💠"), ("zombie", "🎮"), ("repo", "💠"),
    ("mongodb", "💠"), ("truth", "🎉"), ("dare", "🎉"), ("font", "✨"),
    ("markdown", "✨"), ("welcome", "🌟"), ("couple", "❤️"), ("admin", "🎮"),
]

# Small-caps Latin (ʙᴜᴛᴛᴏɴ ꜱᴛʏʟᴇ) -> ASCII, keyword match ke liye.
_SMALLCAPS = str.maketrans({
    "ᴀ": "a", "ʙ": "b", "ᴄ": "c", "ᴅ": "d", "ᴇ": "e", "ꜰ": "f", "ɢ": "g",
    "ʜ": "h", "ɪ": "i", "ᴊ": "j", "ᴋ": "k", "ʟ": "l", "ᴍ": "m", "ɴ": "n",
    "ᴏ": "o", "ᴘ": "p", "ʀ": "r", "ꜱ": "s", "ᴛ": "t", "ᴜ": "u", "ᴠ": "v",
    "ᴡ": "w", "ʏ": "y", "ᴢ": "z",
})


def _normalize(text: str) -> str:
    return text.replace("\ufe0f", "").translate(_SMALLCAPS).lower()


# Emoji + VS16 ke bina dono variants, fast lookup ke liye.
_ICON_LOOKUP = []
for _emo, _eid in PREMIUM_ICON.items():
    _ICON_LOOKUP.append((_emo.replace("\ufe0f", ""), _eid, _emo))
for _emo, _target in ALIAS.items():
    _eid = PREMIUM_ICON.get(_target)
    if _eid:
        _ICON_LOOKUP.append((_emo.replace("\ufe0f", ""), _eid, _emo))


# ---- button colors (Bot API 9.4 `style`) ----------------------------------
# SAB buttons blue (primary), sirf close/cancel/stop type red (danger).
# Purane clients normal button dikhaate hain.

_DANGER_KW = ["close", "forceclose", "cancel", "stop"]
_CB_DANGER = ("close", "cancel", "stop")


def style_for(text, callback_data=None):
    """Close-type -> DANGER (red), baaki SAB -> PRIMARY (blue)."""
    if not _SUPPORTS_STYLE or not _STYLES_ENABLED:
        return None
    n = _normalize(text) if text else ""
    if any(k in n for k in _DANGER_KW):
        return _BTN_STYLE.DANGER
    cb = str(callback_data or "").lower()
    if any(k in cb for k in _CB_DANGER):
        return _BTN_STYLE.DANGER
    return _BTN_STYLE.PRIMARY


def icon_for(text):
    """(premium_emoji_id, matched_emoji_char) ya (None, None)."""
    if not text:
        return None, None
    t = str(text)
    tn = t.replace("\ufe0f", "")
    for emo, eid, canonical in _ICON_LOOKUP:
        if emo and emo in tn:
            return eid, canonical
    n = _normalize(t)
    if n:
        for kw, emo in _KEYWORDS:
            if kw in n:
                return PREMIUM_ICON.get(emo), None
    return None, None


_ENABLED = os.environ.get("PREMIUM_BUTTON_ICONS", "1") != "0"
_STYLES_ENABLED = os.environ.get("PREMIUM_BUTTON_STYLES", "1") != "0"

try:
    _SIG = inspect.signature(InlineKeyboardButton.__init__).parameters
    _SUPPORTS_ICON = "icon_custom_emoji_id" in _SIG
    _SUPPORTS_STYLE = "style" in _SIG
except (ValueError, TypeError):
    _SUPPORTS_ICON = False
    _SUPPORTS_STYLE = False

_BTN_STYLE = None
if _SUPPORTS_STYLE:
    try:
        from pyrogram import enums as _enums

        _BTN_STYLE = getattr(_enums, "ButtonStyle", None)
        _SUPPORTS_STYLE = _BTN_STYLE is not None
    except Exception:
        _SUPPORTS_STYLE = False


def set_enabled(flag: bool):
    """Runtime toggle: set_enabled(False) -> sab buttons plain."""
    global _ENABLED
    _ENABLED = bool(flag)


class Pkb(InlineKeyboardButton):
    """InlineKeyboardButton with auto premium icon.

    text me se mapped emoji pakad ke icon_custom_emoji_id attach karta hai;
    emoji text se hata deta hai (icon hi dikhega), fallback text clean rehta
    hai. icon_custom_emoji_id explicitly pass karne pe auto-detect skip.
    """

    def __init__(
        self, text, icon_custom_emoji_id=None, keep_emoji=False, style=None, **kwargs
    ):
        if (
            _ENABLED
            and icon_custom_emoji_id is None
            and _SUPPORTS_ICON
            and text
        ):
            try:
                pid, emo = icon_for(text)
                if pid:
                    icon_custom_emoji_id = pid
                    if not keep_emoji and emo:
                        stripped = str(text).replace(emo, "")
                        stripped = stripped.replace(emo.replace("\ufe0f", ""), "")
                        stripped = " ".join(stripped.split())
                        if stripped:
                            text = stripped
            except Exception:
                pass
        if style is None:
            try:
                style = style_for(text, kwargs.get("callback_data"))
            except Exception:
                style = None
        if _SUPPORTS_ICON:
            kwargs["icon_custom_emoji_id"] = icon_custom_emoji_id
        if _SUPPORTS_STYLE and style is not None:
            kwargs["style"] = style
        super().__init__(text=text, **kwargs)


_applied = False


def apply_premium_buttons():
    """pyrogram.types.InlineKeyboardButton ko Pkb se replace karo.

    Isko sabse pehle (plugins load hone se pehle) ek baar call karna hai —
    KiyaraMusic/__init__.py se ho jata hai. Baad me jo bhi module
    `from pyrogram.types import InlineKeyboardButton` karega, use premium
    wala class milega.
    """
    global _applied
    if _applied:
        return
    import pyrogram.types as _pt

    _pt.InlineKeyboardButton = Pkb
    _applied = True

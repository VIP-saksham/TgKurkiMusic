# Keyara — premium (custom) emoji support
#
# Ye IDs owner ke premium account se harvest kiye gaye custom emoji pack IDs
# hain. `<emoji id="...">fallback</emoji>` HTML tag: premium viewers ko
# animated premium emoji dikhta hai, baaki sabko plain unicode fallback —
# Telegram khud handle karta hai, kuch toot-ta nahi.

import random

PREMIUM = {
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


def pe(char: str) -> str:
    """HTML <emoji> tag ya plain fallback — dono case me readable."""
    eid = PREMIUM.get(char)
    if eid:
        return f'<emoji id="{eid}">{char}</emoji>'
    return char


# /play ka pehla message — har baar alag random line, premium emoji ke saath.
SEARCHING = [
    ("🔍", "ꜱᴇᴀʀᴄʜɪɴɢ ʏᴏᴜʀ ꜱᴏɴɢ..."),
    ("🎧", "ꜰɪɴᴅɪɴɢ ᴛʜᴇ ʙᴇꜱᴛ ᴠᴇʀꜱɪᴏɴ ꜰᴏʀ ʏᴏᴜ..."),
    ("🎵", "ɢᴇᴛᴛɪɴɢ ʏᴏᴜʀ ᴛʀᴀᴄᴋ ʀᴇᴀᴅʏ..."),
    ("✨", "ꜱᴄᴀɴɴɪɴɢ ᴍɪʟʟɪᴏɴꜱ ᴏꜰ ꜱᴏɴɢꜱ ꜰᴏʀ ʏᴏᴜ..."),
    ("⚡", "ꜰᴇᴛᴄʜɪɴɢ ꜱᴜᴘᴇʀ Qᴜᴀʟɪᴛʏ ꜱᴏᴜɴᴅ..."),
    ("🔥", "ᴏɴ ɪᴛ! ꜰɪɴᴅɪɴɢ ʏᴏᴜʀ ᴍᴜꜱɪᴄ..."),
    ("💎", "ᴄᴜʀᴀᴛɪɴɢ ᴀ ᴘʀᴇᴍɪᴜᴍ ᴘʟᴀʏ ꜰᴏʀ ʏᴏᴜ..."),
]


def searching_text() -> str:
    """Random premium-tagged 'searching' message return karta hai."""
    emo, txt = random.choice(SEARCHING)
    return f"{pe(emo)} {txt}"

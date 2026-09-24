import os
import re
from dotenv import load_dotenv
from pyrogram import filters

load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID") or 0)
OWNER_USERNAME = os.getenv("OWNER_USERNAME", "TrueNakshu")
BOT_USERNAME = os.getenv("BOT_USERNAME", "KeyaraMusicBot")

MONGO_DB_URI = os.getenv("MONGO_DB_URI", None)
# Logging is optional; use 0 when no log group is configured.
LOG_GROUP_ID = int(os.getenv("LOG_GROUP_ID") or 0)
HEROKU_APP_NAME = os.getenv("HEROKU_APP_NAME")
HEROKU_API_KEY = os.getenv("HEROKU_API_KEY")

UPSTREAM_REPO = os.getenv("UPSTREAM_REPO", "https://github.com/VIP-saksham/KeyaraMusic")
UPSTREAM_BRANCH = os.getenv("UPSTREAM_BRANCH", "main")
GIT_TOKEN = os.getenv("GIT_TOKEN", None)

SUPPORT_CHANNEL = os.getenv("SUPPORT_CHANNEL", "https://t.me/TheHellBots")
SUPPORT_GROUP = os.getenv("SUPPORT_GROUP", "https://t.me/sunshine_gc")
INSTAGRAM = os.getenv("INSTAGRAM", "https://instagram.com/Imnakshuu")
YOUTUBE = os.getenv("YOUTUBE", "https://youtube.com/@NakshuPlayz")
GITHUB = os.getenv("GITHUB", "https://github.com/VIP-saksham")
DONATE = os.getenv("DONATE", "https://t.me/TheHellBots/1")
PRIVACY_LINK = os.getenv("PRIVACY_LINK", "https://graph.org/Privacy-Policy-09-19-185")

DURATION_LIMIT_MIN = int(os.getenv("DURATION_LIMIT", 300))
PLAYLIST_FETCH_LIMIT = int(os.getenv("PLAYLIST_FETCH_LIMIT", 25))

TG_AUDIO_FILESIZE_LIMIT = int(os.getenv("TG_AUDIO_FILESIZE_LIMIT", 104857600))
TG_VIDEO_FILESIZE_LIMIT = int(os.getenv("TG_VIDEO_FILESIZE_LIMIT", 2145386496))

SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID", None)
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET", None)

STRING1 = os.getenv("STRING_SESSION", None)
# Channel audio cache (@teamjatayu) — pehla play YT se, agla play channel se instant
CACHE_CHANNEL_ID = int(os.getenv("CACHE_CHANNEL_ID") or -1004495764762)
CACHE_MONGO_DB = os.getenv("CACHE_MONGO_DB", "KurkiMusicCache")
CACHE_UPLOAD_ENABLED = str(os.getenv("CACHE_UPLOAD_ENABLED", "true")).lower() in ("1", "true", "yes", "on")
STRING2 = os.getenv("STRING_SESSION2", None)
STRING3 = os.getenv("STRING_SESSION3", None)
STRING4 = os.getenv("STRING_SESSION4", None)
STRING5 = os.getenv("STRING_SESSION5", None)

AUTO_LEAVING_ASSISTANT = bool(os.getenv("AUTO_LEAVING_ASSISTANT", False))

START_IMG_URL = os.getenv("START_IMG_URL", "https://files.catbox.moe/an0gbb.png")
PING_IMG_URL = "https://files.catbox.moe/an0gbb.png"
PLAYLIST_IMG_URL = "https://files.catbox.moe/an0gbb.png"
STATS_IMG_URL = "https://files.catbox.moe/zd024v.png"
TELEGRAM_AUDIO_URL = "https://files.catbox.moe/an0gbb.png"
TELEGRAM_VIDEO_URL = "https://files.catbox.moe/an0gbb.png"
STREAM_IMG_URL = "https://files.catbox.moe/an0gbb.png"
SOUNCLOUD_IMG_URL = "https://files.catbox.moe/an0gbb.png"
YOUTUBE_IMG_URL = "https://files.catbox.moe/an0gbb.png"
SPOTIFY_ARTIST_IMG_URL = "https://files.catbox.moe/an0gbb.png"
SPOTIFY_ALBUM_IMG_URL = "https://files.catbox.moe/an0gbb.png"
SPOTIFY_PLAYLIST_IMG_URL = "https://files.catbox.moe/an0gbb.png"

BANNED_USERS = filters.user()
adminlist = {}
lyrical = {}
votemode = {}
autoclean = []
confirmer = {}

TEMP_DB_FOLDER = "tempdb"

def time_to_seconds(time):
    stringt = str(time)
    return sum(int(x) * 60**i for i, x in enumerate(reversed(stringt.split(":"))))

DURATION_LIMIT = int(time_to_seconds(f"{DURATION_LIMIT_MIN}:00"))
ERROR_FORMAT = OWNER_ID
DT_Management = "\x40\x53\x68\x72\x75\x74\x69\x53\x75\x70\x70\x6f\x72\x74\x42\x6f\x74"

if SUPPORT_CHANNEL and not re.match(r"(?:http|https)://", SUPPORT_CHANNEL):
    raise SystemExit(
        "[ERROR] - SUPPORT_CHANNEL URL is invalid. It must start with https://"
    )

if SUPPORT_GROUP:
    if not re.match(r"(?:http|https)://", SUPPORT_GROUP):
        raise SystemExit(
            "[ERROR] - SUPPORT_GROUP URL is invalid. It must start with https://"
        )

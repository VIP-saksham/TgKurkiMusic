"""
youtube.py — KurkiMusic merged engine (FAST)

Priority (audio play ke liye):
  1. Local disk cache  (downloads/{vid}.mp3)
  2. Telegram channel cache (@teamjatayu via Mongo index)
  3. HellAPI /api/stream  (localhost — sabse fast online path)
  4. yt-dlp + YouTube Premium cookies (fallback)

Har naya download background me channel + Mongo me cache ho jata hai —
next play ekdum instant (0.1s-level, no YouTube call).

Env:
  HELLAPI_URL=http://localhost:8000
  HELLAPI_KEY=HellAPIxxxx
  YTDLP_COOKIES=/root/nakshu/kurkimusic/yt_cookies.txt
"""

import asyncio
import os
import re
from urllib.parse import parse_qs, urlparse
from typing import Union

import aiohttp
import yt_dlp

try:
    from pyrogram.enums import MessageEntityType
    from pyrogram.types import Message
    _HAS_PYROGRAM = True
except Exception:
    Message = object
    MessageEntityType = None
    _HAS_PYROGRAM = False

from ..core.channelcache import fetch_cached_file, cache_from_download

# ── Config ───────────────────────────────────────────────────────────────────
API_URL = (os.environ.get("HELLAPI_URL") or "").rstrip("/")
API_KEY = os.environ.get("HELLAPI_KEY", "")
HELLAPI_ON = bool(API_URL and API_KEY)

_COOKIES = os.environ.get("YTDLP_COOKIES", "yt_cookies.txt")
_COOKIES = _COOKIES if os.path.isabs(_COOKIES) else os.path.join(os.getcwd(), _COOKIES)

_HEADERS = {"x-api-key": API_KEY, "Connection": "keep-alive"} if HELLAPI_ON else {}
_TIMEOUT = aiohttp.ClientTimeout(total=60, connect=10)
_VTIMEOUT = aiohttp.ClientTimeout(total=180, connect=10)

DOWNLOAD_DIR = os.environ.get("DOWNLOAD_DIR", "downloads")

_connector = None


def _get_connector():
    global _connector
    if _connector is None or _connector.closed:
        _connector = aiohttp.TCPConnector(limit=20, ttl_dns_cache=300, use_dns_cache=True)
    return _connector


_VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")


def _normalise_video_url(value, videoid=False):
    raw = str(value or "").strip()
    if videoid:
        raw = raw.split("&", 1)[0].split("?", 1)[0]
        if not _VIDEO_ID_RE.fullmatch(raw):
            raise ValueError("Expected an 11-character YouTube video ID.")
        return f"https://www.youtube.com/watch?v={raw}"
    if _VIDEO_ID_RE.fullmatch(raw):
        return f"https://www.youtube.com/watch?v={raw}"
    parsed = urlparse(raw)
    host = (parsed.hostname or "").lower()
    if host == "youtu.be":
        candidate = parsed.path.strip("/").split("/", 1)[0]
    elif host.endswith("youtube.com"):
        if parsed.path == "/watch":
            candidate = parse_qs(parsed.query).get("v", [""])[0]
        elif parsed.path.startswith(("/shorts/", "/embed/")):
            candidate = parsed.path.split("/")[2]
        else:
            candidate = ""
    else:
        candidate = ""
    if not _VIDEO_ID_RE.fullmatch(candidate):
        raise ValueError("Only a YouTube URL or 11-char video ID is supported here.")
    return f"https://www.youtube.com/watch?v={candidate}"


def _video_id(value, videoid=False):
    return parse_qs(urlparse(_normalise_video_url(value, videoid)).query)["v"][0]


def _clean_id(link) -> str:
    link = str(link or "")
    if "v=" in link:
        return link.split("v=")[-1].split("&")[0]
    if "youtu.be/" in link:
        return link.split("youtu.be/")[-1].split("?")[0].split("&")[0]
    return link.split("?")[0].split("&")[0]


def _time_to_seconds(t):
    try:
        parts = [int(x) for x in str(t).split(":")]
        return sum(x * (60 ** i) for i, x in enumerate(reversed(parts)))
    except Exception:
        return 0


def _seconds_to_min(seconds):
    try:
        m, s = divmod(int(seconds or 0), 60)
        h, m = divmod(m, 60)
        return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"
    except Exception:
        return "0:00"


seconds_to_min = _seconds_to_min


async def _bot_app():
    # Channel se download ke liye ASSISTANT (user account) better hai —
    # bots ko channel history ke liye admin hona padta hai, users ko nahi.
    try:
        from KeyaraMusic import userbot
        if userbot and getattr(userbot, "one", None):
            return userbot.one
    except Exception:
        pass
    try:
        from KeyaraMusic import app
        return app
    except Exception:
        return None


# ── Channel cache (Telegram) ─────────────────────────────────────────────────

async def _try_channel_cache(vidid: str):
    if not vidid or not _VIDEO_ID_RE.fullmatch(vidid):
        return None
    app = await _bot_app()
    if app is None:
        return None
    try:
        path = await fetch_cached_file(app, vidid)
    except Exception:
        return None
    if path and os.path.exists(path) and os.path.getsize(path) > 0:
        return path
    return None


def _backfill_channel_cache(vidid, path, title=""):
    """Background upload — play ko block nahi karta."""
    if not vidid or not _VIDEO_ID_RE.fullmatch(vidid):
        return
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(cache_from_download(None, vidid, path, title or "", ""))
    except Exception:
        pass


# ── HellAPI helpers ──────────────────────────────────────────────────────────

def _cleanup(path):
    try:
        if path and os.path.exists(path):
            os.remove(path)
    except Exception:
        pass


async def _api_get(path, params, timeout=None, retries=1):
    if not HELLAPI_ON:
        raise ConnectionError("HellAPI disabled")
    url = f"{API_URL}{path}"
    last = None
    for attempt in range(retries + 1):
        try:
            async with aiohttp.ClientSession(connector=_get_connector(), connector_owner=False) as s:
                async with s.get(url, params=params, headers=_HEADERS, timeout=timeout or _TIMEOUT) as r:
                    if r.status != 200:
                        raise ConnectionError(f"HellAPI {r.status}: {(await r.text())[:80]}")
                    return await r.json()
        except Exception as e:
            last = e
            if attempt < retries:
                await asyncio.sleep(1.0)
    raise last or ConnectionError("HellAPI request failed")


async def _download_file(url, path, timeout=None):
    async with aiohttp.ClientSession(connector=_get_connector(), connector_owner=False) as s:
        async with s.get(url, timeout=timeout or _VTIMEOUT) as r:
            if r.status != 200:
                raise ConnectionError(f"Download failed: HTTP {r.status}")
            with open(path, "wb") as f:
                async for chunk in r.content.iter_chunked(131072):
                    f.write(chunk)


async def _ydl_search(query, limit=1):
    """Song-name search: HellAPI pehle, yt-dlp+cookies fallback."""
    if HELLAPI_ON:
        try:
            data = await _api_get("/search", {"q": query, "limit": max(1, min(int(limit), 10))})
            out = []
            for r in data.get("results", []):
                vid = r.get("id") or ""
                if not vid:
                    continue
                out.append({
                    "id": vid, "vidid": vid,
                    "title": r.get("title") or "Unknown",
                    "link": r.get("url") or f"https://www.youtube.com/watch?v={vid}",
                    "url": r.get("url") or f"https://www.youtube.com/watch?v={vid}",
                    "duration": r.get("duration"),
                    "duration_min": _seconds_to_min(r.get("duration")),
                    "thumb": r.get("thumbnail") or "",
                    "thumbnail": r.get("thumbnail") or "",
                })
            if out:
                return out
        except Exception:
            pass
    # yt-dlp fallback
    try:
        def _search():
            opts = {
                "quiet": True, "no_warnings": True, "noplaylist": True,
                "extract_flat": "in_playlist", "default_search": "ytsearch",
            }
            if os.path.exists(_COOKIES) and os.path.getsize(_COOKIES) > 50:
                opts["cookiefile"] = _COOKIES
            with yt_dlp.YoutubeDL(opts) as y:
                info = y.extract_info(f"ytsearch{max(1, min(int(limit), 10))}:{query}", download=False)
            entries = info.get("entries") or []
            out = []
            for e in entries:
                vid = e.get("id")
                if not vid:
                    continue
                out.append({
                    "id": vid, "vidid": vid,
                    "title": e.get("title") or "Unknown",
                    "link": f"https://www.youtube.com/watch?v={vid}",
                    "url": f"https://www.youtube.com/watch?v={vid}",
                    "duration": e.get("duration"),
                    "duration_min": _seconds_to_min(e.get("duration")),
                    "thumb": (e.get("thumbnails") or [{}])[0].get("url", "") if e.get("thumbnails") else "",
                    "thumbnail": "",
                })
            return out
        return await asyncio.to_thread(_search)
    except Exception:
        return []


# ── yt-dlp download fallback (Premium cookies) ───────────────────────────────

def _ytdlp_download(vidid, media_type="audio"):
    out = os.path.join(DOWNLOAD_DIR, f"{vidid}.%(ext)s")
    opts = {
        "outtmpl": out, "quiet": True, "no_warnings": True, "noplaylist": True,
        "nocheckcertificate": True, "retries": 2, "socket_timeout": 20,
    }
    if media_type == "audio":
        opts["format"] = "bestaudio[ext=m4a]/bestaudio/best"
        opts["postprocessors"] = [{
            "key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192",
        }]
    else:
        opts["format"] = "best[height<=720][ext=mp4]/best[height<=720]/best"
    if os.path.exists(_COOKIES) and os.path.getsize(_COOKIES) > 50:
        opts["cookiefile"] = _COOKIES
    with yt_dlp.YoutubeDL(opts) as y:
        info = y.extract_info(f"https://www.youtube.com/watch?v={vidid}", download=True)
        path = info.get("requested_downloads", [{}])[0].get("filepath") or y.prepare_filename(info)
        if media_type == "audio" and path.endswith((".m4a", ".webm", ".opus")):
            mp3 = os.path.splitext(path)[0] + ".mp3"
            if os.path.exists(mp3):
                path = mp3
        if not os.path.exists(path):
            raise Exception("yt-dlp: file nahi mili")
        return path


# ── Core media fetch: cache → HellAPI → yt-dlp ───────────────────────────────

async def _hellapi_stream_url(vidid):
    """HellAPI se stream URL (download nahi) — pytgcalls direct stream kar sakta hai."""
    if not HELLAPI_ON:
        return None
    try:
        data = await _api_get(
            "/api/stream",
            {"url": f"https://www.youtube.com/watch?v={vidid}", "type": "audio"},
            timeout=_VTIMEOUT,
        )
        return data.get("stream_url") or data.get("direct_url") or data.get("url")
    except Exception:
        return None


def _bg_channel_backfill(vidid, title=""):
    """Background: yt-dlp download → channel upload (future instant plays)."""
    async def _job():
        try:
            app = await _bot_app()
            if app is None:
                return
            from ..core.channelcache import get_cached
            if await get_cached(vidid):
                return
            path = await asyncio.to_thread(_ytdlp_download, vidid, "audio")
            ext_path = os.path.join(DOWNLOAD_DIR, f"{vidid}.mp3")
            if path != ext_path and os.path.exists(path):
                os.replace(path, ext_path)
                path = ext_path
            if os.path.exists(path) and os.path.getsize(path) > 0:
                await cache_from_download(app, vidid, path, title, "")
                try:
                    os.remove(path)
                except Exception:
                    pass
        except Exception:
            pass
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(_job())
    except Exception:
        pass


async def _fetch_media(vidid, media_type="audio"):
    """Returns local file path / stream URL ya None.
    Audio me HellAPI stream URL direct return hota hai — 0 download wait,
    play ~0.1s me start. Channel cache background me banta rehta hai."""
    if not vidid or not _VIDEO_ID_RE.fullmatch(vidid):
        return None
    ext = "mp4" if media_type == "video" else "mp3"
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    file_path = os.path.join(DOWNLOAD_DIR, f"{vidid}.{ext}")

    # 1) local disk — 0ms
    if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
        return file_path

    if media_type == "audio":
        # 2) HellAPI direct stream URL — download skip, instant play
        stream_url = await _hellapi_stream_url(vidid)
        if stream_url:
            _bg_channel_backfill(vidid)
            return stream_url

        # 3) Telegram channel cache (~2s)
        cached = await _try_channel_cache(vidid)
        if cached:
            return cached
    else:
        # video: channel cache nahi, HellAPI download
        if HELLAPI_ON:
            try:
                data = await _api_get(
                    "/api/stream",
                    {"url": f"https://www.youtube.com/watch?v={vidid}", "type": "video"},
                    timeout=_VTIMEOUT,
                )
                stream_url = data.get("stream_url") or data.get("direct_url") or data.get("url")
                if stream_url:
                    await _download_file(stream_url, file_path)
                    if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                        return file_path
            except Exception:
                _cleanup(file_path)

    # 4) yt-dlp + cookies fallback
    try:
        path = await asyncio.to_thread(_ytdlp_download, vidid, media_type)
        if media_type == "audio":
            if path != file_path and os.path.exists(path):
                os.replace(path, file_path)
            _backfill_channel_cache(vidid, file_path)
            return file_path if os.path.exists(file_path) else path
        return path if os.path.exists(path) else None
    except Exception:
        _cleanup(file_path)
        return None


# ── Standalone functions (direct imports) ────────────────────────────────────

async def download_song(link: str) -> str:
    try:
        vidid = _video_id(link)
    except ValueError:
        vidid = _clean_id(link)
    return await _fetch_media(vidid, "audio")


async def download_video(link: str) -> str:
    try:
        vidid = _video_id(link)
    except ValueError:
        vidid = _clean_id(link)
    return await _fetch_media(vidid, "video")


# ── YouTubeAPI class ─────────────────────────────────────────────────────────

class YouTubeAPI:

    def __init__(self):
        self.base = "https://www.youtube.com/watch?v="
        self.regex = r"(?:youtube\.com|youtu\.be)"
        self.listbase = "https://youtube.com/playlist?list="
        self.reg = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

    # Yukki-style: song-NAME ya URL/ID → (track_details, vidid)
    async def name(self, link: str, videoid=None):
        if videoid:
            link = self.base + link
        try:
            vidid = _video_id(link)
            watch = f"https://www.youtube.com/watch?v={vidid}"
            if HELLAPI_ON:
                data = await _api_get("/info", {"url": watch})
                d = data.get("data", {})
                return {
                    "title": d.get("title") or "Unknown",
                    "link": watch,
                    "vidid": vidid,
                    "duration_min": _seconds_to_min(d.get("duration_seconds")),
                }, vidid
            results = await _ydl_search(watch, limit=1)
            if results:
                r = results[0]
                return {"title": r["title"], "link": watch, "vidid": vidid,
                        "duration_min": r["duration_min"]}, vidid
            return {"title": "Unknown", "link": watch, "vidid": vidid,
                    "duration_min": "0:00"}, vidid
        except ValueError:
            pass
        results = await _ydl_search(link, limit=1)
        if not results:
            raise ValueError(f"No results found for: {link}")
        r = results[0]
        return {"title": r["title"], "link": r["link"], "vidid": r["id"],
                "duration_min": r["duration_min"]}, r["id"]

    async def exists(self, link: str, videoid=None) -> bool:
        try:
            _normalise_video_url(link, videoid)
            return True
        except ValueError:
            return False

    async def url(self, message_1):
        if not _HAS_PYROGRAM:
            return None
        messages = [message_1]
        if message_1.reply_to_message:
            messages.append(message_1.reply_to_message)
        for message in messages:
            if message.entities:
                for entity in message.entities:
                    if entity.type == MessageEntityType.URL:
                        text = message.text or message.caption
                        return text[entity.offset: entity.offset + entity.length]
            elif message.caption_entities:
                for entity in message.caption_entities:
                    if entity.type == MessageEntityType.TEXT_LINK:
                        return entity.url
        return None

    def _clean(self, link: str) -> str:
        return link.split("&")[0] if "&" in link else link

    async def details(self, link: str, videoid=None):
        """Returns: title, duration_min, duration_sec, thumbnail, vidid
        Song-NAME bhi accept karta hai (search karke pehla result)."""
        try:
            vidid = _video_id(link, videoid)
        except ValueError:
            res = await _ydl_search(str(link), limit=1)
            if not res:
                raise ValueError(f"No results found for: {link}")
            r = res[0]
            return r["title"], r["duration_min"], _time_to_seconds(r["duration_min"]), r["thumb"], r["id"]
        watch = f"https://www.youtube.com/watch?v={vidid}"
        title, dur_min, thumb = "Unknown", "0:00", ""
        if HELLAPI_ON:
            try:
                data = await _api_get("/info", {"url": watch})
                d = data.get("data", {})
                title = d.get("title") or title
                dur_min = _seconds_to_min(d.get("duration_seconds"))
                thumb = d.get("thumbnail") or ""
            except Exception:
                pass
        if title == "Unknown":
            try:
                res = await _ydl_search(watch, limit=1)
                if res:
                    title = res[0]["title"]
                    dur_min = res[0]["duration_min"]
                    thumb = res[0]["thumb"] or thumb
            except Exception:
                pass
        return title, dur_min, _time_to_seconds(dur_min), thumb, vidid

    async def title(self, link: str, videoid=None) -> str:
        t, *_ = await self.details(link, videoid)
        return t

    async def duration(self, link: str, videoid=None) -> str:
        _, d, *_ = await self.details(link, videoid)
        return d

    async def thumbnail(self, link: str, videoid=None) -> str:
        _, _, _, t, _ = await self.details(link, videoid)
        return t

    async def track(self, link: str, videoid=None):
        """Returns: (track_details dict, vidid)
        Song-NAME bhi chalta hai — search karke best result."""
        try:
            vidid = _video_id(link, videoid)
        except ValueError:
            res = await _ydl_search(str(link), limit=1)
            if not res:
                raise ValueError(f"No results found for: {link}")
            r = res[0]
            return {
                "title": r["title"], "link": r["link"], "vidid": r["id"],
                "duration_min": r["duration_min"], "thumb": r["thumb"],
            }, r["id"]
        watch = f"https://www.youtube.com/watch?v={vidid}"
        title, dur_min, thumb = "Unknown", "0:00", ""
        if HELLAPI_ON:
            try:
                data = await _api_get("/info", {"url": watch})
                d = data.get("data", {})
                title = d.get("title") or title
                dur_min = _seconds_to_min(d.get("duration_seconds"))
                thumb = d.get("thumbnail") or ""
            except Exception:
                pass
        if title == "Unknown":
            try:
                res = await _ydl_search(watch, limit=1)
                if res:
                    title = res[0]["title"]
                    dur_min = res[0]["duration_min"]
                    thumb = res[0]["thumb"] or thumb
            except Exception:
                pass
        return {
            "title": title, "link": watch, "vidid": vidid,
            "duration_min": dur_min, "thumb": thumb,
        }, vidid

    async def formats(self, link: str, videoid=None):
        link = _normalise_video_url(link, videoid)
        result = []
        if HELLAPI_ON:
            try:
                data = await _api_get("/formats", {"url": link})
                for f in data.get("formats", []):
                    fmt_str = f.get("resolution") or f.get("ext") or ""
                    if "dash" in fmt_str.lower():
                        continue
                    result.append({
                        "format": f"{f.get('format_id')} - {fmt_str}",
                        "filesize": f.get("filesize_approx"),
                        "format_id": f.get("format_id"),
                        "ext": f.get("ext"),
                        "format_note": f.get("resolution") or "",
                        "yturl": link,
                    })
                if result:
                    return result, link
            except Exception:
                pass
        def _formats():
            with yt_dlp.YoutubeDL({"quiet": True}) as y:
                r = y.extract_info(link, download=False)
            out = []
            for fmt in r.get("formats", []):
                try:
                    if "dash" not in str(fmt.get("format", "")).lower():
                        out.append({
                            "format": fmt["format"], "filesize": fmt.get("filesize"),
                            "format_id": fmt["format_id"], "ext": fmt["ext"],
                            "format_note": fmt.get("format_note") or "", "yturl": link,
                        })
                except Exception:
                    continue
            return out
        result = await asyncio.to_thread(_formats)
        return result, link

    async def slider(self, link: str, query_type: int, videoid=None):
        if not videoid and not re.search(self.regex, str(link or "")):
            res = await _ydl_search(link, limit=max(1, query_type + 1))
            if res and len(res) > query_type:
                r = res[query_type]
                return r["title"], r["duration_min"], r["thumb"], r["id"]
            raise ValueError("No search results")
        title, duration, _, thumbnail, vidid = await self.details(link, videoid)
        return title, duration, thumbnail, vidid

    async def playlist(self, link, limit, user_id, videoid=None):
        """KeyaraMusic contract: list of vidid strings."""
        if videoid:
            link = self.listbase + link
        link = self._clean(link)
        ids = []
        if HELLAPI_ON:
            try:
                data = await _api_get("/info", {"url": link}, retries=0)
                entries = data.get("data", {}).get("entries", []) or []
                for e in entries[: max(1, int(limit))]:
                    if isinstance(e, dict) and e.get("id"):
                        ids.append(e["id"])
            except Exception:
                pass
        if not ids:
            try:
                def _plist():
                    opts = {"quiet": True, "no_warnings": True,
                            "extract_flat": "in_playlist", "noplaylist": False}
                    if os.path.exists(_COOKIES) and os.path.getsize(_COOKIES) > 50:
                        opts["cookiefile"] = _COOKIES
                    with yt_dlp.YoutubeDL(opts) as y:
                        info = y.extract_info(link, download=False)
                    out = []
                    for e in (info.get("entries") or [])[: max(1, int(limit))]:
                        if e and e.get("id"):
                            out.append(e["id"])
                    return out
                ids = await asyncio.to_thread(_plist)
            except Exception:
                return []
        return ids

    async def related(self, videoid: str, exclude_ids=None):
        exclude = set(exclude_ids or [])
        exclude.add(videoid)
        try:
            _, _, _, _, vid = await self.details(videoid, True)
            seed_title = await self.title(videoid, True)
            res = await _ydl_search(seed_title, limit=10)
            for r in res:
                if r["id"] not in exclude and r.get("duration"):
                    return {
                        "title": r["title"], "vidid": r["id"],
                        "duration_min": r["duration_min"], "thumb": r["thumb"],
                        "link": r["url"],
                    }
        except Exception:
            pass
        return None

    async def video(self, link: str, videoid=None):
        """Returns: (1, file_path) or (0, error_msg)"""
        try:
            vidid = _video_id(link, videoid)
            path = await _fetch_media(vidid, "video")
            if path:
                return 1, path
            return 0, "Video download failed"
        except Exception as e:
            return 0, str(e)

    async def download(self, link, mystic, video=None, videoid=None,
                       songaudio=None, songvideo=None, format_id=None, title=None):
        """Main download — /play, /vplay. Returns (path, True) or (None, False)."""
        try:
            vidid = _video_id(link, videoid)
            media_type = "video" if (video or songvideo) else "audio"
            path = await _fetch_media(vidid, media_type)
            if path:
                return path, True
            return None, False
        except Exception:
            return None, False


YouTube = YouTubeAPI()

import asyncio
import os
import re

import config
from ..logging import LOGGER

# ----------------------------------------------------------------
# Channel Audio Cache — @teamjatayu
# First play: YouTube se download → audio channel me upload → Mongo index.
# Next play: Telegram channel se direct download (YouTube skip, ekdum fast).
# ----------------------------------------------------------------

CHANNEL_ID = getattr(config, "CACHE_CHANNEL_ID", -1004495764762)
CACHE_MONGO_DB = getattr(config, "CACHE_MONGO_DB", "KurkiMusicCache")
CACHE_UPLOAD_ENABLED = getattr(config, "CACHE_UPLOAD_ENABLED", True)

_cache_col = None
_lock = asyncio.Lock()


def _collection():
    global _cache_col
    if _cache_col is None:
        try:
            from motor.motor_asyncio import AsyncIOMotorClient

            client = AsyncIOMotorClient(config.MONGO_DB_URI)
            _cache_col = client[CACHE_MONGO_DB].tracks
        except Exception as e:
            LOGGER(__name__).error(f"cache mongo init failed: {e}")
            _cache_col = False
    if _cache_col is False or _cache_col is None:
        return None
    return _cache_col


def _video_id(link: str) -> str:
    if "v=" in link:
        return link.split("v=")[-1].split("&")[0]
    if "youtu.be/" in link:
        return link.split("youtu.be/")[-1].split("?")[0].split("&")[0]
    return link.split("?")[0]


async def get_cached(videoid: str):
    """Mongo index se cached audio ka Telegram file_id laao."""
    col = _collection()
    if col is None:
        return None
    try:
        doc = await col.find_one({"_id": str(videoid)})
        if doc and doc.get("file_id"):
            return doc
    except Exception as e:
        LOGGER(__name__).warning(f"cache lookup failed: {e}")
    return None


async def save_cache(videoid: str, title: str, duration_min: str, file_id: str, msg_id: int = None):
    col = _collection()
    if col is None:
        return
    try:
        await col.update_one(
            {"_id": str(videoid)},
            {
                "$set": {
                    "file_id": file_id,
                    "msg_id": msg_id,
                    "title": title,
                    "duration_min": duration_min,
                    "channel": CHANNEL_ID,
                }
            },
            upsert=True,
        )
    except Exception as e:
        LOGGER(__name__).warning(f"cache save failed: {e}")


async def _upload_to_channel(client, path: str, title: str, duration_min: str, videoid: str):
    """Audio ko cache channel (@teamjatayu) me upload karo aur file_id wapas laao."""
    if client is None:
        try:
            from KeyaraMusic import app as client
        except Exception:
            return None
    caption = title
    if duration_min:
        caption = f"{title} [{duration_min}]"
    msg = await client.send_audio(
        CHANNEL_ID,
        audio=path,
        caption=caption[:1000],
        file_name=f"{videoid}.mp3",
    )
    file_id = None
    if msg and msg.audio:
        file_id = msg.audio.file_id
    elif msg and getattr(msg, "document", None):
        file_id = msg.document.file_id
    msg_id = msg.id if msg else None
    return file_id, msg_id


async def cache_from_download(client, videoid: str, path: str, title: str, duration_min: str):
    """Download ke baad background me channel + Mongo cache bharo (play ko block nahi karta)."""
    if not CACHE_UPLOAD_ENABLED:
        return
    if not CHANNEL_ID or not videoid:
        return
    videoid = _video_id(str(videoid))
    if await get_cached(videoid):
        return
    async with _lock:
        if await get_cached(videoid):
            return
        try:
            file_id, msg_id = await _upload_to_channel(client, path, title, duration_min, videoid)
            if file_id:
                await save_cache(videoid, title, duration_min, file_id, msg_id)
                LOGGER(__name__).info(f"cached in channel: {videoid} -> {title[:40]}")
        except Exception as e:
            LOGGER(__name__).warning(f"channel upload failed ({videoid}): {e}")


async def fetch_cached_file(app, videoid: str, dest_dir: str = "downloads"):
    """Cached audio channel se local file me download karo (instant play ke liye)."""
    doc = await get_cached(videoid)
    if not doc:
        return None
    os.makedirs(dest_dir, exist_ok=True)
    path = os.path.join(dest_dir, f"cache_{videoid}.mp3")
    if os.path.exists(path) and os.path.getsize(path) > 0:
        return path
    # Fresh reference lo — file_id ka file_reference expire ho jata hai
    msg = None
    if doc.get("msg_id"):
        try:
            msg = await app.get_messages(CHANNEL_ID, doc["msg_id"])
        except Exception:
            msg = None
    try:
        if msg and (msg.audio or getattr(msg, "document", None)):
            await app.download_media(msg, file_name=path)
        else:
            await app.download_media(doc["file_id"], file_name=path)
        if os.path.exists(path) and os.path.getsize(path) > 0:
            # naya file_id bhi update kar do (fresh reference)
            media = getattr(msg, "audio", None) or getattr(msg, "document", None) if msg else None
            if media and media.file_id and media.file_id != doc.get("file_id"):
                try:
                    await save_cache(videoid, doc.get("title") or "", doc.get("duration_min") or "", media.file_id, doc.get("msg_id"))
                except Exception:
                    pass
            return path
    except Exception as e:
        LOGGER(__name__).warning(f"cache file download failed ({videoid}): {e}")
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception:
            pass
    return None


async def seed_from_channel(app, limit: int = 100):
    """Bot start hote hi channel ke purane audio messages ko Mongo me index karo."""
    col = _collection()
    if col is None:
        return
    count = 0
    try:
        async for msg in app.get_chat_history(CHANNEL_ID, limit=limit):
            audio = getattr(msg, "audio", None)
            doc = getattr(msg, "document", None)
            media = audio or doc
            if not media:
                continue
            title = media.file_name or (msg.caption or media.title or "").split("[")[0].strip()
            dur = getattr(media, "duration", 0)
            dur_min = f"{dur // 60}:{dur % 60:02d}" if dur else ""
            vid = None
            if media.file_name:
                m = re.match(r"^(-?\d+)", media.file_name)
                if m:
                    vid = m.group(1)
            if not vid:
                continue
            try:
                await col.update_one(
                    {"_id": vid},
                    {
                        "$set": {
                            "file_id": media.file_id,
                            "msg_id": msg.id,
                            "title": title,
                            "duration_min": dur_min,
                            "channel": CHANNEL_ID,
                        }
                    },
                    upsert=True,
                )
                count += 1
            except Exception:
                continue
    except Exception as e:
        LOGGER(__name__).warning(f"seed_from_channel failed: {e}")
    if count:
        LOGGER(__name__).info(f"channel cache seeded: {count} tracks")

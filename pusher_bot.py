"""
@aimasterxbot — NVIDIA AI DJ Pusher v3 (24/7)

Guarantee:
  • Har 2-5 min me KAM SE KAM 1 naya song @teamjatayu channel me
  • AI self-check: upload confirm hota hai, fail hua to doosra song try karta hai
  • Har successful push log group me report
  • Dead videos instantly skip (cooldown sirf real rate-limit pe)

Env (.env): BOT_TOKEN, API_ID, API_HASH, MONGO_DB_URI, LOG_GROUP_ID,
            CACHE_CHANNEL_ID, HELLAPI_URL, HELLAPI_KEY, NVIDIA_KEY,
            NVIDIA_MODEL, YTDLP_COOKIES
"""

import asyncio
import json
import os
import random
import re
import time

import aiohttp
import requests as rq
import yt_dlp
from dotenv import load_dotenv
from pyrogram import Client, filters, idle
from pyrogram.errors import FloodWait
from pyrogram.types import Message

HERE = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(HERE, ".env"))

BOT_TOKEN = os.environ["BOT_TOKEN"]
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
MONGO_URI = os.environ["MONGO_DB_URI"]
LOG_GROUP = int(os.getenv("LOG_GROUP_ID", "-1004495764762") or 0)
CHANNEL = int(os.getenv("CACHE_CHANNEL_ID", "-1004323395182"))
HELLAPI_URL = (os.getenv("HELLAPI_URL") or "").rstrip("/")
HELLAPI_KEY = os.getenv("HELLAPI_KEY", "")
NVIDIA_KEY = os.getenv("NVIDIA_KEY", "")
NVIDIA_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
NVIDIA_MODEL = os.getenv("NVIDIA_MODEL", "deepseek-ai/deepseek-v4.1-flash")
COOKIES = os.getenv("YTDLP_COOKIES", os.path.join(HERE, "yt_cookies.txt"))
DL_DIR = os.path.join(HERE, "dl")
os.makedirs(DL_DIR, exist_ok=True)

from motor.motor_asyncio import AsyncIOMotorClient

mongo = AsyncIOMotorClient(MONGO_URI)
tracks = mongo["KurkiMusicCache"].tracks
songlog = mongo["KurkiMusicCache"].push_log

app = Client(
    "aimasterx",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    in_memory=False,
    workdir=HERE,
)

HEADERS = {"x-api-key": HELLAPI_KEY, "Connection": "keep-alive"}

GENRES = [
    "hindi trending songs", "punjabi hits", "bollywood classics",
    "english pop hits", "romantic hindi songs", "sad songs hindi",
    "party punjabi songs", "90s bollywood hits", "lofi chill songs",
    "top english songs", "remix hits", "arijit singh best",
    "new hindi songs 2025", "alka yagnik hits", "sonu nigam best",
    "shreya ghoshal songs", "honey singh hits", "guru randhawa songs",
    "atif aslam best", "jubin nautiyal songs", "neutral hindi love songs",
]

# ── State ────────────────────────────────────────────────────────────────────

PUSHED = {"count": 0, "fails": 0, "start": time.time(), "last_push": 0.0}
_yt_cooldown_until = 0.0     # sirf REAL rate-limit pe
_nvidia_fail_until = 0.0     # NVIDIA hang/fail pe 5 min skip
_dead_ids = set()            # is session me dead mile video ids


def _is_rate_limit(err: str) -> bool:
    e = err.lower()
    return "sign in" in e or "429" in e or "too many requests" in e or "confirm you" in e


def _is_dead(err: str) -> bool:
    e = err.lower()
    return "unavailable" in e or "private video" in e or "removed" in e or "terminated" in e


# ── NVIDIA (optional variety — fail-fast) ────────────────────────────────────

def _nvidia_songs(query: str, count: int = 4):
    global _nvidia_fail_until
    if not NVIDIA_KEY or time.time() < _nvidia_fail_until:
        return []
    try:
        r = rq.post(NVIDIA_URL, timeout=25, headers={
            "Authorization": f"Bearer {NVIDIA_KEY}", "Accept": "application/json"},
            json={"model": NVIDIA_MODEL, "max_tokens": 512, "temperature": 0.9,
                  "messages": [
                      {"role": "system", "content":
                          f'Output ONLY JSON: {{"songs": ["song - artist", ...]}}. '
                          f'{count} real popular songs for: {query}. No duplicates.'},
                      {"role": "user", "content": query}]})
        r.raise_for_status()
        txt = r.json()["choices"][0]["message"]["content"]
        m = re.search(r"\{.*\}", txt, re.S)
        d = json.loads(m.group(0)) if m else {}
        return [s for s in d.get("songs", []) if isinstance(s, str)][:count]
    except Exception as e:
        _nvidia_fail_until = time.time() + 300
        print(f"[nvidia] fail 5min skip: {str(e)[:60]}", flush=True)
        return []


# ── HellAPI search (primary) + yt-dlp search (fallback) ──────────────────────

MIN_DUR, MAX_DUR = 60, 420  # sirf 1-7 min ke songs — jukebox/mix VPS pe download hi nahi hote


def _dur_ok(d):
    try:
        return bool(d) and MIN_DUR <= int(d) <= MAX_DUR
    except Exception:
        return False


async def _hellapi_search(query, limit=5):
    if not HELLAPI_URL:
        return []
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(f"{HELLAPI_URL}/search", params={"q": query, "limit": limit},
                             headers=HEADERS, timeout=aiohttp.ClientTimeout(total=15)) as r:
                if r.status != 200:
                    return []
                data = await r.json()
                return data.get("results", []) or []
    except Exception:
        return []


def _ytdlp_search_ids(query, limit=8):
    """yt-dlp se seedhe video ids — HellAPI down ho to bhi candidates milenge."""
    try:
        opts = {"quiet": True, "no_warnings": True, "extract_flat": True,
                "skip_download": True}
        if os.path.exists(COOKIES) and os.path.getsize(COOKIES) > 50:
            opts["cookiefile"] = COOKIES
        with yt_dlp.YoutubeDL(opts) as y:
            info = y.extract_info(f"ytsearch{limit}:{query}", download=False)
            out = []
            for e in (info.get("entries") or []):
                if e and e.get("id") and len(e["id"]) == 11 and _dur_ok(e.get("duration")):
                    out.append((e["id"], e.get("title") or query))
            return out
    except Exception:
        return []


# ── yt-dlp download (primary) + HellAPI stream (fallback) ────────────────────

def _ytdlp_download(name, vidid=None):
    """Fallback path — direct+cookies (proxy attempts bekaar hain, IP already slow)."""
    out = os.path.join(DL_DIR, f"{vidid or ('q' + str(abs(hash(name)) % 10**8))}.%(ext)s")
    opts = {
        "format": "bestaudio[ext=m4a]/bestaudio/best", "outtmpl": out, "quiet": True,
        "no_warnings": True, "noplaylist": True, "retries": 1, "socket_timeout": 15,
        "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3",
                            "preferredquality": "192"}],
    }
    if os.path.exists(COOKIES) and os.path.getsize(COOKIES) > 50:
        opts["cookiefile"] = COOKIES
    with yt_dlp.YoutubeDL(opts) as y:
        query = f"https://www.youtube.com/watch?v={vidid}" if vidid else f"ytsearch1:{name} audio"
        info = y.extract_info(query, download=True)
        entry = (info.get("entries") or [info])[0]
        vid = entry.get("id") or vidid
        path = entry.get("requested_downloads", [{}])[0].get("filepath") or y.prepare_filename(entry)
        mp3 = os.path.splitext(path)[0] + ".mp3"
        return (mp3 if os.path.exists(mp3) else path), vid, entry.get("title") or name


async def _hellapi_stream_url(vidid):
    """Returns (stream_url, is_dead) — HellAPI ka apna infra YT block bypass karta hai."""
    if not HELLAPI_URL:
        return None, False
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(
                f"{HELLAPI_URL}/api/stream",
                params={"url": f"https://www.youtube.com/watch?v={vidid}", "type": "audio"},
                headers=HEADERS, timeout=aiohttp.ClientTimeout(total=45),
            ) as r:
                if r.status != 200:
                    return None, False
                data = await r.json()
                detail = str(data.get("detail") or "").lower()
                if "unavailable" in detail or "removed" in detail:
                    return None, True
                # Jukebox/mix (7+ min) — VPS pe download hi nahi hota, skip
                if data.get("duration") and int(data["duration"]) > MAX_DUR:
                    return None, True
                url = data.get("stream_url") or data.get("direct_url") or data.get("url")
                return url, False
    except Exception:
        return None, False


async def _download_to(url, path, timeout=600):
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(url, timeout=aiohttp.ClientTimeout(total=timeout, sock_read=90)) as r:
                if r.status != 200:
                    raise ConnectionError(f"HTTP {r.status}")
                with open(path, "wb") as f:
                    async for chunk in r.content.iter_chunked(131072):
                        f.write(chunk)
        return os.path.exists(path) and os.path.getsize(path) > 10000
    except Exception:
        return False


# ── Upload + Mongo index ─────────────────────────────────────────────────────

async def _already_cached(vidid):
    return bool(await tracks.find_one({"_id": vidid}, {"file_id": 1}))


async def _upload_to_channel(path, title, vidid, dur_min=""):
    caption = f"{title} [vid:{vidid}]"
    msg = await app.send_audio(
        CHANNEL,
        audio=path,
        caption=caption[:1000],
        file_name=f"{vidid}.mp3",
        title=title[:60],
        performer="KurkiMusic AI DJ",
    )
    fid = msg.audio.file_id if msg and msg.audio else (
        msg.document.file_id if msg and getattr(msg, "document", None) else None
    )
    if fid:
        await tracks.update_one(
            {"_id": vidid},
            {"$set": {"file_id": fid, "msg_id": msg.id, "title": title, "duration_min": dur_min,
                      "channel": CHANNEL, "source": "aimasterx", "ts": int(time.time())}},
            upsert=True,
        )
    return fid


# ── AI self-check: push confirm hota hai? ────────────────────────────────────

async def _verify_push(vidid):
    """Upload ke baad Mongo + channel dono se confirm karo."""
    try:
        doc = await tracks.find_one({"_id": vidid}, {"file_id": 1, "msg_id": 1})
        return bool(doc and doc.get("file_id") and doc.get("msg_id"))
    except Exception:
        return False


async def _log_report(text):
    if not LOG_GROUP:
        return
    try:
        await app.send_message(LOG_GROUP, text)
    except FloodWait as e:
        await asyncio.sleep(min(e.value, 30))
    except Exception:
        pass


# ── Single song push (complete flow + self-check) ────────────────────────────

async def push_one(vidid, title):
    """Ek song ka poora flow: download → upload → verify → log. Returns bool."""
    path = os.path.join(DL_DIR, f"{vidid}.mp3")
    try:
        # 1) Download — HellAPI relay PRIMARY (apna infra), yt-dlp fallback
        if not (os.path.exists(path) and os.path.getsize(path) > 10000):
            stream, dead = await _hellapi_stream_url(vidid)
            if dead:
                _dead_ids.add(vidid)
                PUSHED["fails"] += 1
                print(f"[dead] {vidid} — HellAPI bola unavailable", flush=True)
                return False
            got = False
            if stream:
                got = await _download_to(stream, path)
            if not got:
                # HellAPI slow/fail → yt-dlp (cookies) fallback
                try:
                    path, vidid, title = await asyncio.wait_for(
                        asyncio.to_thread(_ytdlp_download, title, vidid), timeout=120)
                except asyncio.TimeoutError:
                    raise ConnectionError("ytdlp timeout 120s")
                except Exception as e:
                    err = str(e)
                    if _is_rate_limit(err):
                        global _yt_cooldown_until
                        _yt_cooldown_until = time.time() + 180
                        print("[cooldown] YT rate-limit — 3 min", flush=True)
                    raise

        if not (os.path.exists(path) and os.path.getsize(path) > 10000):
            raise ConnectionError("file nahi bani")

        # 2) Upload channel me
        try:
            fid = await app.send_audio(
                CHANNEL, audio=path, caption=f"{title} [vid:{vidid}]"[:1000],
                file_name=f"{vidid}.mp3", title=title[:60], performer="KurkiMusic AI DJ")
        except FloodWait as e:
            print(f"[flood] {e.value}s — upload baad me", flush=True)
            await asyncio.sleep(min(e.value + 2, 60))
            fid = await app.send_audio(
                CHANNEL, audio=path, caption=f"{title} [vid:{vidid}]"[:1000],
                file_name=f"{vidid}.mp3", title=title[:60], performer="KurkiMusic AI DJ")

        audio = fid.audio if getattr(fid, "audio", None) else getattr(fid, "document", None)
        file_id = audio.file_id if audio else None
        if not file_id:
            raise ConnectionError("upload me file_id nahi mila")

        # 3) Mongo index
        await tracks.update_one(
            {"_id": vidid},
            {"$set": {"file_id": file_id, "msg_id": fid.id, "title": title,
                      "channel": CHANNEL, "source": "aimasterx", "ts": int(time.time())}},
            upsert=True,
        )
        await songlog.insert_one({
            "vidid": vidid, "title": title, "msg_id": fid.id,
            "ts": int(time.time()), "source": "aimasterx"})

        # 4) AI SELF-CHECK — sach me index ho gaya?
        ok = await _verify_push(vidid)

        # 5) Log group me report
        total = await tracks.count_documents({})
        await _log_report(
            "🎵 <b>Naya song push!</b>\n\n"
            f"🎶 <b>{title[:60]}</b>\n"
            f"🆔 <code>{vidid}</code>\n"
            f"💾 Total cache: <b>{total}</b>\n"
            f"{'✅ Verified' if ok else '⚠️ Verify pending'} — @teamjatayu"
        )
        PUSHED["count"] += 1
        PUSHED["last_push"] = time.time()
        print(f"[pushed] {vidid} — {title[:40]} (verify={'OK' if ok else 'PEND'})", flush=True)
        return True

    except Exception as e:
        err = str(e)
        PUSHED["fails"] += 1
        if _is_dead(err):
            _dead_ids.add(vidid)
            print(f"[dead] {vidid} — skip", flush=True)
        else:
            print(f"[fail] {vidid}: {type(e).__name__} {err[:70]}", flush=True)
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception:
            pass
        return False
    finally:
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception:
            pass


# ── Cycle: candidates nikalo, ek push karo ───────────────────────────────────

async def get_candidates():
    """Fresh song candidates — genre + NVIDIA variety."""
    genre = random.choice(GENRES)
    print(f"[cycle] genre: {genre}", flush=True)
    candidates = []

    results = await _hellapi_search(genre, 10)
    candidates = [(r["id"], (r.get("title") or genre)[:70]) for r in results
                  if r.get("id") and _dur_ok(r.get("duration"))]

    if not candidates:
        # HellAPI fail → yt-dlp flat search
        candidates = await asyncio.to_thread(_ytdlp_search_ids, genre, 8)

    # NVIDIA variety (fail-fast)
    songs = await asyncio.to_thread(_nvidia_songs, genre, 4)
    for name in songs:
        extra = await _hellapi_search(f"{name} audio", 2)
        candidates += [(r["id"], (r.get("title") or name)[:70]) for r in extra
                       if r.get("id") and _dur_ok(r.get("duration"))]

    # Filters: cached + dead skip
    fresh = []
    for vidid, title in candidates:
        if vidid in _dead_ids or vidid in {v for v, _ in fresh}:
            continue
        if await _already_cached(vidid):
            continue
        fresh.append((vidid, title))

    # Ye cycle ke genre ke bina bhi kuch chahiye to seedha yt-dlp se
    if not fresh:
        fresh = [
            (v, t) for v, t in await asyncio.to_thread(_ytdlp_search_ids, genre + " songs", 10)
            if v not in _dead_ids and not await _already_cached(v)
        ]
    random.shuffle(fresh)
    return fresh


async def push_cycle():
    """Ek baar chalta hai — kam se kam 1 push ki koshish (max 4 candidates try)."""
    if time.time() < _yt_cooldown_until:
        wait = int(_yt_cooldown_until - time.time())
        print(f"[cooldown] {wait}s baaki — HellAPI-only mode", flush=True)
        results = await _hellapi_search(random.choice(GENRES), 8)
        fresh = []
        for r in results:
            if r.get("id") and not await _already_cached(r["id"]):
                fresh.append((r["id"], (r.get("title") or "?")[:70]))
        random.shuffle(fresh)
        for vidid, title in fresh[:4]:
            if await push_one(vidid, title):
                return True
        return False

    fresh = await get_candidates()
    # HellAPI-stream-able candidates pehle (unke paas apna infra hai)
    streamable = []
    others = []
    for vidid, title in fresh[:6]:
        stream, dead = await _hellapi_stream_url(vidid)
        if dead:
            _dead_ids.add(vidid)
            continue
        if stream:
            streamable.append((vidid, title))
        else:
            others.append((vidid, title))
    for vidid, title in (streamable + others)[:4]:
        if await push_one(vidid, title):
            return True
    return False


# ── Watchdog: 2-5 min guarantee ──────────────────────────────────────────────

async def worker():
    """Main loop — har cycle ke beech 2-5 min, push fail hua to jaldi retry."""
    cycle = 0
    while True:
        t0 = time.time()
        try:
            ok = await push_cycle()
        except Exception as e:
            ok = False
            print(f"[cycle-fail] {type(e).__name__}: {str(e)[:90]}", flush=True)
        cycle += 1

        # Guarantee: push hua to 2-5 min break, nahi hua to 45s me retry
        if ok:
            gap = random.randint(120, 300)
        else:
            gap = 45

        # Har 10 cycle pe status log
        if cycle % 10 == 0:
            total = await tracks.count_documents({})
            mins = (time.time() - PUSHED["start"]) / 60
            rate = PUSHED["count"] / max(0.1, mins / 60)
            await _log_report(
                f"📊 <b>Pusher Status</b>\n\n"
                f"🆕 Session push: <b>{PUSHED['count']}</b>\n"
                f"❌ Fails: {PUSHED['fails']}\n"
                f"💾 Total cache: <b>{total}</b>\n"
                f"⚡ Rate: {rate:.1f} songs/hour\n"
                f"⏱ Last push: {int((time.time() - PUSHED['last_push']) / 60) if PUSHED['last_push'] else '—'} min pehle"
            )
        print(f"[worker] cycle {cycle} done in {int(time.time() - t0)}s, next in {gap}s", flush=True)
        await asyncio.sleep(gap)


# ── Owner commands (log group me) ────────────────────────────────────────────

@app.on_message(filters.command("stats") & (filters.chat(LOG_GROUP) if LOG_GROUP else filters.user()))
async def stats_cmd(_, m: Message):
    total = await tracks.count_documents({})
    mins = (time.time() - PUSHED["start"]) / 60
    await m.reply_text(
        f"💾 <b>Channel cache:</b> {total} songs\n"
        f"🆕 Session push: {PUSHED['count']} | Fails: {PUSHED['fails']}\n"
        f"⚡ Rate: {PUSHED['count'] / max(0.1, mins / 60):.1f} songs/hour\n"
        f"⏱ Last push: {int((time.time() - PUSHED['last_push']) / 60) if PUSHED['last_push'] else '—'} min pehle\n"
        f"🎧 @teamjatayu se instant play."
    )


@app.on_message(filters.command("forcepush") & (filters.chat(LOG_GROUP) if LOG_GROUP else filters.user()))
async def forcepush_cmd(_, m: Message):
    q = m.text.split(maxsplit=1)
    if len(q) < 2:
        return await m.reply_text("Usage: /forcepush <song name>")
    wait = await m.reply_text(f"🔎 Search + push: <b>{q[1]}</b> ...")
    results = await _hellapi_search(q[1], 3)
    vidid = next((r["id"] for r in results if r.get("id")), None)
    title = next((r.get("title") for r in results if r.get("id")), None)
    if not vidid:
        ids = await asyncio.to_thread(_ytdlp_search_ids, q[1], 3)
        if not ids:
            return await wait.edit_text("❌ Kuch nahi mila.")
        vidid, title = ids[0]
    ok = await push_one(vidid, title or q[1])
    await wait.edit_text(
        f"✅ <b>Pushed!</b>\n\n🎵 {title}\n🆔 <code>{vidid}</code>"
        if ok else f"❌ Push fail — logs check karo."
    )


@app.on_message(filters.command("check") & (filters.chat(LOG_GROUP) if LOG_GROUP else filters.user()))
async def check_cmd(_, m: Message):
    """AI health-check: last push kitna purana, aur abhi turant ek push karo."""
    ago = int((time.time() - PUSHED["last_push"]) / 60) if PUSHED["last_push"] else None
    if ago is None:
        await m.reply_text("⚠️ Abhi tak koi push nahi hua — turant cycle start karta hoon...")
        await push_cycle()
        return
    if ago > 10:
        await m.reply_text(f"⚠️ Last push {ago} min purana — healthy nahi. Turant push karta hoon...")
        await push_cycle()
    else:
        total = await tracks.count_documents({})
        await m.reply_text(
            f"✅ Sab sahi hai — last push {ago} min pehle.\n💾 Total: {total} songs"
        )


# ── Main ─────────────────────────────────────────────────────────────────────

async def main():
    await app.start()
    me = await app.get_me()
    print(f"✅ AI DJ Pusher v3 live: @{me.username}", flush=True)
    if LOG_GROUP:
        try:
            await app.send_message(
                LOG_GROUP,
                "🚀 <b>AI DJ Pusher v3 online!</b>\n\n"
                "🎯 Guarantee: har 2-5 min me 1 naya song @teamjatayu me\n"
                "🤖 AI self-check: har push verify hota hai\n"
                "📊 Commands: /stats • /forcepush &lt;song&gt; • /check",
            )
        except Exception:
            pass
    await worker()


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
